# N05: Replaying Published Rust Examples Under Consumer Feature Profiles

Submission-oriented empirical replication package for the fifth idea in the
attached FSE 2027 Industry screening portfolio. Everything in `results/` is
produced by executing the scripts; missing experiments are NEVER imputed.

**Final independent validation verdict:** the second 30-release cohort contains
24 eligible feature-profile mismatches across nine new source repositories.
The original v1 strategy succeeds on 24/24 while seeded random orders succeed
on 75% on average; the *exact* project-level bootstrap 95% CI of the success
difference is **[0, 42.86] percentage points**. The previously specified
superiority criterion is **not** met. A post-hoc consumer-relevance sensitivity
excluding six hidden test-fixture imports gives 18 cases: v1 and the native
compiler-diagnostic baseline **both succeed on all 18**. No real-world CI
deployment or causal industrial ROI has been established. See the audited
English [industrial report](paper/INDUSTRIAL_VALIDATION.md) and the
[Chinese verdict](paper/INDUSTRIAL_VALIDATION_CN.md).

## Research question

Can a Rust code example included in a **published** crate's documentation
compile when built with its docs.rs feature configuration, yet fail in an
ordinary consumer Cargo project that depends on the same pinned release with
defaults? Can a bounded CPU-only search suggest a smaller set of extra
features than the docs.rs build configuration?

This problem is distinct from running a crate's own doctests. Cargo packages
may be built under multiple mutually inconsistent feature profiles, and a
rustdoc snippet may require context or a dev-only dependency that a consumer
does not have. We conservatively *exclude* an example if it fails with the
docs.rs feature profile, and separate docs-only compiler flags from features.

## Source and frozen experiment

`data/crates_manifest.json` records 24 **pinned** crates.io releases with
their official `.crate` URL, SHA-256, feature maps and docs.rs metadata.
`data/crates/*.crate` preserves the downloaded official source archives, not
modified forks. `data/corpus.jsonl` contains every syntactically recognized
literal Rustdoc fence referring to its own crate, plus exact code and source
position. This **candidate** corpus is not a set of 2,212 verified examples.

`data/frozen_sample.json` was generated before any consumer replay result: three
seeds (17, 29, 43), at most two feature-sensitive code candidates and one
control per crate/seed. Overlap across seeds shares one actual compilation.
No random selection may be silently changed after seeing compile outcomes.

The sampled releases are a **convenience sample**; the high-risk stratum is
deliberately oversampled. No extrapolation to crates.io population prevalence
is justified.

## Run (CPU only)

Tools: Python 3.10+, official Rust/Cargo **1.91.0**, a C/C++ compiler and
CMake (needed by some optional crate dependencies); no GPU, API token, hosted
model, or Kubernetes cluster. Internet connectivity is required to obtain
transitive Cargo dependencies not present in the local registry cache.
The runner is deliberately single-process (`CARGO_BUILD_JOBS=4`, common
target cache) to make outcomes independently auditable.

From this directory (assuming `cargo` 1.91.0 is in `PATH`):

```bash
python3 -m unittest discover -s tests -v
python3 scripts/collect.py
python3 scripts/select.py
python3 scripts/replay.py --stage screen
python3 scripts/replay.py --stage search
python3 scripts/minimize.py
python3 scripts/ablations.py
python3 scripts/audit.py
python3 scripts/analyze.py
```

The **previously unseen eight-crate transfer set** is intentionally evaluated
after the main method is frozen. Run it in this order (from the same package
directory); the wrapper writes separate evidence to `holdout/`:

```bash
python3 holdout/run_holdout.py collect
python3 holdout/run_holdout.py select
python3 holdout/run_holdout.py screen
python3 holdout/run_holdout.py search
python3 holdout/run_holdout.py minimize
python3 holdout/run_holdout.py ablate
python3 holdout/run_holdout.py audit
python3 holdout/run_holdout.py analyze
```

The supplied run was executed with isolated paths `../tools/cargo-home` and
`../tools/rustup-home`. On other systems the runner detects `cargo` on PATH
and the conventional Rust home, or accepts `N05_RUST_BIN_DIR`,
`N05_CARGO_HOME`, and `N05_RUSTUP_HOME` environment overrides. The downloaded
source archives and frozen `data/locks/*.lock` files are provided; on a fresh
replay set `N05_LOCKED=1` to require locked dependency versions after the
lockfile has been installed. `cargo +1.91.0` is deliberate.

### Second independent-repository replication and real-world records

The additional **30-version** cohort is frozen, with zero overlap in crate
names with the first 32 releases. `prospective/PREREGISTRATION.md` specifies
the outcome metrics, thresholds, source repositories and an explicitly
secondary source-path ranking (the original v1 ranking is unchanged). All 193
distinct selected examples were compiled under both consumer feature profiles.
Reproduce these stages sequentially:

```bash
python3 prospective/run_prospective.py collect
python3 prospective/run_prospective.py select
python3 prospective/run_prospective.py screen
python3 prospective/run_prospective.py search
python3 prospective/run_prospective.py minimize
python3 prospective/run_prospective.py ablate
python3 prospective/run_prospective.py audit
python3 prospective/run_prospective.py analyze
python3 scripts/pathaware_evaluate.py --cohort prospective
python3 scripts/diagnostic_baseline.py --cohort prospective
python3 scripts/freeze_locks.py
python3 prospective/validate.py
python3 prospective/consumer_sensitivity.py
python3 scripts/budget_curve.py
python3 industrial/feature_footprint.py
python3 industrial/verify_dominated_fix.py
python3 scripts/plot_independent.py
python3 scripts/build_industrial_report.py
```

`prospective/results/independent_validation.json` is computed separately from
the historic held-out set and additionally excludes packages sharing source
repositories with an earlier release. `paper/INDUSTRIAL_VALIDATION.md`
combines actual Cargo outputs with public *observational* GitHub Actions
runs, upstream historical issue records, and rendered version-specific doc
badges. Source retrieval and re-audit scripts are in
`scripts/industrial_evidence.py`, `industrial/historical_issues.py`, and
`industrial/rendered_feature_audit.py`.

`industrial/consumer_gate.py` and `industrial/github_actions_gate.yml` are
optional runnable CI integration prototypes. They have not been installed
in the upstream projects; output is advisory because a feature mismatch can
be explicitly disclosed on an API page.

The `industrial/local_ci_runs/tower-http-0.6.6/` directory contains a
two-example *local smoke test* of the gate, not an upstream CI execution.
Project-specific frozen locks are saved for every one of the 30 new releases.
Where an older holdout's initial dependency lockfile could not be recovered,
the original Cargo outputs are preserved but bit-for-bit recompilation of
its transitive dependency resolution is not guaranteed.

**Replaying a package doesn't execute network code:** `cargo check` only
compiles it. Third-party crates can still execute package build scripts.
Run in a disposable/isolated environment if your trust requirements demand it.

## Methods and evidence

- `screen`: external consumer crates are generated with only the pinned target
  dependency; `cargo check` under default features and docs.rs **feature**
  profile. `docs_cfg` fallback is separately labeled and is NOT a feature-only
  mismatch. Any missing imports, deliberately ignored/compile-fail blocks,
  external dev-only dependencies, or compiler infrastructure errors are not
  counted as feature-only successes.
- `search`: a deterministic source-and-snippet token ranking plus documented
  Rust feature contracts (guided), a lexical feature-hint baseline, and three
  random feature orders. Each has an equal ceiling of 8 **additional** Cargo
  checks per eligible example. Random baselines have recorded seeds.
- `minimize`: further independent compile attempts remove redundant features.
  Reports **subset-minimal**, never unproven *globally cardinality-minimal*.
  Those calls are outside the equal-budget search evaluation and counted.
- `ablations`: separate Rustdoc-hidden preparation code from the code a reader
  would copy from the rendered example. At most one per project and stratum.
- `audit`: links every screen-positive example to the fixed published release
  and surrounding original source; flags possible inline feature disclosures,
  but **does not** pretend these are reviewer-confirmed annotations.
- `analyze`: table of independent project counts, screen labels, success@8,
  paired method results and project-cluster bootstrap 95% confidence interval.

Full Cargo JSON logs are in `results/check_logs/*.txt.gz`, and each recorded
run has its exact manifest and source SHA-256, elapsed time, status, errors and
toolchain identifier in `results/checks/*.json`. Runtime is observational:
cache and compilation order preclude a strictly fair wall-time comparison.
The reproducible cost metric is independent Cargo compilations per method.

## Interpretation limits (do not remove for submission)

1. A compiler-pass under docs.rs features is NOT proof that docs.rs itself ran
   the snippet's doctest or showed it on a particular rendered page.
2. A feature-dependent example may already have a clearly documented feature
   annotation. A source-level feature mismatch **is not automatically a
   documentation bug**; manual page-level adjudication is needed for actionable
   missing-disclosure claims.
3. The sample is intentionally stratified and not randomly representative of
   the Rust ecosystem. Several examples cannot compile as standalone programs
   even under full documentation features. These are excluded, not labeled as
   feature-caused consumer failures.
4. The observed evidence demonstrates a mechanism and a proposed CPU-only
   assessment procedure, **not** industrial deployment savings, adoption, or
   acceptance by FSE 2027.
5. Official crates.io source packages preserve library source; transitive
   dependency lockfiles need to be checked and preserved to guard against
   later upstream dependency changes.

## Credits and legal

This package consists of original experiment scripts and official third-party
crates.io tarballs whose authors retain copyright. Check each published crate's
license prior to redistributing externally. Academic citations should include
the original crate authors and the following primary specifications:

- https://docs.rs/about/metadata
- https://doc.rust-lang.org/cargo/commands/cargo-test.html
- https://doc.rust-lang.org/rustdoc/write-documentation/documentation-tests.html
- https://rust-lang.github.io/rfcs/3485-feature-documentation.html
