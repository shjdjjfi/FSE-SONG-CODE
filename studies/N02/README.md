# N02 — Helm Upgrade Configuration Intent: CPU Reproducible Experiment Package

**First read (latest):** [Phase-3 Chinese audit](phase3/EXPERIMENT_REPORT_PHASE3_CN.md) /
[Phase-3 English paper-results supplement](phase3/PAPER_RESULTS_PHASE3_EN.md) /
[AI expert desk audit—NOT a human study](phase3/AI_EXPERT_DESK_AUDIT_CN.md).
Previous rounds: [Phase-2 Chinese audit](phase2/EXPERIMENT_REPORT_PHASE2_CN.md) /
[Phase-2 English paper-results supplement](phase2/PAPER_RESULTS_PHASE2_EN.md).
The original [Phase-1 Chinese audit](EXPERIMENT_REPORT_CN.md) and
[Phase-1 English Results](PAPER_RESULTS_EN.md) are retained without retroactive edits.

**State of the research:** Phase-3 external challenge confirms **6 additional
manifest-level failures in 3 Chart families**, detected 3/6 by unchanged CID,
plus 3 external controls and 1 unrenderable candidate. The previous 72
negative controls remain; CID's aggregate false-alert tally is 0/75. Nine
more authentic helm-diff-plugin calls were performed on *synthetic* historical
Release Secrets. A documentation-independent schema scan separately found two
additional verified *exploratory* Loki losses (not pooled into the six-case
confirmatory count). **No real Kubernetes Pods, actual human reviewer minutes,
or ≥15 pp advantage over docs+native-diff were demonstrated.** This is still
**NOT** a complete FSE 2027 Industry Track experiment.

### Phase-3 executed evidence

| Test | Outcome |
|---|---|
| Predeclared documentation-informed candidates | 10 = 6 manifest positives + 3 controls + 1 invalid |
| Frozen CID on 6 positives | 3/6 (50%) |
| Simple missing-key baseline on 6 positives | 3/6 (50%); CID advantage 0 pp |
| Combined Phase-2/Phase-3 controls | CID 0/75 false flags |
| Native helm-diff vs synthetic historical Releases | 9/9 plugin runs; 6,110 normalized diff lines |
| Automated schema-only exploratory discovery | 6 old-only string paths; 4 lost sentinels; 2 novel verified positive contracts |
| Actual independent human reviewers | 0; no review-minute data |

After installing the toolchain (below), verify Phase 3 and regenerate the
numerical outputs from the package root with:

    python3 phase3/verify_phase3.py
    python3 phase3/run_external_challenge.py
    python3 phase3/native_diff_external.py
    python3 phase3/analyze_external.py
    python3 phase3/schema_blind_probe.py
    python3 phase3/validate_blind_discoveries.py

The `phase3/` directory also contains the exact chart version archives,
predeclaration, source SHA-256 audit, complete native-diff transcripts and
qualitative AI review. Those AI notes must not be passed off as human data.

### Prior Phase-2 executed evidence (historical)

### Phase-2 executed evidence

| Test | Outcome |
|---|---|
| Preregistered external families | 8; 6 evaluable, 2 documented exclusions |
| External values | 72 stable / 0 silent value loss |
| CID on external controls | 0/72 false alerts; sensitivity not estimable |
| Old-defaults reuse emulation on external controls | 72/72 preserve unique literal |
| Actual helm-diff plugin over synthetic Helm v3 Secret | 27/27 default, 27/27 normalized/context-3 |
| Native Pods or in-cluster Helm upgrades | 0; cluster infrastructure unavailable |
| Genuine reviewer-time observations | 0; instrumentation ready but no people participated |

Run offline:

    python3 scripts/verify_results.py
    python3 phase2/verify_phase2.py

The phase2/ folder contains the fixed preregistration, 14 additional original
chart packages, source-hash audit, raw plugin transcripts, full summaries,
candidate-selection logs, a guarded real-cluster replay harness, and a
randomized human-review stopwatch. See
[Phase-2 report](phase2/EXPERIMENT_REPORT_PHASE2_CN.md) for precise limitations,
application probes, run commands, and submission stop conditions.
To re-install the exact native comparison tool after unpacking: first
run the existing Helm bootstrap script, then
run phase2/bootstrap_diff_plugin.sh for the pinned helm-diff v3.12.0 plugin.

## Frozen result snapshot

| Check | Recorded result |
|---|---|
| Genuine public chart packages | 10 releases / 5 families |
| Helm version | v3.17.0 |
| Helm lint | 10/10 pass |
| Main renderer | 118 actual Helm templates per full study run |
| Constructed states | 27 (8 contract-positive, 19 controls) |
| Verified old→upgrade→repaired contracts | 8/8 |
| Exploratory detector | 8/8 positive hits, 0/19 control flags |
| Legacy-key-absent heuristic | 8/8 hits, 3/19 false flags |
| Explicit actionable migration notes | 7/8 positive cases |
| Seeded review-budget decisions | 2,268 CSV records; seeds 17,29,43 |
| Original Prometheus parser | 4/4 generated configs accepted by official v3.8.1 promtool |
| Local Prometheus process probe | exact generated configs fail off-cluster; transparent job-inventory-only adaptation succeeds, 11 vs 1 |
| cert-manager hard-error negative control | v1.16.0 explicit webhook.config=null reproduced nil-pointer template error |
| Default-provenance twin experiment | 3/3 identical old manifests but divergent new output when old default explicitly pinned |

## Package contents

```text
N02_experiments/
  README.md
  EXPERIMENT_REPORT_CN.md
  PAPER_RESULTS_EN.md
  cases.yaml                          fixed 27 constructed scenario inputs
  requirements.txt                    pinned Python analysis dependencies
  charts/                             10 upstream-version chart tarballs
  scripts/
    bootstrap_tools.sh                optional official Helm / Prometheus downloads
    run_study.py                      chart rendering, risk scoring, contracts
    provenance_twins.py               implicit vs explicit old-default differences
    lint_charts.py                    real helm lint + cert-manager error control
    validate_prometheus.py            actual promtool application parser
    validate_prometheus_runtime.py    exact off-cluster failure & adapted process probe
    analyze_study.py                  paired ranking, ablations, bootstrap, charts
    verify_results.py                 fully offline record/hash/invariant assertions
  results/
    case_results.jsonl                every case, input, rendering outcome, contract
    default_drift.json                default render resource/field changes
    toolchain_and_sources.json        Helm binary and all chart archive SHA-256
    rankings_seeded.csv               2,268 seeded budget decisions
    analysis_summary.json             aggregate results, paired bootstrap intervals
    lint_and_known_failure.json       per-chart Helm lint + non-silent control
    promtool_parser_audit.json        4 actual Prometheus parser checks
    prometheus_configs/               raw configs and adapted local process configs
    prometheus_runtime_probe.json     exact startup failures and adapted live API results
    provenance_twins.json             3 old-default source-provenance pairs
  figures/
    figure1_budgeted_selection.png
    figure2_effect_loss.png
```

The ZIP includes all original chart archives used by the analysis and all evidence records. It excludes ~150+ MB of downloaded tool binaries and any temporary source clones.

## 1. Verify frozen experiment results (offline)

Python 3.10+:

```bash
python3 scripts/verify_results.py
```

Expected:

```text
PASS: 5 chart families / 10 immutable chart archives; 27 real-Helm cases (8 migration contracts + 19 controls)
PASS: 8/8 manifest contracts lost and repaired; 8/8 detected, 0/19 controls flagged in curated cohort
PASS: 2,268 seeded rankings; 10/10 lint; 4/4 promtool parser; 2/2 adapted localhost Prometheus probes
PASS: 3 source-provenance twin divergences; all recorded artifact hashes match
```

## 2. Re-run all experiments

Commands assume Linux x86-64 and the current directory is `N02_experiments/`.
The original shell commands install only into this package's `toolchain/`:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt

# Fetch official Helm v3.17.0 and Prometheus v3.8.1 (~150 MB combined).
bash scripts/bootstrap_tools.sh --with-prometheus

# All 118 main-chart template renders: real Helm, constructed release inputs.
.venv/bin/python scripts/run_study.py

# Public chart defaults and source-provenance twin interventions.
.venv/bin/python scripts/provenance_twins.py

# Ten upstream chart lint runs + official cert-manager hard-error reproduction.
.venv/bin/python scripts/lint_charts.py

# Actual Prometheus application parser; four original generated configs.
.venv/bin/python scripts/validate_prometheus.py

# Exact original off-cluster startup attempts and clearly adapted live process probes.
.venv/bin/python scripts/validate_prometheus_runtime.py

# Seeded 7-method × 4-budget × 3-seed ranking comparisons; plots and statistics.
.venv/bin/python scripts/analyze_study.py

# Cross-file, outcome and SHA-256 checks.
.venv/bin/python scripts/verify_results.py
```

Re-running the experiment **overwrites generated results in `results/`**. The reproducibility scripts use no GPU, do not connect to a Kubernetes cluster, do not touch your normal Helm repository configuration, and create only private temporary Prometheus data paths. The live probe binds exclusively to `127.0.0.1` and terminates each process.

### Pinning third-party artifacts

All ten charts are present under `charts/` and verified using `results/toolchain_and_sources.json`. They originate from:

- `https://argoproj.github.io/argo-helm` (Argo CD 5.55.0 / 6.0.0)
- `https://grafana.github.io/helm-charts` (Tempo Distributed 1.32.0 / 1.33.0)
- `https://prometheus-community.github.io/helm-charts` (Prometheus 27.0.0 / 28.0.0, kube-state-metrics 3.0.0)
- official Git tag `kube-state-metrics-2.13.2` of `https://github.com/prometheus-community/helm-charts` (SHA `1f980d9da0262bb661f9c64b8b3c0dfb443324e2`, repackaged with Helm)
- `https://charts.jetstack.io` (cert-manager v1.15.3 / v1.16.0)

The official Helm binary comes from `https://get.helm.sh/helm-v3.17.0-linux-amd64.tar.gz`. Prometheus v3.8.1 binaries come from its GitHub release. The repository itself supplies the chart source licensing; consult their respective upstream license files before redistributing or adapting charts. The experimental Python and Markdown files are independently authored for this research package.

## Interpretation safeguards

1. **Constructed release is not a customer's release:** there is no actual Helm storage Secret or observed operator action history.
2. **Successful Helm render is not a successful deployment:** only the manifest-level contract is checked in four chart families.
3. **Promtool parse is not live scraping:** original Kubernetes-dependent Prometheus configs cannot boot in this off-cluster workspace; the independent process probe validates only an explicitly adapted job inventory.
4. **The manifest-diff ranking is not direct helm-diff upgrade:** the true plugin requires an existing release and was not benchmarked against the same historic Kubernetes state.
5. **Documentation is an exceptionally strong baseline:** seven of eight selected migration cases are explicitly called out upstream, and the method did not meet the original ≥15 percentage-point improvement gate at the maximum budget.
6. **No holdout/generalization claim:** case selection and scoring evolved together; three tie-breaking seeds do not multiply independent observations.

The most useful next experiment is a pinned, disposable Kubernetes cluster with two genuine old-release installations, coupled with real operator configuration history and direct helm-diff + migration-guide time measurement. See the Chinese audit for the exact stop criteria and the missing-paper-experiment checklist.
