"""Export two frozen synthetic owner-link cases to native promtool test YAML.

The generated test is syntactically compatible with Prometheus unit testing,
but only a real promtool execution can validate its query and rule evaluation.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from simulator import Policy, SECONDS_PER_TICK, evaluate, make_episode

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "promtool" / "generated_owner_cases.yml"


def encode(episode, *, positive: bool) -> tuple[dict, dict]:
    policy = Policy("owner_relink", episode.hold_ticks)
    status_by_time: list[set[str]] = []
    fired_by_time: list[set[str]] = []
    for tick in episode.ticks:
        fired_by_time.append(policy.step(tick.observation()))
        status_by_time.append(set(policy.last_condition))
    if positive:
        picked = next((t for t, fired in enumerate(fired_by_time) if fired), None)
        if picked is None:
            raise AssertionError("No positive relink evidence on the frozen example")
    else:
        if any(fired_by_time):
            raise AssertionError("Negative owner-reuse trace unexpectedly fires")
        picked = min(len(episode.ticks) - 1, episode.hold_ticks + 35)

    observed_owners = sorted({uid for values in status_by_time for uid in values
                              if not uid.startswith("pod:")})
    input_series = []
    for uid in observed_owners:
        values = ["1" if uid in labels else "_" for labels in status_by_time[:picked + 1]]
        input_series.append({
            "series": f'n06_owner_unavailable{{job="n06-relink",namespace="synthetic",service="checkout",owner_uid="{uid}"}}',
            "values": " ".join(values),
        })
    firing_ids = sorted(uid for uid in fired_by_time[picked] if not uid.startswith("pod:"))
    expected = [{"exp_labels": {"job": "n06-relink", "namespace": "synthetic", "service": "checkout",
                                "owner_uid": uid, "severity": "test"}} for uid in firing_ids]
    case = {
        "name": f"N06 synthetic {'verified owner continuity' if positive else 'unrelated owner reuse'}",
        "interval": f"{SECONDS_PER_TICK}s",
        "input_series": input_series,
        "alert_rule_test": [{"eval_time": f"{picked * SECONDS_PER_TICK}s",
                             "alertname": "N06OwnerRelinkDown",
                             "exp_alerts": expected}],
    }
    audit = {"episode_id": episode.episode_id, "oracle_category": "positive" if positive else "negative",
             "test_tick": picked, "expected_firing": len(expected),
             "evidence_kind": "synthetic policy-output replay, not native engine execution"}
    return case, audit


def main() -> None:
    positive = make_episode("kube_prometheus_targetdown_10m", "churn_outage", 17, 0)
    negative = make_episode("kube_prometheus_targetdown_10m", "owner_reuse", 17, 0)
    a, audit_a = encode(positive, positive=True)
    b, audit_b = encode(negative, positive=False)
    tests = {"rule_files": ["alert_rules.yml"],
             "evaluation_interval": f"{SECONDS_PER_TICK}s", "tests": [a, b]}
    OUT.write_text(yaml.safe_dump(tests, sort_keys=False, allow_unicode=True), encoding="utf-8")
    audit_file = ROOT / "results_v2" / "promtool_generated_cases.json"
    audit_file.write_text(json.dumps({"native_promtool_executed": False, "cases": [audit_a, audit_b]},
                                     indent=2), encoding="utf-8")
    print(f"Prepared {len(tests['tests'])} synthetic owner-relink cases; native promtool still required.")


if __name__ == "__main__":
    main()
