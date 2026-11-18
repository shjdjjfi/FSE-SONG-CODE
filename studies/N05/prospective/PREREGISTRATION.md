# N05 second independent-project evaluation — frozen before screening

Frozen by the research workflow on 2026-11-15 (Asia/Shanghai); the cohort and
analysis rules below were fixed **before** consumer-compilation outcomes for
these package releases were inspected.

## Cohort

The complete version-pinned list is the `FROZEN` constant in
`prospective/run_prospective.py`. No listed package may be dropped based on its
subsequent compilations or observed effects. Packages whose published archives
cannot be downloaded, cannot be parsed, or contain no eligible Rustdoc fences
remain in the denominator of attempted packages and are explicitly listed as
non-evaluable. The cohort excludes all 32 development and prior holdout crates.

## Fixed method and statistics

- Run unchanged `scripts/collect.py`, `scripts/select.py`, and
  `scripts/replay.py`: three seeds (17, 29, 43); at most two documentation-risk
  and one other snippet per crate per seed; maximum eight additional compiler
  checks; no optimization of the ranking on this cohort.
- Main outcomes among positively screened default-fail/docs-pass *unique*
  snippets: guided and random-seed-averaged success@8, average added compiler
  checks, and number of enabled flags. Project-cluster bootstrap at 10,000
  replicates, not example-level confidence intervals.
- Primary independent project unit is the source repository; crates from the
  same repository shall be pooled when computing confidence intervals. Any
  absent/malformed repository URL is separately marked (and package clustered
  conservatively), never silently treated as a verified independent author.
- Secondary: strict negative controls (both profiles pass), invalid samples,
  feature-repair minimality and one-shot docs-feature-profile baseline.
- Search ability is not evidence of a *documentation defect*. An actual defect
  requires independent review of source feature annotations and publicly
  rendered docs, or a maintainer-confirmed issue/patch. An added CI gate is not
  a deployed CI benefit; local CPU replays are counterfactual costs.

## Decision rule

For a strong superiority claim we require: at least five independently
represented repositories with positively screened cases; guided success@8
at least +15 percentage points above random; and an independent-repository
cluster 95% CI excluding zero. Otherwise superiority is **not established**.

The pre-existing 24-crate development set and 8-crate holdout must remain
separate from this independent cohort. No result from this cohort may be used to
retune the original method. Anything run after unblinding is labelled
exploratory.

**Post-analysis numerical verification:** The originally prescribed 10,000-draw
repository bootstrap was close enough to the 2.5th percentile boundary that
two random seeds yielded different conclusions (lower bounds zero versus
slightly positive). The final `prospective/validate.py` additionally enumerates
all multinomial count vectors for nine repositories to obtain the *exact*
project-bootstrap percentile endpoints. The exact lower endpoint is zero:
the model superiority criterion must be reported as **not met**, irrespective
of a favorable Monte Carlo seed. The exact bootstrap changes no cases,
rankings, metrics or project grouping; it only removes simulation error.

## Frozen, explicitly secondary v2 method

Before running *any search* for this prospective cohort, a second prespecified
algorithm was added, motivated by **only** a previously reported failure on
the 8-crate historical holdout: a code example in the `services/fs` source
directory did not contain the literal `fs` Cargo feature token. The generic
v2 algorithm in `scripts/pathaware.py` adds a constant source-directory
lexical-match bonus to the original frozen ranking. It does not use compiler
outcomes to learn or choose bonuses, and cannot claim an untouched validation
on the old 8-crate holdout. Evaluation on the present 30-release cohort is
prespecified now, but with a transparent note that a small initial portion of
the *screen labels* had been printed before this v2 addendum; no search
outcomes had been observed. Because this is a design change, the original v1
remains primary; v2 is a strictly secondary, independently tested refinement.

For v2, compare the same three random seeds on the same set of candidate
features, using the same eight-check budget, project-cluster intervals and
pre-registered +15pp decision criterion. All path feature matches score +30,
otherwise retain the original order. No further tuning on these results.

## Explicitly exploratory budget curve added after partial search visibility

Because the original 8-check endpoint can saturate when a package has fewer
than eight named features, `scripts/budget_curve.py` will also report every
budget k=1,...,8 (not cherry-pick a single favorable k), plus mean success over
these eight points. This analysis was added after some initial search outcomes
in this second cohort were visible, and is **exploratory**, not a replacement
for the frozen success@8 primary outcome or its decision rule.

## Required strong baseline: native Rust compiler's own feature hints

An earlier (8-crate) holdout E0432 error explicitly says that `ServeDir` is
gated behind `fs`. Thus a competitive baseline must extract existing rustc
`#[cfg(feature = "...")]` and "gated behind" diagnostics from the **same
default-profile compile already paid by every method**, then try indicated
feature flags under the identical eight-additional-check budget. This is
implemented in `scripts/diagnostic_baseline.py` and applied to all cohorts.
If rustc does not suggest a needed feature, the baseline falls back to a
plain alphabetical order over public feature flags; it never calls the
proposed lexical feature ranker.
The baseline was added after some outcomes were observed, and is classified
as a *state-of-practice challenge*, not a preregistered new method. Its
performance is a major test of whether the proposed research adds any value
beyond out-of-the-box Rust compiler guidance.

## Explicitly post-hoc consumer-relevance sensitivity (not primary)

After the full v1 search was inspected, all six positive cases in `sea-query`
were found to import `sea_query::tests_cfg::*`. In that exact release, the
`tests_cfg` module is gated by `tests-cfg` and annotated `#[doc(hidden)]` in
`src/lib.rs`; its symbols are fixtures for doctests, not ordinary consumer
APIs. `prospective/consumer_sensitivity.py` reports a clearly labeled
post-hoc subset excluding this specific, objective hidden-fixture dependency.
The pre-registered full 24-case comparison must remain unchanged, but the
industrial-actionability interpretation must not claim these six are normal
consumer repairs. Any drop in effect after exclusion must be reported.
