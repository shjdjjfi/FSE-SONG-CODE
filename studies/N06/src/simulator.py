"""N06 controlled, discrete-time alert-state experiment.

IMPORTANT: This is an independently implemented *model* of the Prometheus
`for` state machine, not the Prometheus TSDB, PromQL engine, or promtool.
No generated trace is a production trace.  The health oracle is hidden from
all policies.  All methods see exactly the same observable event stream.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import random
from typing import Any

SECONDS_PER_TICK = 15
PROFILES = {"kube_prometheus_targetdown_10m": 40, "ftw_podnotready_15m": 60}
SEEDS = (17, 29, 43)
FAMILIES = (
    "no_churn_outage",
    "churn_outage",
    "rollout_clock_skew",
    "long_gap_outage",
    "missing_owner",
    "scrape_gap_outage",
    "owner_reuse",
    "recovery_reset",
    "silent_recovery_no_rollout",
    "healthy_rollout",
    "partial_replica",
)
POLICIES = (
    "instance",
    "service",
    "targetdown10",
    "service_grace",
    "targetdown10_grace",
    "owner_no_gap",
    "owner_lookback",
    "owner_relink",
    "owner_relink_v2",
    "owner_no_probe",
    "probe_latch",
)


@dataclass(frozen=True)
class Pod:
    pod: str
    owner: str | None
    bad: bool


@dataclass(frozen=True)
class Rollout:
    old_pod: str
    new_pod: str
    old_owner: str | None
    new_owner: str | None
    trusted: bool


@dataclass(frozen=True)
class Tick:
    time: int
    pods: tuple[Pod, ...]
    rollouts: tuple[Rollout, ...]
    probe_bad: bool | None
    # The fields below exist ONLY for evaluation and must never be passed
    # to a policy; they are removed in observation().
    oracle_bad_owners: tuple[str, ...]

    def observation(self) -> "Observation":
        return Observation(self.time, self.pods, self.rollouts, self.probe_bad)


@dataclass(frozen=True)
class Observation:
    time: int
    pods: tuple[Pod, ...]
    rollouts: tuple[Rollout, ...]
    probe_bad: bool | None


@dataclass(frozen=True)
class Episode:
    episode_id: str
    profile: str
    hold_ticks: int
    family: str
    seed: int
    replicate: int
    ticks: tuple[Tick, ...]

    def to_record(self) -> dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "profile": self.profile,
            "hold_ticks": self.hold_ticks,
            "family": self.family,
            "seed": self.seed,
            "replicate": self.replicate,
            "seconds_per_tick": SECONDS_PER_TICK,
            "synthetic": True,
            "ticks": [asdict(t) for t in self.ticks],
        }


def make_episode(profile: str, family: str, seed: int, replicate: int,
                 *, owner_missing: float | None = None,
                 probe_missing: float = 0.12, probe_noise: float = 0.0) -> Episode:
    """Generate a deterministic synthetic episode with independent ground truth.

    The episode oracle represents *owner-scoped black-box service unavailability*,
    not the original intent of any external Prometheus rule.  Observations are
    pod readiness, owner references, rollout metadata, and sampled probes.
    Probe truth, though correlated with the oracle, is neither perfect nor
    continuously available.  The oracle is never consumed by a policy.
    """
    if profile not in PROFILES or family not in FAMILIES:
        raise ValueError("Unknown profile/family")
    if not 0 <= probe_missing <= 1 or not 0 <= probe_noise <= 1:
        raise ValueError("probabilities must be in [0, 1]")
    if owner_missing is not None and not 0 <= owner_missing <= 1:
        raise ValueError("owner_missing must be in [0, 1]")
    hold = PROFILES[profile]
    rng = random.Random(f"N06-v1|{profile}|{family}|{seed}|{replicate}")
    length = 3 * hold + 55
    start = 16 + rng.randint(0, 4)
    end = length - 18
    uid_a, uid_b = f"deployment-A-{replicate}", f"deployment-B-{replicate}"
    pod_prefix = f"ns{replicate % 4}-svc{replicate % 6}"
    turns: list[tuple[int, int, str, str, bool, int]] = []

    if family in {"churn_outage", "rollout_clock_skew", "long_gap_outage", "missing_owner", "healthy_rollout"}:
        candidate = start + rng.randint(8, 13)
        while candidate < end - 10:
            gap = rng.randint(1, 4)
            if family == "long_gap_outage" and len(turns) == 1:
                gap = rng.randint(11, 17)
            jitter = rng.randint(-3, 3) if family == "rollout_clock_skew" else 0
            trusted = family != "missing_owner" or rng.random() > 0.45
            turns.append((candidate, gap, uid_a, uid_a, trusted, jitter))
            candidate += rng.randint(12, 20)
    elif family == "owner_reuse":
        turn = start + round(0.70 * hold)
        turns.append((turn, rng.randint(1, 3), uid_a, uid_b, True, 0))
    elif family == "recovery_reset":
        turn = start + round(0.65 * hold)
        turns.append((turn, rng.randint(2, 5), uid_a, uid_a, True, 0))

    # Never allow overlapping gap intervals; event delivery can be late/early.
    turns.sort()
    event_at: dict[int, list[Rollout]] = {}
    for i, (turn, gap, old_owner, new_owner, trusted, jitter) in enumerate(turns):
        event_time = max(0, turn + jitter)
        event_at.setdefault(event_time, []).append(
            Rollout(f"{pod_prefix}-p{i}", f"{pod_prefix}-p{i + 1}",
                    old_owner, new_owner, trusted))

    owner_dropout = owner_missing if owner_missing is not None else (0.48 if family == "missing_owner" else 0.0)
    probe_period = rng.choice((4, 8, 12))
    probe_phase = rng.randint(0, probe_period - 1)
    scrape_gaps: set[int] = set()
    if family == "scrape_gap_outage":
        for _ in range(4):
            gap_start = rng.randint(start + 4, end - 14)
            scrape_gaps.update(range(gap_start, gap_start + rng.randint(3, 8)))

    first_owner_end = turns[0][0] if turns and family == "owner_reuse" else None
    recovery_start = (turns[0][0] if turns and family == "recovery_reset" else
                      start + round(0.65 * hold) if family == "silent_recovery_no_rollout" else None)
    recovery_length = rng.randint(3, 6)
    if family == "silent_recovery_no_rollout":
        assert recovery_start is not None
        scrape_gaps.update(range(recovery_start, recovery_start + recovery_length))
    ticks: list[Tick] = []
    for t in range(length):
        if family in {"owner_reuse", "recovery_reset", "silent_recovery_no_rollout"}:
            if family == "owner_reuse":
                assert first_owner_end is not None
                if start <= t < first_owner_end:
                    actual = (uid_a,)
                elif first_owner_end <= t < first_owner_end + round(0.70 * hold):
                    actual = (uid_b,)
                else:
                    actual = ()
            else:
                assert recovery_start is not None
                spell2 = recovery_start + recovery_length
                actual = ((uid_a,) if (start <= t < recovery_start or
                        spell2 <= t < spell2 + round(0.65 * hold)) else ())
        elif family in {"healthy_rollout", "partial_replica"}:
            actual = ()
        else:
            actual = (uid_a,) if start <= t < end else ()

        active_gap = next(((i, turn, gap) for i, (turn, gap, *_rest) in enumerate(turns)
                           if turn <= t < turn + gap), None)
        completed_turns = sum(turn + gap <= t for turn, gap, *_rest in turns)
        current_pod_id = f"{pod_prefix}-p{completed_turns}"
        current_owner = uid_b if family == "owner_reuse" and completed_turns else uid_a
        pods: list[Pod] = []
        if active_gap is None and t not in scrape_gaps:
            metadata = current_owner if rng.random() >= owner_dropout else None
            is_bad = bool(actual)
            if family == "healthy_rollout":
                is_bad = any(turn + gap <= t < turn + gap + rng.randint(3, 5)
                             for turn, gap, *_rest in turns)
            if family == "partial_replica":
                pods.append(Pod(current_pod_id, metadata, True))
                pods.append(Pod(f"{pod_prefix}-healthy", uid_a, False))
            else:
                pods.append(Pod(current_pod_id, metadata, is_bad))

        # Synthetic black-box health samples are an observation, not the oracle.
        probe: bool | None = None
        if t % probe_period == probe_phase and rng.random() >= probe_missing:
            probe = bool(actual)
            if rng.random() < probe_noise:
                probe = not probe
        ticks.append(Tick(t, tuple(pods), tuple(event_at.get(t, ())), probe, actual))

    episode_id = f"{profile}__{family}__s{seed}__r{replicate:03d}"
    return Episode(episode_id, profile, hold, family, seed, replicate, tuple(ticks))


class PendingFor:
    """Prometheus-like per-fingerprint hold duration, without PromQL/TSDB."""

    def __init__(self, hold_ticks: int) -> None:
        self.hold_ticks = hold_ticks
        self.active_at: dict[str, int] = {}

    def step(self, t: int, active: set[str]) -> set[str]:
        for key in tuple(self.active_at):
            if key not in active:
                del self.active_at[key]
        for key in active:
            if key not in self.active_at:
                self.active_at[key] = t
        return {key for key, begun in self.active_at.items() if t - begun >= self.hold_ticks}


class Policy:
    def __init__(self, policy: str, hold_ticks: int, grace: int = 6,
                 probe_ttl: int = 14) -> None:
        if policy not in POLICIES:
            raise ValueError(f"unknown policy: {policy}")
        self.name = policy
        self.hold = PendingFor(hold_ticks)
        self.grace = grace
        self.probe_ttl = probe_ttl
        self.last_bad: dict[str, int] = {}
        self.last_verified_rollout: dict[str, int] = {}
        self.last_probe_bad: int | None = None
        self.last_condition: frozenset[str] = frozenset()
        self.pod_owner_cache: dict[str, str] = {}

    def step(self, obs: Observation) -> set[str]:
        """No access to Tick.oracle_bad_owners or to future observations."""
        t = obs.time
        if self.name == "probe_latch":
            if obs.probe_bad is True:
                self.last_probe_bad = t
            if obs.probe_bad is False:
                self.last_probe_bad = None
            bad = (self.last_probe_bad is not None and
                   t - self.last_probe_bad <= self.probe_ttl)
            self.last_condition = frozenset({"service"} if bad else ())
            return self.hold.step(t, {"service"} if bad else set())

        owner_based = self.name in {"owner_no_gap", "owner_lookback", "owner_relink", "owner_relink_v2", "owner_no_probe"}
        use_gap = self.name in {"service_grace", "targetdown10_grace", "owner_lookback", "owner_relink", "owner_relink_v2", "owner_no_probe"}
        use_probe = self.name in {"service_grace", "targetdown10_grace", "owner_no_gap", "owner_lookback", "owner_relink", "owner_relink_v2"}
        if obs.probe_bad is True:
            self.last_probe_bad = t
        if obs.probe_bad is False:
            self.last_probe_bad = None
        rejected: set[str] = set()
        if owner_based:
            for event in obs.rollouts:
                old_key = event.old_owner or f"pod:{event.old_pod}"
                if (event.trusted and event.old_owner is not None and
                        event.old_owner == event.new_owner):
                    self.last_verified_rollout[old_key] = t
                    if self.name == "owner_relink_v2":
                        self.pod_owner_cache[event.old_pod] = event.old_owner
                        self.pod_owner_cache[event.new_pod] = event.new_owner
                else:
                    # An owner replacement is a *negative* link, even when
                    # namespace/service strings are identical.
                    rejected.add(old_key)
                    self.last_verified_rollout.pop(old_key, None)
                    self.last_bad.pop(old_key, None)

        readings: dict[str, list[bool]] = {}
        for pod in obs.pods:
            if self.name == "owner_relink_v2" and pod.owner is not None:
                self.pod_owner_cache[pod.pod] = pod.owner
            if self.name == "instance":
                key = f"pod:{pod.pod}"
            elif owner_based:
                inferred = (self.pod_owner_cache.get(pod.pod)
                            if self.name == "owner_relink_v2" else None)
                key = pod.owner or inferred or f"pod:{pod.pod}"
            else:
                key = "namespace/service"
            readings.setdefault(key, []).append(pod.bad)

        # The `targetdown10*` alternatives approximate the upstream TargetDown
        # >10% threshold.  All other owner/stable-service alternatives require
        # every *currently visible* replica to be unready.  Both choices are
        # simplified offline contracts, not exact PromQL query execution.
        if self.name in {"targetdown10", "targetdown10_grace"}:
            active = {key for key, statuses in readings.items()
                      if sum(statuses) / len(statuses) > 0.10}
        else:
            active = {key for key, statuses in readings.items() if all(statuses)}
        if use_gap and self.grace > 0:
            for key, last in tuple(self.last_bad.items()):
                if key in readings or key in rejected or t - last > self.grace:
                    continue
                if self.name in {"owner_relink", "owner_relink_v2", "owner_no_probe"}:
                    verified = self.last_verified_rollout.get(key)
                    if verified is None or t - verified > self.grace:
                        if self.name != "owner_relink_v2":
                            continue
                        # V2 was designed *after* examining the first-run
                        # diagnostics.  A recent unhealthy black-box probe
                        # provides provisional continuity without a rollout,
                        # but this may wrongly bridge an unobserved recovery.
                        probe = self.last_probe_bad
                        if probe is None or t - probe > self.probe_ttl:
                            continue
                active.add(key)

        # Healthy black-box probes are equally available to all probe-aware
        # baselines, not a special hidden ground-truth advantage of our method.
        if use_probe and obs.probe_bad is False:
            active.clear()
            self.last_bad.clear()
        else:
            for key in active:
                if key in readings and key in active:
                    self.last_bad[key] = t
            for key, statuses in readings.items():
                if key not in active:
                    self.last_bad.pop(key, None)
        self.last_condition = frozenset(active)
        return self.hold.step(t, active)


def evaluate(episode: Episode, *, grace: int = 6,
             probe_ttl: int = 14,
             selected: tuple[str, ...] = POLICIES) -> list[dict[str, Any]]:
    """Pair all methods on one frozen trace; compute independent oracle first."""
    oracle = PendingFor(episode.hold_ticks)
    expected: list[bool] = []
    for tick in episode.ticks:
        expected.append(bool(oracle.step(tick.time, set(tick.oracle_bad_owners))))
    target_first = next((i for i, x in enumerate(expected) if x), None)
    rows: list[dict[str, Any]] = []
    for name in selected:
        policy = Policy(name, episode.hold_ticks, grace=grace, probe_ttl=probe_ttl)
        predicted = [bool(policy.step(tick.observation())) for tick in episode.ticks]
        first_correct = next((i for i, (p, y) in enumerate(zip(predicted, expected))
                              if p and y), None)
        false_page_count = sum(p and not (predicted[i - 1] if i else False) and not y
                               for i, (p, y) in enumerate(zip(predicted, expected)))
        false_ticks = sum(p and not y for p, y in zip(predicted, expected))
        delay = ((first_correct - target_first) * SECONDS_PER_TICK / 60
                 if first_correct is not None and target_first is not None else None)
        rows.append({
            "episode_id": episode.episode_id,
            "profile": episode.profile,
            "family": episode.family,
            "seed": episode.seed,
            "replicate": episode.replicate,
            "policy": name,
            "oracle_positive": target_first is not None,
            "oracle_first_tick": target_first,
            "correct_first_tick": first_correct,
            "any_correct_page": first_correct is not None,
            "miss": target_first is not None and first_correct is None,
            "false_page_events": false_page_count,
            "any_false_page": false_page_count > 0,
            "false_firing_minutes": false_ticks * SECONDS_PER_TICK / 60,
            "delay_after_oracle_minutes": delay,
            "total_ticks": len(expected),
            "grace_ticks": grace,
            "probe_ttl_ticks": probe_ttl,
        })
    return rows
