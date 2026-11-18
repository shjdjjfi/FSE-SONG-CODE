# N06 — Preserving Service-Level Alert Timing Across Metric Identity Churn

**Status: research prototype / controlled mechanism study; NOT an FSE submission-complete empirical result.**

**2026-11-15 field-readiness update:** An additional read-only capture,
Alertmanager first-hop receiver, authenticated pager-receipt analysis,
live-process resource sampler, native field-case exporter, independent-cluster
gate and GitHub Actions native `promtool` workflow have been added under
`field_capture/` and `.github/`. The local Python test suite has 25 tests.
These additions do **not** constitute executed experiments on two real
Kubernetes clusters. The native N06 test on this machine remains
`NOT_EXECUTED`; the actual native CI pass located is for the **upstream rule
repository only**. The field gate remains `BLOCKED`. See
`paper/NEW_FIELD_EVIDENCE_AUDIT.md` and `field_capture/README.md`.

This reproducibility package evaluates *what happens if* a service has a
continuous owner-scoped outage but the monitored pod/metric fingerprint changes.
It also models actual recoveries, missing owner metadata, late rollout events,
silence without rollout, and two unrelated owners reusing a service name.

The upstream repositories provide **real public alert definitions and tests**.
The 1,980 primary event traces are **synthetically generated**; there are **zero
independent production rollout+probe traces** here.  No native `promtool` run
was possible on this execution machine, and no number in the tables is an
observed production accuracy estimate.

## Read first

1. `paper/EXPERIMENT_PROTOCOL.md`: design, ground truth, evaluation units.
2. `results_v2/TABLE_1.md`: frozen primary model-only numerical results.
3. `results_v2/submission_gate.json`: explicit pass/fail publication gate.
4. `paper/RESULTS_AND_LIMITATIONS.md`: full interpretation and failure modes.
5. `paper/PRIOR_ART.md`: a newly located owner-aggregation precedent.
6. `paper/INDUSTRY_NOVELTY_BOUNDARY.md`: Mixin/Nextdoor baseline audit and
   honest remaining research question.
7. `results_field/`: measured LOCAL synthetic Python microbenchmark and
   machine-verifiable negative results for missing native/field evidence.

## Data and independent source versions

| Purpose | Source | Pin | Artifact |
|---|---|---|---|
| Stable service aggregation (`TargetDown`, `for: 10m`) | [kube-prometheus](https://github.com/prometheus-operator/kube-prometheus) | `d88939bfbe7ffa368a62dcc1ff477b1c19fa9674` | `sources/kube_prometheus_general.libsonnet` |
| Pod-specific readiness (`KubePodNotReady`, `for: 15m`) | [Fractal Techware](https://github.com/Fractal-Techware/prometheus-alert-rules) | `3e61642f0dbbcab5a4fae1c830962fe8cd009c29` | `sources/ftw_kubernetes_workloads.rules.yml` |
| Public authored promtool tests | same Fractal repository | same commit | `sources/ftw_kubernetes_workloads.test.yml` |
| Prior art: Deployment aggregation and `max_over_time` | [Nextdoor Prometheus alerts](https://github.com/Nextdoor/k8s-charts/tree/804668b33a820b576653afbc120c06672b3bb4ae/charts/prometheus-alerts) | `804668b33a820b576653afbc120c06672b3bb4ae` | citation and audit, *not* a copied file |

These two upstream rule projects provide source-configured **duration profiles**;
they are *not* two independently observed real operational systems.  In
particular, the simulated service-outage contract is NOT the exact `TargetDown`
ratio rule or the exact pod-specific `KubePodNotReady` intent.  `targetdown10`
approximates the `>10%` threshold.  All modeled policies run on the same
observable trace.  See `paper/EXPERIMENT_PROTOCOL.md`.

## Reproduce the frozen primary comparison

Tested with Python 3.12, PyYAML, NumPy, and Matplotlib.  One CPU machine is
sufficient; no GPU, cloud API, SSH credentials, Docker, or Kubernetes cluster
is used for the controlled benchmark.

```bash
python3 -m pip install -r requirements.txt
python3 -m unittest discover -s tests -v
python3 src/run_experiments.py --replicates 30 --seeds 17,29,43 --output reproduced_primary
```

The frozen primary output from the *pre-v2* phase lives at `results_v2/`.
The code also contains the transparently marked **post-hoc** policy
`owner_relink_v2`; therefore a fresh run additionally emits this v2 policy.
Filter it out of a fresh run to reproduce the earlier 10-policy primary table.
Random seeds and scenario-generating code for the original 10 policies have
not been changed, and no tuning is performed during either replay.

## Reproduce the exploratory, new-seed validation of v2

```bash
python3 src/run_experiments.py --replicates 30 --seeds 101,211,307 --output reproduced_v2
```

The v2 variant was proposed **after** seeing the original 17/29/43 seed
diagnostics.  Its new 101/211/307 seeds are a fresh *synthetic* evaluation, not
an independent Kubernetes holdout or field replication.

## Prometheus native validation (not executed here)

```bash
python3 src/export_promtool_cases.py
python3 src/validate_promtool_fixtures.py
bash scripts/run_native_promtool.sh
```

`promtool/tests.yml` contains four handcrafted rule-unit cases; the generated
owner-relink fixture includes two further synthetic cases.  The Python
checker checks seven handcrafted assertions in a small restricted evaluator;
it is **not** a replacement for PromQL evaluation.  Only the last command,
with an installed official `promtool`, actually tests the native rules.  It
exits with code 2 if the executable is missing; do not count such a skip as a
test pass.  The `promtool` rule is only a consumer of synthetic, externally
constructed `n06_owner_unavailable` samples: the new **untested field**
`owner_exporter.py` is a separate read-only polling prototype, not evidence
of a working production exporter.

An official-version Docker GitHub Actions workflow is in
`.github/workflows/n06-native-promtool.yml`. It has not been triggered on this
package here. `python3 field_capture/native_evidence.py` emits a
`NOT_EXECUTED` report if no `promtool` binary is installed. For actual field
tests, the capture and native exporter protocol is in `field_capture/README.md`.

## Results and paths

- `results_v2/raw/synthetic_traces.jsonl.gz`: fully auditable synthetic
  observations **including a separate evaluation-only oracle**.  The oracle is
  never passed to a policy.
- `results_v2/raw/paired_policy_results.csv`: one policy row per episode;
  paired comparisons use an identical frozen trace.
- `results_v2/summary.csv`, `family_results.csv`, `seed_results.csv`:
  overall and stratified numerical tables.
- `results_v2/grace_sensitivity.csv`: 0 to 180 seconds carry window sensitivity
  on 1/5 of each synthetic stratum.
- `results_v2/paired_mc_intervals.csv`: purely Monte Carlo intervals conditional
  on the generator and scenario families, **not** confidence intervals for
  industrial deployments.
- `results_v2/figures/`: source plots.
- `results_v2/submission_gate.json`: explicit missing field-validation gates.
- `exploratory_holdout/`: v2 analysis on new random seeds.
- `results_field/`: current local cost microbenchmark and explicit blocked
  native/real-incident evidence gates. All measured costs here are local Python
  processing of synthetic input; no production CPU or paging result exists.

The exact source SHA-256s and software environment are in
`results_v2/source_evidence.json` and `results_v2/run_manifest.json`.

## Publication integrity constraints

- **Never describe simulation successes or synthetic fault labels as real
  Kubernetes failures, production recall, or observed SRE incidents.**
- **Never call a restricted model test a `promtool` test pass.**
- **Never claim two actual deployments were evaluated merely because two
  independently maintained YAML rule repositories were read.**
- For actual submission: collect consented/appropriately public independent
  incident traces with pod UIDs, owner relations, rollout times, query results,
  probe health and timestamps; run native Prometheus evaluation, hold out a
  project, test Alertmanager page delivery and processing overhead; see
  `paper/SUBMISSION_BLOCKERS.md`.
- Actual Nextdoor Deployment aggregation and the Kubernetes Mixin owner rule
  predate this experiment. A new algorithm name does not establish novelty.

The upstream source snapshots have their original licenses stored under
`sources/`. The generated work in `src/`, `scripts/`, `paper/`, `promtool/`,
and `results_v2/` is original to this experiment package.
