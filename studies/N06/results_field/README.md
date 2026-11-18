# N06 field-readiness result status (2026-11-15)

| Experiment | Status | Evidence in this folder |
|---|---|---|
| Two independent actual Kubernetes systems | **NOT RUN / ZERO REAL SYSTEMS** | `field_evidence_gate.json` has status `BLOCKED` |
| Native N06 Prometheus/promtool evaluation | **NOT EXECUTED HERE** | `native_attempt/native_test_report.json` has status `NOT_EXECUTED`, exit 2 |
| Genuine Alertmanager first-hop and authenticated page delivery | **NOT RUN** | Receiver and analysis scripts exist under `field_capture/`, but no real records were provided |
| Real field false pages and resolved alerts | **NOT MEASURED** | Requires independently adjudicated real incident and healthy windows |
| Actual production CPU/RSS | **NOT MEASURED** | A live PID sampler exists; no candidate or baseline processes were running |
| Industrial advantage over published exact Deployment owner baselines | **NOT ESTABLISHED** | `paper/INDUSTRY_NOVELTY_BOUNDARY.md` documents prior art; only synthetic comparisons exist |

## One completed local *synthetic* cost measurement

`local_python_benchmark.json` contains an actual local wall-clock and
`tracemalloc` allocation measurement on constructed, synthetic in-memory Pod
objects; **not** a measured cluster, PromQL/TSDB or notification overhead.
One run per policy/scale, 12 state updates per policy, Python 3.12.14:

| Synthetic Pods | Owner-lookback Python seconds | N06 v2 Python seconds | Owner-lookback peak Python allocations MB | N06 v2 allocations MB |
|---:|---:|---:|---:|---:|
| 1,000 | 0.0073 | 0.0057 | 0.0098 | 0.0434 |
| 10,000 | 0.1310 | 0.1241 | 0.0962 | 0.3454 |
| 100,000 | 1.4084 | 1.5988 | 0.9509 | 6.3369 |

At 100k constructed Pod observations, N06 v2 was about 13.5% slower than
the simplified owner-lookback model **in this single local run**. Allocations
exclude the pre-created Pod input objects. They are *not* process RSS. The
result is a reason to test overhead under native Prometheus; not evidence of
industrial efficiency.

## Machine and artifact integrity

- The **25** unit tests exercise Python continuity, UID matching, input
  sanitization, webhook timestamp handling, exporter behavior and strict
  evidence failure. They do not test real Kubernetes calls.
- The previous `results_v2/` and `exploratory_holdout/` mechanism studies
  are unchanged and synthetic.
- Source licenses and pinned source rules are in `sources/`. The ZIP package
  includes a SHA-256 manifest.

**Submission verdict remains FAIL.** New scripts enable collection when the
required systems and authorized telemetry are provided, but they cannot
retroactively generate authentic production evidence.
