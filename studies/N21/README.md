# N21 — Incomplete TypeScript Output Recovery: FSE 2027 Industry Experiment Package

This directory contains newly executed, auditable experiments expanding the
user-provided `FSE2027_4_ideas.zip` Idea **N21**. It is a research replication
package, **not evidence of industrial deployment**.

**New real runner validation (2026-11-18):** Three independent GitHub Actions
runs in the user's isolated [FSE-EXP-1 repository](https://github.com/shjdjjfi/FSE-EXP-1)
executed real `Attest/typescript-cache-action` restores in 45 hosted jobs,
producing 42 validated strategy/fault observations and full logs. The
experimental faults were deliberate; this is **not** a production incident
sample or observed incidence denominator. See `results/github_actions_aggregate.md`.

## Scientific scope

The object is recovery from incomplete or changed emitted files while an
incremental compiler may retain `.tsbuildinfo`. We test three distinct questions:

1. **Detection and correctness:** When does a nominally successful build leave
   output different from an independent clean compilation?
2. **Cost and configuration:** When do project-selective recovery, full clean,
   forced build, a real Wireit cache, and a real Turborepo cache work? Which
   project-reference edges reduce local savings?
3. **Safety boundary:** What fails if the prior output manifest is trusted
   across changed inputs, including changes whose file times are backdated?

**All fault injections are experimental**, not natural CI incidents. The public
issue catalog does not estimate fault prevalence. The comparison with full-cache
restore assumes a **complete, correct cache entry already exists**, rather than
assuming every workflow can obtain one.

## Provenance / subjects

- Real source snapshots of `ts-pattern@5.8.0`, `zod@3.25.76` (v3 only),
  `neverthrow@8.2.0`, and `mitt@3.0.1` are placed in one **constructed**
  multi-project TypeScript workspace to study the local recovery decision.
  The source files themselves are not fabricated, but their shared workspace
  and compilation configuration are experimental. `neverthrow` uses its
  upstream `strict:false` compatibility setting.
- `andrewthauer/ts-monorepo` at commit
  `4250b1ad404027b5f7f2637be79bac61164602fa`: native project-reference
  configuration (`core`, `api`, `cli`, `web`); small illustrative repository.
- `Quramy/npm-ts-workspaces-example` at commit
  `3fa93f092298cfb6be302d9d2eb10a411f4ae3fe`: native references
  (`x-core`, `x-cli`) with dependencies installed using `npm ci --ignore-scripts`;
  small illustrative repository.
- `microsoft/TypeScript` source tag `v5.9.3`: the native
  `compiler -> jsTyping -> services` reference subgraph, with the upstream
  diagnostics generator run first, then TypeScript `5.9.3` used to compile
  declaration outputs. This is a real, much larger source tree.
- Separate genuine TypeScript compiler API reproductions use 5.9.3 and 6.0.2,
  with an artificial minimal TypeScript program, following a public Nest CLI
  failure report.

Source URLs and archive SHA-256 hashes are **pinned** in `run_n21.py`, and the
TypeScript 6 tarball digest is in `run_api_probe.py`. Re-downloading the
archives and recomputing hashes is supported. No third-party source snapshots,
`node_modules`, or generated compiler-output trees are included in the ZIP.

## Strategies and observable measures

| Strategy | What actually runs | Caveat |
|---|---|---|
| `standard` | Unforced `tsc -b` | Can exit 0 without repairing a file |
| `selective_path` | Compare declared paths, invalidate selected `.tsbuildinfo`, `tsc -b` | Cannot detect silent byte corruption |
| `selective_hash` | Compare SHA-256 output manifest, invalidate selected `.tsbuildinfo`, `tsc -b` | Only valid if all relevant inputs match manifest |
| `guarded_hash` | Validate source/config/lock content key, then perform hash-selective recovery | **Fail closed** to clean build if input key differs; deployment needs full environment/dependency key |
| `invalidate_all` | Remove all incremental metadata, unforced `tsc -b` | Can preserve unexpected extra output files |
| `clean_all` | Remove each project's output directory and build metadata, then `tsc -b` | Strong correctness comparator; always pays clean-build cost |
| `force_all` | Whole solution with `tsc -b --force` | Forces rebuilding but may preserve old extra output files |
| `full_cache` | Copy complete, verified prior snapshot (output and metadata) | An **available-cache** upper bound, not a method for missing caches |

All fault-free controls must produce zero differing emitted files, including
their paths and SHA-256 values. The independent clean compiler is run **before**
injecting faults; its result is **not used** by the recovery strategy.
Expected outputs exclude `.tsbuildinfo`, which is compiler state rather than
emitted deliverable content, even if located inside the output directory.

The `compiled_source_units_proxy` is the sum of TypeScript source-file counts
for projects explicitly logged by the compiler as rebuilt. It is **not** a
count of emitted machine instructions, CPU cycles, or individual compiler
subtasks. Both wall time and source-unit proxies are recorded. Wall timings are
for this shared research environment and are exploratory, not industrial CI
time saved. All repetition/seed-level records are clustered within repos.

## Environment and reproduction

Tested in November 2026 under Linux, Node 24, npm 11, Python 3.12,
TypeScript 5.9.3 and 6.0.2. For exact environment versions, see
`metadata/environment.json` in the packaged result.

To regenerate the *entire* matrix, execute `bash REPRODUCE.sh` with a working
internet connection. It makes a new private temporary working directory,
copies the scripts there, downloads pinned inputs, and leaves the archived
results untouched. Download/execution can take substantial time. Python 3.12+
is recommended. Individual commands are also supported; example:

```bash
python3 run_n21.py prepare --cases libraries,andrewthauer,quramy,typescript
python3 run_n21.py run --cases libraries,andrewthauer,quramy \
  --faults delete_nested_js,delete_entry_js,delete_dts,corrupt_js,corrupt_dts,extra_stale,erase_dist,intact,buildinfo_missing --seeds 17
python3 run_n21.py run --cases typescript --results results/typescript \
  --faults delete_dts,corrupt_dts,extra_stale,intact --seeds 17
python3 run_n21.py run --cases libraries,andrewthauer,quramy \
  --results results/guarded --arms guarded_hash --seeds 17
python3 strong_baselines.py
python3 turbo_baseline.py
python3 run_api_probe.py
python3 input_drift_probe.py
python3 version_holdout.py
python3 audit_public_issues.py
python3 analyze_n21.py
python3 validate_results.py
python3 paper_tables.py
python3 robustness_stats.py
python3 figures_n21.py
```

To reproduce the additional random-position checks, use the `--projects`,
`--faults`, `--arms`, and `--seeds 29,43` flags; see `results/all_trials.csv`
for the exact executed grid. The runner can **resume** a partially completed
grid from JSONL without repeating completed keys.

`version_holdout.py` builds a **fresh independent TypeScript 6** oracle; it
does not incorrectly compare TypeScript 6 output digests against TypeScript 5.
The original upstream source files and our compiler options are recorded;
no experiment modifies third-party repositories in place.

## Evidence audit

- `results/**/trials.jsonl` (new runs): per-trial commands, tool stdout/stderr,
  target, corruption type, before/after digest discrepancies, elapsed time and
  rebuilt-project lists.
- `metadata/*.json`: source-unit counts, emitted-file counts and **complete
  reference SHA-256 manifests**; independent clean compile logs and checks.
- `results/analysis.json`, `results/all_trials.csv`, and
  `results/EXPERIMENT_REPORT.md`: recomputed summaries, not hand-entered data.
- `results/public_issue_audit.json`: seven linked primary-source case notes,
  including two adjacent but **out-of-scope** failure mechanisms.
- `results/wireit/observations.json` and
  `results/turborepo/observations.json`: actual tool executions under different
  availability conditions, not idealized performance assumptions.
- `results/turborepo/misconfigured_outputs_in_inputs.json`: **excluded
  configuration ablation**. Without explicit inputs in this artificial
  non-git fixture, changed outputs invalidated the cache key, so those runs
  must not be described as correctly configured Turborepo cache hits.
- `results/api_incremental_probe.json`, `results/input_drift_probe.json`,
  `results/version_holdout.json`: supplementary mechanistic and safety checks.
- `results/VALIDATION_REPORT.json` checks exact coverage of all 920 archived
  main/guard/sensitivity trials, duplicate keys, expected outcomes and
  supplementary evidence.
- `results/public_ci_observability.json` is a **separate read-only audit** of
  all 17 scheduled GitHub-hosted runs of Wireit's real cache-service workflow
  on Nov. 1–17, 2026. All 17 logs reported successful cache regression tests
  and npm dependency cache hits. This cohort has **no emitted-file integrity
  label**, so its 17-run denominator is NOT an N21 incident-rate denominator.
- `results/public_ci_incident_evidence.json` distinguishes an actual
  first-person historical CI complaint from a complete verifiable incident.
  It contains one qualitative natural report, **zero** cases with complete
  natural CI job logs/output manifests, and **no** N21 incidence denominator.
- `github_actions/n21-attest-benchmark.yml` and `gha_n21.py` were executed
  with the **actual pinned Attest save/restore actions** on GitHub-hosted
  Ubuntu 22.04 runners three times. Runs: [44237916114](https://github.com/shjdjjfi/FSE-EXP-1/actions/runs/44237916114),
  [44238758566](https://github.com/shjdjjfi/FSE-EXP-1/actions/runs/44238758566),
  [44238773494](https://github.com/shjdjjfi/FSE-EXP-1/actions/runs/44238773494).
  These include 45 successful runner jobs, 42 independently checked result
  records, 45 full raw logs and original runner artifact archives.
- `github_actions/analyze_gha.py`, `results/github_actions_aggregate.md`,
  `.json`, `.csv`, and `results/github_actions_run_<ID>/` document exact
  evidence and small-fixture cost sensitivity. Pilot [44237397496](https://github.com/shjdjjfi/FSE-EXP-1/actions/runs/44237397496)
  is excluded from timing because generated declarations were incorrectly
  included in input fingerprints in the original runner harness.
- `results/PAPER_TABLES.md`, `.tex`, `results/ROBUSTNESS.md`, and
  `figures/*.svg`: paired publication-ready descriptive tables, sensitivity
  checks and vector figures regenerated from trial JSON.
- `N21_SUBMISSION_EVIDENCE.md`: Chinese end-to-end research report and
  explicit Industry-track evidence gaps.
- `EXCLUSIONS.md`: transparently records one unsupported initial injection,
  12 invalidated first-pass TypeScript records, and an excluded misconfigured
  Turborepo fixture, all separate from audited main observations.

## Limits to any FSE Industry publication claim

No complete **naturally occurring industrial CI incident** logs or production
cache manifests were supplied. The archived 45 GitHub Actions job logs are
real but arise from an isolated researcher-created fixture.
Public GitHub issues validate plausibility and mechanism, **not incidence or
general workload frequency**. No independent industrial deployment, engineer
time study, real business cost, or production-scale speedup has been measured.
The results can support a carefully scoped *conditional repair / limits of
measurement* empirical paper; they do **not** establish a general positive
ROI for deploying a new recovery gate or outperform a working complete cache.

For requirements and evaluation criteria, use the official
[FSE 2027 Industry Track call](https://conf.researchr.org/track/fse-2027/fse-2027-industry-papers).

