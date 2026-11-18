# N06: falsifiable experiment protocol

## Research question and units

**RQ1** Can owner-/rollout-aware alert-state association preserve true
owner-scoped service outage timers when pod identities churn?

**RQ2** Does it reject inappropriate continuity across genuine recovery and
different owner UIDs sharing the same namespace/service name?

**RQ3** Are any gains still present against strong existing methods using
service aggregation, owner aggregation with lookback, and direct black-box
probe latching?

An independent evaluation *unit* is one generated episode, **not** a timestep,
pod, rule, alert transition or raw metric sample.  The same episode is
evaluated under all policies.  Public source rule *profiles* are two distinct
durations, not two deployed test systems.

## Source-derived configurations and fixed parameters

- `TargetDown` in kube-prometheus, grouped by cluster/job/namespace/service,
  uses a ratio of down targets greater than 10% and `for: 10m`.  The model
  includes an explicit `targetdown10` ratio-approximation baseline.
- Fractal Techware's `KubePodNotReady` includes pod identity and `for: 15m`.
  We reuse its duration profile, **not** the original production PodNotReady
  expression or notion of pod-specific correct behavior.
- Evaluation tick = 15 seconds.  Hold time = 40 or 60 consecutive ticks after
  the initial active step.  Event horizon = 3×hold+55 ticks.
- Main runs use three seeds 17, 29, 43; 30 replicates per seed, family,
  duration; 2 × 11 × 3 × 30 = 1,980 episodes.
- Primary gap allowance = 6 ticks / 90 s.  Probe freshness TTL = 14 ticks.
  Probe missingness = 12%, probe noise = 0%; phases and cadence (60/120/180 s)
  vary by fixed deterministic generator seed.  This is a *mechanism setting*,
  not an estimate of public production telemetry quality.
- Deterministic generation uses `random.Random` with a string made from
  profile, family, seed and replicate.  No hidden API, LLM or GPU is involved.

## Independent oracle and blind policies

The oracle defines an incident only while **the same owner UID** has an
uninterrupted simulated black-box service outage for at least the hold time.
If a service name is deleted and reused by a different owner UID, the clocks
must be distinct.  This is an explicit *owner-scoped service contract*; other
organizations may have different on-call contracts.  A short genuine recovery
resets the true timer.

The data generator then projects the oracle into observable but incomplete
pod readiness samples, owner metadata, rollout events and lower-cadence
independent health probes.  Policy inputs are `Observation(time, pods,
rollouts, probe_bad)` only; the oracle is excluded from that type.  Tests
explicitly verify that changing the evaluation-only oracle does not alter
method predictions.  The synthetic probe is correlated with the oracle, but
does not reveal unobserved time steps, and it is equally exposed to all
probe-aware baselines.

## Policy arms

| Name | Operational abstraction | Receives probe veto? |
|---|---|---|
| `instance` | per-pod label fingerprint and `for` | No |
| `service` | stable namespace/service, all *visible* pods down | No |
| `targetdown10` | approximate upstream >10% down threshold | No |
| `service_grace` | service aggregation with 90 s last-observation bridging | Yes |
| `targetdown10_grace` | ratio threshold and 90 s bridging | Yes |
| `owner_no_gap` | stable owner UID but no gap bridging | Yes |
| `owner_lookback` | existing-practice approximation: owner UID + lookback bridge | Yes |
| `owner_relink` | owner UID, **verified rollout event** required to bridge gaps | Yes |
| `owner_no_probe` | same as relink, omit health-probe veto | No |
| `probe_latch` | independent probe state retained for a 210 s TTL | Based exclusively on probe |
| `owner_relink_v2` | **post-hoc exploratory**: verified pod-to-owner cache and unhealthy-probe fallback | Yes |

All methods see an identical stream and use the same `for`.  Some methods use
less information deliberately as ablations.  `owner_lookback` is an especially
strong existing-practice comparator after discovering the Nextdoor chart.
It is not the chart's exact PromQL and cannot be used as a measured replay of
Nextdoor software.

## Scenario taxonomy

| Family | Oracle | Stressor / falsification |
|---|---|---|
| `no_churn_outage` | positive | prolonged true outage without replacement |
| `churn_outage` | positive | multiple same-owner replacements and short missing series |
| `rollout_clock_skew` | positive | event timing ±3 ticks, strict verified bridging |
| `long_gap_outage` | positive | same-owner replacement with one 165–255 s gap |
| `missing_owner` | positive | 48% probability owner field absent; 45% rollout trust loss |
| `scrape_gap_outage` | positive | unrelated metric gaps with **no** verified rollout |
| `owner_reuse` | negative | old/new different UIDs reuse the same service string |
| `recovery_reset` | negative | true recovery and same-owner rollout between two short outages |
| `silent_recovery_no_rollout` | negative | genuine recovery disappears from metric stream, no rollout |
| `healthy_rollout` | negative | healthy service with transient pod-not-ready observations |
| `partial_replica` | negative | one unready pod, another healthy; black-box service remains up |

Six positive and five negative families × 2 profiles × 3 seeds × 30
replicates.  The exact failure onset, pod ID, sample timing and probe phase
vary per deterministic episode.

## Primary endpoints

1. **Detection recall** = positive episodes with a firing alert at a tick
   while owner-scoped oracle alert is firing / positive episodes.
2. **False-page episode rate** = negative episodes with at least one transition
   to a firing alert / negative episodes.
3. False first-page transitions per 100 *simulated* hours, and false firing
   minutes per 100 simulated hours (normalizing all episodes).
4. Conditional delay = first correct firing tick minus the first oracle
   firing tick ×15 s, reported only for successful detections.  Missing
   positives are recorded separately, not silently treated as zero delay.
5. Paired model differences and stratified Monte Carlo bootstrap intervals
   of miss and false-page rate, balanced by family/seed/profile.  The
   bootstrap is **not a field-level 95% CI**, and seed-level statistics are
   reported separately.

## Sensitivity and negative controls

The frozen sensitivity grid varies bridging window from 0 to 180 seconds on
every fifth synthetic replicate.  Negative controls include unrelated owner
reuse, genuine healing with or without rollout, healthy rolling update, and
partial replica failures.  The `owner_no_probe` ablation tests the explicit
probe-veto assumption.  A native Prometheus rule unit-test file is prepared
to verify label fingerprints and `for` semantics externally.

## Predeclared publication gate and stop condition

**Stop or redesign if a simpler owner aggregation / lookback baseline offers
equal detection timeliness and no greater healthy-rollout false-page rate.**
The proposal also demands a meaningful first-page difference of at least one
15-second evaluation interval on an independently held-out deployed system,
and no worse healthy-rollout false alarm count.

The gate cannot pass on the simulated benchmark alone.  It requires at least
two independent *actual* Kubernetes/service systems with independent probe
truth and rollout event identity, native Prometheus evaluation of all rule
arms, and project-held-out inference with project/event cluster intervals.
See `SUBMISSION_BLOCKERS.md` for the missing parts.

## Model/validity limitations

The simulator does **not** implement PromQL vector matching, staleness,
lookback_delta, rule group scheduling, alert restoration on restart,
`keep_firing_for`, Alertmanager grouping/deduplication/routing, real owner
resolution via ReplicaSet, probe delivery latency, or Kubernetes rollout
control-plane delays.  It only models a per-fingerprint `for` clock over
synthetically projected boolean alert conditions.  It is honest to call this
a controlled mechanism study, **not a Prometheus/Kubernetes empirical study**.
