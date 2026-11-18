# Prior art and novelty risk audit — N06

Research date: November 15, 2026.  These entries were checked against
authoritative project or research sources; coverage is not exhaustive.

## 1. Official Prometheus behavior

The Prometheus project states that an alert condition becomes active for each
distinct output vector element/labelset. `for` requires persistence over the
configured duration, while `keep_firing_for` retains **already firing** alerts
after the condition is lost.  Rule testing is officially supported with
`promtool test rules`.

- https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/
- https://prometheus.io/docs/prometheus/latest/configuration/unit_testing_rules/
- https://github.com/prometheus/prometheus/blob/main/rules/alerting.go

The Prometheus issue below reported *short no-data gaps* and timer reset,
**not** a documented owner UID or pod-replacement discontinuity.  It is
independent evidence of gap-related fragility only, not a verified positive
example of the N06 identity-churn hypothesis:

- https://github.com/prometheus/prometheus/issues/19909

## 2. High-risk near precedent: Nextdoor Kubernetes alert chart

Nextdoor's open-source `charts/prometheus-alerts` contains an opt-in
`KubeDeploymentLowAvailability` alert.  Its PromQL aggregates container
restarts across pods belonging to the same Deployment via the existing
`namespace_workload_pod:kube_pod_owner:relabel_nd` recording rule and keys the
alert at Deployment level; this directly addresses pod replacement under
stable owner grouping.  Its README additionally discusses a
`max_over_time((...)[30m:1m])` wrapper to bridge short gaps, explicitly noting
the trade-off of delayed resolution.  The chart also applies `max_over_time`
to crash-loop observability.  These are **not new ideas introduced by N06**.

- Commit checked: `804668b33a820b576653afbc120c06672b3bb4ae`
- https://github.com/Nextdoor/k8s-charts/blob/804668b33a820b576653afbc120c06672b3bb4ae/charts/prometheus-alerts/README.md
- https://github.com/Nextdoor/k8s-charts/blob/804668b33a820b576653afbc120c06672b3bb4ae/charts/prometheus-alerts/templates/containers-prometheusrule.yaml

The work to differentiate is **not** generic owner aggregation or generic
lookback.  A potentially distinct contribution is certified owner/release
linking plus external probe veto of false continuity, under incomplete owner
metadata, with careful failure semantics and measured SRE costs.  None of this
is established as novel by the synthetic benchmark alone.

## 3. Other relevant original sources

- **Kubernetes Mixin owner recording rule** already traverses
  Pod → ReplicaSet → Deployment and exposes
  `namespace_workload_pod:kube_pod_owner:relabel`.  It is a stronger, widely
  relevant owner-based alternative than Pod-instance alerts:
  https://monitoring.mixins.dev/kubernetes/
- **Kubernetes Mixin discussion #1247 (2026)** documents owner
  aggregation and discusses downstream `last_over_time` staleness handling.
  This is a discussion of a proposed lower-cardinality enhancement, not proof
  that the enhancement was merged:
  https://github.com/kubernetes-sigs/kubernetes-mixin/issues/1247

- **kube-prometheus TargetDown**: actual service-level grouping already
  exists; the original rule `100 × count(up==0)/count(up) > 10` is keyed by
  cluster, job, namespace and service and uses `for: 10m`.
  https://github.com/prometheus-operator/kube-prometheus/blob/d88939bfbe7ffa368a62dcc1ff477b1c19fa9674/jsonnet/kube-prometheus/components/mixin/alerts/general.libsonnet
- **Fractal Techware PodNotReady**: this independently maintained rule uses
  pod labels and `for: 15m` and has public positive/negative promtool cases.
  https://github.com/Fractal-Techware/prometheus-alert-rules/blob/3e61642f0dbbcab5a4fae1c830962fe8cd009c29/rules/kubernetes-workloads.rules.yml
- **Validating Alerts in Cloud-Native Observability** (Borges et al., 2025):
  a pre-existing Kubernetes observability fault-injection and alert-validation
  approach; rule testing in realistic injected systems is not new.  Its
  study uses OXN and a cloud-native microservice demo.
  https://fb-swt.gi.de/fileadmin/FB/SWT/Softwaretechnik-Trends/Verzeichnis/Band_45_Heft_4/SSP25_paper_24.pdf
- **Kubernetes official kube-state-metrics documentation** explains owner and
  readiness metadata: https://kubernetes.io/docs/concepts/cluster-administration/kube-state-metrics/
- **Prometheus alerting practice** recommends alerts aligned to end-user pain,
  rather than firing solely on low-level causes:
  https://prometheus.io/docs/practices/alerting/

## 4. Honest novelty boundary

The first screening ZIP said no complete matching paper was found in its
limited search.  That does **not** demonstrate novelty.  The later Nextdoor
chart materially narrows any plausible novelty.  There has been no systematic
60–200-paper/library sweep in this deliverable, and no assertive claim of a
novel method should appear in a camera-ready manuscript until independent
source-search and real-system experimental evidence are secured.

The Mixin recording rule and the 2026 issue further narrow the claimed
industrial contribution. See `INDUSTRY_NOVELTY_BOUNDARY.md` for the mandatory
matched-baseline design and the currently plausible, unverified novelty.
