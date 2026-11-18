# FSE 2027 Industry — N05 Experimental Protocol

Working title: **Replaying Published Rust Examples Under Consumer Feature Profiles**

## Scope and outcome distinctions

This is a study of feature-profile portability of real documentation code.
The primary observation is a **feature-profile mismatch**, not necessarily a
fault or a missing annotation. Five non-equivalent claims must be kept apart:

1. The fixed `.crate` manifest publishes different docs.rs versus consumer
   default feature profiles (configuration evidence only).
2. The identical Rustdoc example code actually fails in a stand-alone Cargo
   consumer with defaults, while passing with the docs.rs **feature profile**
   (compiler-confirmed feature-profile mismatch).
3. Removing/adding a subset of features reproduces the same outcome, so the
   failure can be given an actionable consumer fix (independent fix witness).
4. The item page has **no adequate feature disclosure** (requires review of
   the version-specific rendered docs.rs page; source comments alone cannot
   establish this).
5. A tool in an industrial publication pipeline prevents a real downstream
   failure (requires field deployment, CI integration or an independently
   observed producer/consumer report; laboratory replay alone cannot prove).

Only claims for which the stored evidence exists should appear as findings.

## Experimental units

- Release/project: 24 pinned crates.io packages, selected for diverse feature
  metadata and real Rustdoc code; no guarantee of random representativeness.
- Example: literal Rust Markdown fence from published source comments or
  README. Exclude `ignore`, `compile_fail`, `should_panic`, non-Rust, huge,
  incomplete ellipsis and explicit placeholders. Include `no_run` **for
  compilation only**. Literal `///` / `//!` docs are parsed; macro-generated
  strings are outside this corpus's recall.
- Observation: a Cargo consumer project with exactly one top-level target
  dependency, same pinned version, same Rust 1.91.0 and Linux target; all
  checks generate a hash-linked snippet and dependency manifest.
- Repetition: seeds 17, 29, 43 choose different cases within each project's
  risk/control stratum; overlapping examples are checked once and replay
  evidence is shared, avoiding fake pseudo-replication.

## Independent labels and stratification

Default consumer configuration is one `cargo check` with the crate's default
feature set. Docs configuration is another `cargo check` with exactly the
additional features declared in the crate's docs.rs metadata (including
all-features where used). Both use the Rustdoc-hidden preparation lines so
this evaluates only the specified dependency profile difference.

Per example:

- **Feature mismatch:** default compile FAIL + docs feature compile PASS.
- **Negative control:** default PASS (regardless of docs profile; never call
  this a feature failure).
- **Invalid independent snippet:** docs feature compile FAIL and not rescued by
  project-defined docs-specific cfg; do not classify its default failure as
  caused by features.
- **Docs cfg dependent:** docs feature compile FAIL, but compiled with
  project-specific non-`docsrs` rustdoc cfg switches; exclude from a
  feature-only result.
- **Infrastructure:** network, timeout, compiler MSRV or build-script failure;
  do not silently classify as any product behavior.

If a crate's docs metadata includes unstable or nightly-only custom flags,
the inability to reproduce its docs.rs environment on a stable compiler is
reported and never treated as a consumer API failure.

## RQs and baselines

**RQ1 — Is there an independent compiler witness for a documentation/profile
gap?** Report each project's numerator/denominator separately, stratify by
static risk score and distinguish invalid snippets. Source all positive cases
to a version and exact code fragment in the official archive.

**RQ2 — Can a bounded compilation search identify usable feature supplements?**
Compare under the same fixed **eight additional Cargo checks** per positive:

| Arm | Information | Proposed output | Budget |
|---|---|---|---|
| Guided | Published feature list, code tokens and documented Rust feature semantics | Ranked cumulative feature supplement | 8 |
| Text-only hints | Literal feature-name mentions in the example | Ranked cumulative feature supplement | 8 |
| Random 17/29/43 | Same eligible feature list, randomized order | Ranked cumulative feature supplement | 8 |
| All/docs configuration | Exact docs.rs declared feature set | Compile-success ceiling; large/possibly unstable set | 1 |

Measure **fix success@8** (independent Cargo pass), additional attempts, and
number of requested and expanded local features. Do not count the default/doc
label generation builds in any arm. If the guided method fails, report failure
even though the docs/all arm passed. The all/docs arm is not a minimality
baseline. Cumulative ranking is deterministic and does not learn from the
test labels.

**RQ3 — Do Rustdoc hidden lines or docs-only cfg change the conclusion?**
For up to one example per project and eligibility stratum, remove the
Rustdoc-hidden preparation lines, replay with the already admissible profile,
and record source compilation differences. Docs-only cfg rescue is counted
separately. This is *not* a sample of actual production copy-paste actions.

## Fix minimality

Once a candidate feature set successfully compiles, attempt deleting each
member using an independent Cargo build. Only label the result
**subset-minimal** if every single-feature deletion of the final set fails.
The minimization checks are **outside** the eight-check discovery budget and
must be reported separately. Cardinality/global minimality among *all*
possible feature sets is not established without a complete search of the
candidate feature lattice. Public Rust feature sets are not necessarily
monotonic, so no subset should be treated as passing merely by logical
extrapolation.

## Analysis / test plan

- Primary descriptive rates: per-project feature-mismatch counts and
  actionable search-success counts, always conditioned on independently
  admissible example compilation.
- Main paired effect: guided success@8 minus mean of three randomized order
  success@8 values for the same example. Resample **projects** with replacement
  for 10,000 percentile-bootstrap replicates (95% interval). No atomized
  snippet-level CI that ignores clustering.
- Seeds are separate sampling assignments; run summaries by seed to expose
  selection instability. Do not treat rerunning the same deterministic
  compiler as three independent trials.
- Resource cost is measured in Cargo invocations. Measured wall seconds are
  descriptive only because later conditions reuse shared compilation caches.
- Cases with no admissible positive are reportable as negative findings; do
  not drop these projects after seeing data.

## Pre-committed value and stopping checks

The original N05 proposal requested an improvement of at least 15 percentage
points in actionable failure discovery for an equal compilation budget and
false positive rate no greater than 5%. Whether the **observed** results
meet those thresholds is an empirical question. Without an independent
evaluation of page-level missing disclosures, it is unjustified to report a
tool precision or false-positive rate for *documentation bugs*. Do not claim
the threshold passed based on compiler mismatches alone.

## Threats and industrial relevance

Selection is convenience-based. Some docs.rs pages visibly indicate feature
requirements, so profile mismatch need not be a documentation defect.
Rustdoc code may have implicit dev dependencies or assume service endpoints.
We compile, not run, `no_run` examples. Source crates' docs.rs cfg settings,
platform-specific modules, Rust compiler version, and Cargo transitive
dependency updates may change behavior; exact source package digests and
post-run Cargo.lock copies mitigate but do not eliminate drift.

The plausible industrial workflow is a low-cost, CPU-only documentation
release gate: replay a bounded sample in clean dependency profiles, surface
minimal compiling feature suggestions, and show maintainers precise source
witnesses. This research package is **not** evidence of adoption or impact at
an actual software company. FSE 2027 Industry allows work with clearly
articulated industrial relevance even without an industrial partner, but
experimental thoroughness and practitioner lessons are explicit criteria.

## Official references

- FSE 2027 Industry Call: https://conf.researchr.org/track/fse-2027/fse-2027-industry-papers
- docs.rs build metadata: https://docs.rs/about/metadata
- Cargo documentation tests: https://doc.rust-lang.org/cargo/commands/cargo-test.html
- Rustdoc doctest behavior: https://doc.rust-lang.org/rustdoc/write-documentation/documentation-tests.html
- Feature documentation RFC 3485: https://rust-lang.github.io/rfcs/3485-feature-documentation.html
