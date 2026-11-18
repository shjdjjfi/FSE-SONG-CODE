# N06 — Explicit completion gate for FSE Industry

This is a **fail-closed checklist**. Completed controlled simulation is not
equivalent to completing the paper's required field experiments.

| Required evidence | Status in this package | How to close and verify |
|---|---|---|
| Source-backed public rule profiles | DONE (2 independent repositories) | SHA-frozen files and upstream-authored tests in `sources/` |
| Reproducible CPU-only controlled mechanisms | DONE | 1,980 original + 1,980 separate v2 synthetic episodes; 14 Python tests |
| Strong baselines and negative controls | DONE in simulation only | service+grace, ratio+grace, owner+lookback, probe-only, no-probe, no-event and true recovery |
| Source-independent production telemetry | **MISSING**; collection/audit code ADDED | Acquire 2+ actual projects' time-aligned pod/owner/controller UIDs, rollout/audit events, Prometheus query results and independent black-box probes; use `field_capture/collector.py` and `audit.py` |
| Frozen outage and recovery ground truth | **MISSING** | Label real incidents independently of candidate and baseline metric expressions; blind annotators / operator corroboration |
| Native Prometheus / promtool evaluation | **N06 NOT EXECUTED**; upstream CI native pass verified | Official native `promtool` on candidate hand-authored AND real field fixtures, preserve logs/versions; run live Prometheus+Alertmanager |
| Faithful implementation of owner association | **EXPERIMENTAL POLLING EXPORTER WRITTEN, FIELD UNTESTED** | Validate `field_capture/owner_exporter.py` on real Pod→ReplicaSet→Deployment UID joins, event age and probe-veto semantics; replace polling with reliable informer architecture |
| Holdout of actual independent system | **MISSING** | Pre-register and freeze method on project A and test untouched project B; use project/event clustered CIs, not synthetic-seed MC intervals |
| Alertmanager delivery outcome | **MISSING**; isolated test receiver and analysis ADDED | Measure both first-hop webhook receipt and external paging-provider actual delivered page, false resolution, repeated page and recovery |
| Cost, scale, failure injection | **LOCAL SYNTHETIC COST ONLY**; live PID sampler ADDED | CPU, memory, event backlog, owner graph retention, 10k–100k pods and schedule jitter; benchmark under real monitoring load |
| Novelties against available solutions | **NOT CLEARED**; Mixin owner-rule precedent ADDED | Compare exact Nextdoor Deployment alert plus `max_over_time`, Kubernetes Mixin owner-relabelling and `last_over_time` lookback; document true difference |
| Industrial decision impact | **NOT MEASURED** | Prespecified actionable reduction in missed pages / extra pages, and operator-defined severity thresholds with project-level uncertainty |

## Suggested field protocol (not executed)

1. Choose two independent public/consented Kubernetes projects with actual
   rollout timing, owner-controller identifiers, 15–60 s scrape samples,
   black-box request probes and read-only issue/incident annotations.
2. Freeze cases **before** examining candidate outcomes: include persistent
   failure + pod rotation, independent failure, genuine healing, same-name
   owner reuse, missing owner links, deployment scaling and healthy rollout.
3. Capture the raw PromQL expression output vectors, labelsets, scrape gaps,
   staleness, Alertmanager notifications and delivery times.  Replay the
   *unchanged original rules* as well as appropriately adapted contract rules.
4. Run a native Prometheus engine with known version, record a checkable
   `promtool` version output, and preserve the complete stdout/exit status.
5. Implement and freeze v2 based on development project only.  Compare with
   service aggregation, exact published owner aggregation, `max_over_time`
   gap smoothing, probe-based alerting and original unmodified rules.
6. Report per-project decision impact, sensitivity to missing events, on-call
   false page and true resolution delays, and project/event-clustered
   intervals.  If owner+lookback is equal or better, record a negative result
   and stop or reframe the work.

## Resource limitation observed in this task

`promtool` was not present, no Go compiler or local container/Kubernetes
runtime was installed, and an attempted download of the official release
binary timed out in this environment.  A restricted Python check of test
fixtures passed, but it is not evidence that the fixtures passed native
PromQL evaluation.  The publicly located artifacts did not include the
joint time-series/owner/rollout/probe observations needed to make a
production false-page claim.  This is a transparent execution blocker, not
an assertion that such datasets do not exist anywhere.

**Update 2026-11-15:** `field_capture/` now includes end-to-end read-only
capture, Alertmanager webhook logging, provider receipt analysis, live PID cost
sampling, synthetic-to-native separation and strict data gate. The automatic
gate report in `results_field/field_evidence_gate.json` remains `BLOCKED`,
and the native runner report in `results_field/native_attempt/` remains
`NOT_EXECUTED`. One upstream Fractal Techware GitHub Actions workflow passed
**its own** native promtool tests, not this package's tests. The public-source
eligibility and stronger prior-art checks are fully documented in
`NEW_FIELD_EVIDENCE_AUDIT.md` and `INDUSTRY_NOVELTY_BOUNDARY.md`.

**Overall decision: do not describe N06 experiments as submission-complete.**
