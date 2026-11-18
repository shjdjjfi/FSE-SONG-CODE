# I01: preregistered full follow-up, 2026-11-14

This document was fixed **before** running the new dependency-resolution outcomes.
It supersedes no earlier pilot. The work is a cross-sectional public-PyPI,
public-OSV **wheel-only installability** experiment, not a production deploy/test
or vulnerability-exploitability experiment. No GPU, model, private code, or paid API.

## Sampling frame, independent variables, exclusions

- Input snapshot: official OSV PyPI `all.zip` downloaded 2026-11-14,
  SHA-256 `305dbca79abb7dc1bf52c8466c1be9e7c134b25ec67975c2d395f5259041d22e`.
- Include non-withdrawn OSV records that explicitly identify a PyPI package,
  an `ECOSYSTEM` affected range, and a PEP-440-parseable, final `fixed`
  release. Collapse `project + version` advisories; name normalization is PEP 503.
- For each project, select the **most recently published** qualifying OSV
  advisory (tie: lexical OSV ID). If it has several final `fixed` events, use
  the **lowest** PEP-440 version. No outcome-based replacement of projects.
- Assign project to `<=2023`, `2024-2025`, or `2026` according to the
  selected advisory's published year. Uniformly take exactly 40 projects per
  stratum by smallest SHA-256 of `i01-20261114-project-` + canonical name.
  This is a stratified sample, NOT a prevalence-weighted ecosystem estimate.
- Target Cartesian grid: CPython 3.8 / 3.10 / 3.12 / 3.14 × Linux x86-64
  (manylinux2014/glibc 2.17) / Windows AMD64 / macOS arm64 (macOS 11).
  120 projects × 12 targets = **1,440** planned target scenarios.
- Never drop cases based on whether metadata exists or an installation passes;
  missing/deleted/restricted release or metadata and network/time-out errors
  receive distinct terminal statuses and are included in a flow diagram.
  Unknown/unresolved must not be quietly counted as unpatchable.
- A short feasibility smoke test, if needed before the full runner, is excluded
  from all statistical results and recorded separately.

## Operational labels

1. `root_artifact`: A compatible non-yanked wheel exists for the precise
   OSV-stated fixed release, and the release and file `Requires-Python`
   conditions accept the target. **No source builds permitted**.
2. `dependency_resolution`: Whether *that exact pinned release*, together
   with its entire distribution dependency closure, can be resolved using
   public PyPI prebuilt wheels, target markers and target Python/platform.
   `uv pip compile` is primary closure oracle; a preregistered stratified
   20% of tasks receives secondary `pip install --dry-run --ignore-installed`
   checks. Both are actual solvers, neither installs/runs target packages.
3. `patchability_frontier`: For each project/OS, first tested Python target
   at which (2) passes, and whether a newer Python target changes failure to
   success. **No claim that the fixed version is the only security-safe
   alternative; OSV backports, source builds, local constraints and future
   alternative versions remain unexamined.**

Network/timeout/permission/parser error ≠ infeasible. Report successful,
solver-unsatisfiable, unknown, and dropped stages separately. Scenarios with
missing root metadata remain in the intention-to-measure denominator but not
the adjudicated performance denominator. Use at most 45 s per uv scenario,
up to 75 s per pip validation; concurrent workers ≤4; retries ≤2 for
connectivity failures; `--only-binary :all:` to avoid executing build scripts.

## Comparison / falsification

- B0: fixed-release `Requires-Python` only. Predicts candidate exists if
  declared Python range accepts runtime; ignores wheel tags.
- B1: wheel-tag presence only; ignores Requires-Python.
- B2: original pilot root compatibility gate: `Requires-Python` + file wheel
  tags, implemented independently with standard packaging tag parsing. This
  answers root installation feasibility only, **not full closure**.
- B3: unrestricted full `uv` resolver on every condition (reference oracle).
- Proposed planner: use B2 to prune *definitely impossible* cases and call
  full `uv` only where B2 passes. Under wheel-only assumptions B2 is a
  necessary condition, not a complete predictor. Compare planner with B3 on
  final `dependency_resolution` outcomes, changes in solver calls and
  observed wall-time. A failed B2 must never be treated as an independently
  solved full dependency conflict; diagnostic category is root artifact gate.
- Additional check: actual `pip --dry-run` on 20% of scenarios sampled by
  smallest SHA-256 of `i01-pip20-` + scenario key (uniform across projects;
  if possible, ensure each 2026/older × Python × OS cell represented). Audit
  all uv/pip discordances and wheel-gate false negative cases.
- Root case difficulty: compare B0/B1/B2 against actual pip no-deps on the
  same 20% validation set. Report improvements with CIs, not as new software
  repair tools or as independent labels if they merely duplicate tags.

## Primary metrics & statistics

- Cellwise root and full-closure success / unsatisfiable / unknown counts.
- By-project/OS patchability frontier; 3 OS × 4 Python matrices, old→new
  recovery rate, and cross-OS disagreement.
- On adjudicated scenarios: B0/B1/B2 binary root-gate accuracy, false-safe,
  false-blocked vs pip no-deps; planner full-closure agreement, false-blocked,
  solver invocation/time ratio against full uv. Compare all categories
  explicitly; no oracle claim if uv/pip disagree.
- 95% confidence intervals via 2,000 within-stratum **project-level** bootstrap
  resamples, fixed RNG seed 20261114; no treating 1,440 correlated targets
  as independent observations. Paired McNemar where valid on root labels;
  descriptive rather than hypothesis testing elsewhere.
- Time includes direct subprocess user-observable wall time per target, but
  report metadata API fetch separately and mark cache effects; solver avoided
  work is an **estimated** single-pass saving, not a measured deployment-speed
  improvement. Report sample diversity, fixed-version dates, failures,
  response hashes, package examples, and limitations.

## Precommitted decision thresholds

- Strong result only if ≥90% of scenarios yield a decisive full-solver label,
  ≥95% of the 20% pip validation are decisive, zero observed B2 false-blocked
  vs full solver (unresolved excluded with denominator shown), and planner
  reduces full solver calls ≥10%. If any fails, report the study as inconclusive
  for the corresponding claim, not an FSE-ready success.
- Novelty test is independent: 2026 *VulnBump* already documents Python-version
  incompatibility during vulnerability repair; this study must demonstrate
  additional multi-target measurements and useful budget/diagnostic tradeoffs.

## Auditing caveats

Only wheel-only metadata compatibility and dependency resolution are studied.
No consumer application installation, import/test/CI behavior, security
validation, transitive dependencies with application-imposed pins, actual
backport safety or fix applicability, or in-the-wild prevalence is proved.
The sample deliberately balances advisory-year strata. Real production claims
require separate consumer-project study; no fabrication of industrial data.
