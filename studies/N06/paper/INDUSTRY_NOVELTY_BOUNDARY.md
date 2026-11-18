# Exact comparison requirements and industrial novelty boundary

## Already-known building blocks (not claims of N06 novelty)

| Source (original) | Existing mechanism | Why it matters |
|---|---|---|
| [Kubernetes Mixin](https://monitoring.mixins.dev/kubernetes/) | `namespace_workload_pod:kube_pod_owner:relabel` resolves Pod → ReplicaSet → Deployment into workload-level recording series | Existing owner-level aggregation can keep a stable alert identity across Pod rotation. |
| [Kubernetes Mixin issue #1247, 2026](https://github.com/kubernetes-sigs/kubernetes-mixin/issues/1247) | Discusses lower-cardinality per-workload aggregation and using downstream `last_over_time` for staleness; proposal/discussion, **not proof this enhancement shipped** | Need compare to owner-map lookback and analyze cardinality; cannot call staleness smoothing new. |
| [Nextdoor charts](https://github.com/Nextdoor/k8s-charts/blob/804668b33a820b576653afbc120c06672b3bb4ae/charts/prometheus-alerts/templates/containers-prometheusrule.yaml) | Deployment-scoped availability/restart alerts use owner relabeling; documented `max_over_time` lookback trades less flapping for slower resolution | Strongest close industrial baseline; must match actual expressions and end-user contracts. |
| [kube-prometheus](https://github.com/prometheus-operator/kube-prometheus) | `TargetDown` is already group-scoped at service/job with duration | Name-level aggregate is not sufficient if reused by different owners. |
| [Prometheus alerting](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/) | `for` and `keep_firing_for` have precisely specified labelset/timer behavior | Baseline is the native engine, not a hand-implemented timer approximation. |

## Hypothesis remaining to be tested

An alert-level *owner UID continuity certificate*, using Kubernetes rollout
events while applying an independent probe veto, may improve **missed page
versus false page versus recovery-delay** tradeoffs when owner metadata is
missing, deployment names are reused or short Prometheus gaps occur. It may
also add cardinality, CPU, rollout-event race and operational burden.

An industrial contribution needs a head-to-head field improvement over the
**exact published owner+lookback alternatives**, not just over per-Pod alerts.
It must show when N06 is better, equal, and worse. The existing synthetic
experiment is insufficient to decide that question.

## Matched baseline designs for field testing

1. Unmodified native Kubernetes per-Pod alert with `for`.
2. Unmodified or semantically matched kube-prometheus service aggregation.
3. Kubernetes Mixin Pod→Workload label joining at owner name and UID,
   with no lookback and with independently tuned/lookback-stabilized variants.
4. Nextdoor's actual Deployment-scoped rule with its original event contract,
   plus optional published lookback settings. Do **not** label a synthetic
   Python `owner_lookback` proxy as an exact Nextdoor replication.
5. Independent black-box probe-only alert with matched `for` duration.
6. N06 v2 with all components versus without probe veto, no event trust,
   wrong-owner negative control, missing-owner metadata, real heal and
   rollout with no outage.

Primary field outcome: per-incident probability of first on-call page during
the independently labeled outage window, with observed arrival delay. Safety
outcomes: additional pages during truly healthy time; false continuation after
real recovery; wrong-owner carryover; event volume and total monitoring cost.
Unit of independence: project/incident, **not 15-second samples**.

Do not write that "the owner-aware method is an original new monitoring
primitive" until the above original prior art is handled; at present the
novelty claim is **unverified and likely narrower than the original screening**.
