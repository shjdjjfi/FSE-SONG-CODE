# Real-system data availability and native-engine evidence audit

Research checkpoint: 2026-11-15. No independent cluster logins, monitoring
endpoints, incident ground truth, or pager-provider credentials were supplied
for this run. All independently generated traces in `results_v2/` and
`exploratory_holdout/` remain **synthetic**.

## A. Public datasets screened for two independent field replays

| Original source | What is public / useful | What is absent for a valid N06 field replay | Eligibility |
|---|---|---|---|
| [ssepin/edge-fault-dataset](https://github.com/ssepin/edge-fault-dataset) | Genuine edge application fault-injection metrics in Kubernetes; QoS and failure measurements for two apps | Cannot join recorded Pod/ReplicaSet/Deployment UIDs, rollout events, native alert instances and actual page receipts from the published CSV columns | **Not sufficient** |
| [hkerma/kubernetes-event-dataset](https://github.com/hkerma/kubernetes-event-dataset) | Real Kubernetes audit/event logs | No timestamp-joined independent HTTP service probe, Prometheus vectors or actual Alertmanager/pager receipts for these particular events | **Not sufficient** |
| [ilyasstrh/k8s-failure-dataset-generator](https://github.com/ilyasstrh/k8s-failure-dataset-generator) | Published pod/cluster metrics CSV; also explicitly synthetic generation outputs | No complete independently observed Pod UID → stable owner UID + rollout → probe → pager event correspondence | **Not sufficient** |
| [nixwl/KubeWatch](https://github.com/nixwl/KubeWatch) | Public tooling to generate/monitor Kubernetes workloads | Repository describes collecting private data; published repository does not provide the full joint public telemetry needed for this test | **Not sufficient** |

The above is a limited source audit, not a proof that such a dataset is
nowhere publicly available. Multiple workloads within one cluster do not
automatically constitute **two independent real Kubernetes systems**.
Combining different unrelated projects' timelines cannot yield a true single
incident replay or a legitimate estimate of alert delivery latency.

## B. Native Prometheus provenance

The **upstream** Fractal Techware public `promtool` workflow ran on
2026-10-09, GitHub Actions run `37984114650`, job `114001666301`, commit
`3e61642f0dbbcab5a4fae1c830962fe8cd009c29`. Retrieved CI logs show:

```
==> promtool check rules (3 files)
SUCCESS: 1 rules found
SUCCESS: 6 rules found
SUCCESS: 7 rules found
==> promtool test rules (3 files)
SUCCESS
SUCCESS
SUCCESS
```

Workflow: https://github.com/Fractal-Techware/prometheus-alert-rules/actions/runs/37984114650

This proves **upstream authored rules** passed native Prometheus tooling on
that run. It is **not** a native test of the N06 candidate, nor two real
cluster experiments. The local N06 attempt in
`results_field/native_attempt/native_test_report.json` exits with code `2`
and status `NOT_EXECUTED`, because this machine lacks the official executable.

The package now supplies an offline and GitHub Actions native test route using
the official Prometheus 3.16.0 release image (published 2026-11-04) and a
generator for native tests on truly captured fields. Neither route has been
run for this candidate in this environment.

Sources:

- https://prometheus.io/download/
- https://prometheus.io/docs/prometheus/latest/configuration/unit_testing_rules/
- https://github.com/prometheus/alertmanager/blob/main/docs/configuration.md

## C. Actual measured cost (local Python simulation only)

`results_field/local_python_benchmark.json` records actual Python wall time
and tracemalloc allocation peaks **on a local, synthetic, in-memory series**.
It is not measured from Prometheus, Kubernetes, Kubernetes event watches, or
production alerting processes. It does not represent alert send times,
incremental Prometheus CPU/RSS, or operator paging burden. Use only in an
implementation scalability appendix, and disclose the prototype nature.

## D. Evidence needed to close four specified gaps

1. **Two real systems:** obtain two different `kube-system` namespace UID hashes
   and timestamp-aligned Kubernetes object/event, Prometheus and independent
   service-probe streams; freeze real incident annotations independently.
2. **Native engine:** execute an official pinned `promtool` binary or container,
   preserve version, stdout, exit code, rule hash and actual inputs from each
   real system; separately replay live Prometheus rules and Alertmanager.
3. **Delivery/false pages/cost:** observe actual Alertmanager webhook arrival
   and authenticated paging-provider arrival, healthy control windows, real
   recovery, Prometheus rule-evaluation/cardinality metrics and candidate's
   incremental CPU/RSS under equal loads.
4. **Industrial novelty:** compare against the exact Nextdoor Deployment rule,
   Kubernetes Mixin owner-rule with appropriate lookback, service-level ratio,
   probe-only alert, and true recovery controls. Pre-register tolerable
   additional pages/recovery delays; provide per-project results with
   cluster/event-level uncertainty.

**Submission verdict: BLOCKED.** Do not claim any of the four user-requested
real-world components as completed solely on the basis of this package.
