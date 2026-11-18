"""Model semantics and falsification tests, run with stdlib unittest."""

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import yaml

from simulator import (FAMILIES, PROFILES, SEEDS, Episode, Observation, Rollout,
                       PendingFor, Policy, Pod, Tick, evaluate, make_episode)


class AlertStateTests(unittest.TestCase):
    def test_prometheus_like_for_first_eval(self):
        hold = PendingFor(4)
        self.assertEqual([bool(hold.step(t, {"x"})) for t in range(6)],
                         [False, False, False, False, True, True])

    def test_missing_step_erases_pending(self):
        hold = PendingFor(3)
        sequence = [{"x"}, {"x"}, set(), {"x"}, {"x"}, {"x"}, {"x"}]
        self.assertEqual([bool(hold.step(t, s)) for t, s in enumerate(sequence)],
                         [False, False, False, False, False, False, True])

    def test_no_lookahead_oracle(self):
        episode = make_episode(next(iter(PROFILES)), "churn_outage", 17, 3)
        for candidate in ("owner_relink", "owner_relink_v2"):
            policy_a = Policy(candidate, episode.hold_ticks)
            policy_b = Policy(candidate, episode.hold_ticks)
            observed = []
            for tick in episode.ticks:
                observed.append(bool(policy_a.step(tick.observation())))
                falsified = Tick(tick.time, tick.pods, tick.rollouts,
                                 tick.probe_bad, ("secret-oracle-falsified",))
                self.assertIsInstance(falsified.observation(), Observation)
                self.assertEqual(bool(policy_b.step(falsified.observation())), observed[-1])

    def test_unrelated_owner_never_merged(self):
        episode = make_episode("kube_prometheus_targetdown_10m", "owner_reuse", 17, 1)
        results = {r["policy"]: r for r in evaluate(episode)}
        self.assertFalse(results["owner_relink"]["oracle_positive"])
        self.assertEqual(results["owner_relink"]["false_page_events"], 0)
        # Aggregation may merge two separate owners under a reused service name.
        self.assertGreaterEqual(results["service_grace"]["false_page_events"], 0)

    def test_stable_no_churn_detected(self):
        episode = make_episode("kube_prometheus_targetdown_10m", "no_churn_outage", 17, 1)
        results = {r["policy"]: r for r in evaluate(episode)}
        self.assertTrue(results["service"]["oracle_positive"])
        self.assertTrue(results["service"]["any_correct_page"])
        self.assertTrue(results["owner_no_gap"]["any_correct_page"])

    def test_every_profile_family_seed_deterministic(self):
        for profile in PROFILES:
            for family in FAMILIES:
                a = make_episode(profile, family, SEEDS[0], 0)
                b = make_episode(profile, family, SEEDS[0], 0)
                self.assertEqual(a, b)

    def test_only_probes_and_pods_can_trigger(self):
        for name in ("instance", "service", "targetdown10", "service_grace", "targetdown10_grace", "owner_no_gap", "owner_lookback",
                     "owner_relink", "owner_relink_v2", "owner_no_probe", "probe_latch"):
            policy = Policy(name, 3)
            for t in range(9):
                self.assertFalse(policy.step(Observation(t, (), (), None)), name)

    def test_same_owner_relink_does_not_look_past_gap(self):
        policy = Policy("owner_relink", 4, grace=2)
        pattern = (
            Observation(0, (Pod("a", "uid1", True),), (), None),
            Observation(1, (Pod("a", "uid1", True),), (), None),
            Observation(2, (), (), None),
            Observation(3, (), (), None),
            Observation(4, (Pod("b", "uid1", True),), (), None),
        )
        # Without a *verified* rollout event, missing series must reset.
        out = [bool(policy.step(obs)) for obs in pattern]
        self.assertFalse(out[-1])

    def test_v2_recovers_known_pod_owner_metadata_dropout(self):
        original = Policy("owner_relink", 2)
        candidate = Policy("owner_relink_v2", 2)
        series = [
            Observation(0, (Pod("podA", "uid1", True),), (), None),
            Observation(1, (Pod("podA", None, True),), (), None),
            Observation(2, (Pod("podA", None, True),), (), None),
        ]
        self.assertFalse(any(original.step(x) for x in series))
        self.assertTrue(bool([candidate.step(x) for x in series][-1]))

    def test_v2_follows_verified_new_pod_without_metadata(self):
        candidate = Policy("owner_relink_v2", 2, grace=3)
        series = [
            Observation(0, (Pod("podA", "uid1", True),), (), None),
            Observation(1, (), (Rollout("podA", "podB", "uid1", "uid1", True),), True),
            Observation(2, (Pod("podB", None, True),), (), None),
        ]
        self.assertTrue(bool([candidate.step(x) for x in series][-1]))

    def test_healthy_probe_cancels_pending_for_v2(self):
        candidate = Policy("owner_relink_v2", 2, grace=5)
        series = [
            Observation(0, (Pod("podA", "uid1", True),), (), True),
            Observation(1, (), (Rollout("podA", "podB", "uid1", "uid1", True),), True),
            Observation(2, (), (), False),
            Observation(3, (Pod("podB", "uid1", True),), (), True),
            Observation(4, (Pod("podB", "uid1", True),), (), None),
            Observation(5, (Pod("podB", "uid1", True),), (), None),
        ]
        output = [bool(candidate.step(x)) for x in series]
        self.assertEqual(output, [False, False, False, False, False, True])

    def test_v2_refuses_different_owner_uid(self):
        candidate = Policy("owner_relink_v2", 3, grace=5)
        series = [
            Observation(0, (Pod("podA", "uid1", True),), (), True),
            Observation(1, (Pod("podA", "uid1", True),), (), None),
            Observation(2, (), (Rollout("podA", "podB", "uid1", "uid2", True),), True),
            Observation(3, (Pod("podB", "uid2", True),), (), None),
            Observation(4, (Pod("podB", "uid2", True),), (), None),
        ]
        self.assertFalse(any(candidate.step(x) for x in series))


class UpstreamTests(unittest.TestCase):
    def test_upstream_pinned_15m_pod_cases(self):
        src = Path(__file__).resolve().parent.parent / "sources"
        test_file = yaml.safe_load((src / "ftw_kubernetes_workloads.test.yml").read_text())
        cases = [t for t in test_file["tests"] if "KubePodNotReady" in t["name"]]
        self.assertEqual(len(cases), 2)
        self.assertEqual(len(cases[0]["alert_rule_test"][0]["exp_alerts"]), 1)
        self.assertEqual(cases[1]["alert_rule_test"][0]["exp_alerts"], [])
        self.assertIn("owner_kind=\"Job\"", cases[1]["input_series"][1]["series"])

    def test_upstream_sources_have_correct_hold_durations(self):
        from run_experiments import check_upstream
        sources = check_upstream()
        self.assertEqual(sources["kube_prometheus"]["for_minutes"], 10)
        self.assertEqual(sources["fractal_techware"]["for_minutes"], 15)


if __name__ == "__main__":
    unittest.main()
