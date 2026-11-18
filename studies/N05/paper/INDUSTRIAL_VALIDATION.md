# N05 — independent source-release and real-world CI evidence audit

## Executive verdict

- **Original v1 generalization superiority established:** **NO** against three seeded random orders under the pre-registered +15 pp / project-cluster-CI rule. The exact project-bootstrap 95% lower endpoint is 0.0, so the criterion is not satisfied if that lower bound equals zero.
- **Secondary generic source-path v2 criterion established:** **NO**. This is a separate refinement developed after inspecting the older 8-project validation set, not the original algorithm.
- **Real upstream CI adoption/intervention demonstrated:** **NO**. We retrieved successful upstream CI run metadata and published workflow definitions (not job logs), but have no upstream installation of N05, A/B comparison, or measured developer-hours benefit.
- **Independently confirmed actionable issues detected by this original extractor:** **0 of 2 historical iced fixes**. Their affected APIs were absent from its Rustdoc literal-code-fence coverage in the pre- and post-fix published releases.
- **Confirmed errors among all feature-profile discrepancies:** **UNDETERMINED**; those with visible feature prerequisites cannot be called missing-documentation defects.

## Exact replays and independent validation

- Development: 24 crate releases, 141 screened snippets, 25 profile mismatches; guided success 100.0%, random 64.0%.
- First held-out set: 8 releases, 60 screened, 7 profile mismatches; guided 85.7%, random 85.7%.
- Second frozen cohort: 30 releases across 30 repository labels, 193/193 screened; 24 profile mismatches, 24 fully searched.

| Second holdout slice | Positive cases | Independent repos | v1 success@8 | Random success@8 | Δ success | 95% repo-cluster CI | v1 checks | Random checks |
|---|---:|---:|---:|---:|---:|---|---:|---:|
| All new crate names | 24 | 9 | 100.0% | 75.0% | 25.0% | [0.0%, 42.9%] | 1.58 | 4.43 |
| Strictly new source repositories | 24 | 9 | 100.0% | 75.0% | 25.0% | [0.0%, 42.9%] | 1.58 | 4.43 |

**Exact bootstrap verification:** The nominal 10,000-draw project bootstrap is unstable at a boundary: only 3 of 9 source repositories have a positive v1-minus-random difference. When resampling 9 projects with replacement, the exact probability that *all* sampled clusters have zero gain is 2.6012%, larger than the 2.5% lower-tail level. The exact multinomial-enumerated percentile CI therefore **starts at zero**. An earlier 10,000-replicate estimate from a different random seed had a slightly positive lower endpoint; claiming a significant gain from that unstable Monte Carlo outcome would be misleading. The overall method success and mean effort estimates are unchanged.

### Post-hoc consumer-relevance sensitivity

In the exact `sea-query 0.32.5` source, `src/lib.rs` declares `#[doc(hidden)]` and `#[cfg(feature = "tests-cfg")]` on `pub mod tests_cfg`. Six of the 24 supposedly consumer-mismatched examples directly import this hidden test fixture. The formal full-set statistic is retained, but those six should **not** be counted as developer-actionable user API repairs.

| Sensitivity | Examples | Source repos | Guided | Random | Δ success | Exact repo-cluster CI | Compiler-hint baseline |
|---|---:|---:|---:|---:|---:|---|---:|
| All pre-registered cases | 24 | 9 | 100.0% | 75.0% | 25.0% | [0.0%, 42.9%] | 75.0% |
| Exclude published hidden tests_cfg fixtures (post-hoc) | 18 | 8 | 100.0% | 87.0% | 13.0% | [0.0%, 27.0%] | 100.0% |

The sensitivity subset was identified after inspecting the outcomes, not preregistered. Its purpose is to bound industrial relevance, **not** rescue a significant p-value. The native compiler baseline ties v1 at 100% on these 18 plausible consumer examples.

For those 18 cases, the native compiler-hint baseline uses 2.44 additional Cargo checks per example, while v1 uses 1.78. The paired difference (compiler minus v1) is 0.67 checks, exact repository-cluster 95% CI [0.04, 1.80]. This exploratory effort metric may be useful for a developer tool, but is **not** an observed upstream CI runtime, maintainer effort, or business return; it excludes indexing/preprocessing overhead.

### Pre-registered secondary source-path algorithm

Among strictly independent sources, source-path v2 success@8 = 100.0%, difference from random = 25.0%, repository-cluster 95% CI = [0.0%, 42.9%]. Path-aware 24/24 positive records are complete.

### Mandatory compiler-diagnostic strong baseline

Rustc itself emits feature-gate hints in the default-profile error messages. Among the strictly independent positive cases with completed matches (24/24), the diagnostic-first baseline success@8 = 75.0%, versus original v1 = 100.0%. Direct actionable rustc feature hints were present in 58.3% of the positive cases. It shares every default-check diagnostic with v1 and uses at most eight *additional* Cargo checks; this is a stronger state-of-practice challenge than uniform random search.

The docs.rs feature-profile one-shot baseline passes all pre-screened mismatches by construction; its implementation cost is one compiler check but its flag set can be broad. Average declared docs profile contains 14.21 named feature flags across this strict positive subset; v1 successful repairs request 1.5833 flags on average. A flag-count comparison is not a measured change in CI cost or semantic minimality; full dependency feature closure matters.

## Five genuine public upstream CI snapshots

Each row is a successful GitHub Actions workflow run on an upstream project at the recorded commit, with archived workflow source and SHA-256. These runs were NOT performed by N05. Their commit SHAs are not pinned to the 2025 crates.io packages used for example replay, so the table does not prove that a particular replayed failure passed this historical CI run. A missing literal consumer replay in one workflow is not proof no related check exists in reused actions or other workflows.

| Repository | Upstream successful run | Cargo-hack command found in workflow | Doctest/all-target command found | N05 deployed? |
|---|---|---|---|---|
| tokio-rs/tokio | [#43617715543](https://github.com/tokio-rs/tokio/actions/runs/43617715543) (`42fad55e4b`) | Yes | Yes | No |
| tokio-rs/axum | [#43654865679](https://github.com/tokio-rs/axum/actions/runs/43654865679) (`2449f1600c`) | Yes | Yes | No |
| tower-rs/tower | [#36401034616](https://github.com/tower-rs/tower/actions/runs/36401034616) (`d48d77e6f1`) | Yes | Yes | No |
| tower-rs/tower-http | [#43598734092](https://github.com/tower-rs/tower-http/actions/runs/43598734092) (`8569ec8b99`) | No literal command | No literal command | No |
| iced-rs/iced | [#43519026114](https://github.com/iced-rs/iced/actions/runs/43519026114) (`60b9f34344`) | No literal command | Yes | No |

This is stronger, publicly deployed state-of-practice context than a simulated random feature order; any industrial improvement claim requires a head-to-head run against these native gates and actual upstream decisions.

## Independent upstream maintenance evidence and blind spots

- [iced #2188](https://github.com/iced-rs/iced/pull/2188), closed 2024-02-05T23:51:43Z: **Add doc to direct developers to enable features for iced::time::every** — independently reported/accepted upstream documentation repair, not credited to this method.
- [iced #2184](https://github.com/iced-rs/iced/pull/2184), closed 2024-01-05T18:16:06Z: **Fix docs to include missing feature tags** — independently reported/accepted upstream documentation repair, not credited to this method.
- Coverage for Missing feature guidance for iced::time::every: 0 eligible literal target code fences before the fixes, 0 after. These are **not detection successes**; upstream's affected API was outside the current extractor.
- Coverage for Missing feature badges for lazy widget helpers: 0 eligible literal target code fences before the fixes, 0 after. These are **not detection successes**; upstream's affected API was outside the current extractor.

## Actual version-specific documentation disclosure

For four hand-selected first-holdout issue cases, independently fetch and hash the *actual rendered* version-specific rustdoc page:

| Published version and API | Required feature visibly disclosed? | Source |
|---|---|---|
| tower-http 0.6.6 — feature cors only | Yes | [Version-specific rendered documentation](https://docs.rs/tower-http/0.6.6/tower_http/cors/struct.CorsLayer.html) |
| tower-http 0.6.6 — feature fs only | Yes | [Version-specific rendered documentation](https://docs.rs/tower-http/0.6.6/tower_http/services/struct.ServeDir.html) |
| tower 0.5.2 — feature util only | Yes | [Version-specific rendered documentation](https://docs.rs/tower/0.5.2/tower/trait.ServiceExt.html) |
| dashmap 6.1.0 — Requires the raw-api feature | Yes | [Version-specific rendered documentation](https://docs.rs/dashmap/6.1.0/dashmap/struct.DashSet.html) |

This is intentionally not a population-estimated false-positive rate. The four examples were targeted because they occurred in the old validation set; the checked pages already disclose a prerequisite and do not substantiate omissions.

## Cargo feature-footprint caveat

The independent static closure audit covers 55 prior successful minimized fixes. 5 contain a smaller transitive internal-feature-set candidate, requiring independent recompilation before it can be called an alternative repair. The tower `balance` one-flag fix enables seven non-default internal features while a narrower `util` direct flag is a structural candidate. Actual independent Cargo checks now **confirm both patches compile**: the v1-suggested `balance` enables 7 internal Cargo features, whereas `util` enables 2 on the same tower 0.5.2 consumer snippet. Therefore the one-flag certificate was correct only for requested-flag count, and was **not** optimal in feature closure or least-privilege configuration.

## What is and is not demonstrated

Observed: official published archives; direct compiler statuses and complete Cargo stdout/stderr; independent successful GitHub Actions runs and pinned workflow YAML; independent historical maintainer fixes; rendered documentation badges on four chosen examples.

Not observed: N05 adopted into those upstream repos; actual maintained pull requests caused by N05; reduction in false CI quarantines or build failures; measured engineer-hours saved; a blinded human review of all alleged doc defects; a causal ROI estimate.

## Prospective two-repository deployment design needed to close ROI evidence gap

1. Obtain agreement from two independent maintainers/projects and archive the exact release tags, workflow YAML, runner environment, timestamps and permissions. Do not alter third-party repositories unilaterally.
2. Freeze a blinded sample of newly modified feature-gated examples. Run native rustdoc/default doctests and cargo-hack feature powerset as active baselines, then N05 on the exact same release snapshot.
3. Ask maintainers to decide *actionable omission vs already disclosed prerequisite* without revealing which tool raised an alert. Time the review and archive accepted/rejected documentation PRs with commit SHAs.
4. Compare unique confirmed defects, false-positive proportion, fresh-runner CPU minutes, queue delay, repair latency, and developer effort. Report project-cluster CI and both positive and null cases.
5. For industrial production ROI, include actual downstream user issue/CI failures associated with a published example and the observed changes after a correction; local hypothetical savings must remain explicitly modelled.

## FSE 2027 Industry Track fit

The [official FSE 2027 Industry Track call](https://conf.researchr.org/track/fse-2027/fse-2027-industry-papers) welcomes industrially relevant research even without an industrial partner, but calls for a clear industrial context and outcomes. The current research package supports a documented external-consumer compatibility observation. Do not submit a long-paper claim of measured industrial gains or general superiority if the above preregistered criteria fail.

## Reproducibility and evidence boundaries

- `prospective/PREREGISTRATION.md`, `prospective/data/frozen_sample.json`, pinned source archives & SHA-256, `prospective/results/checks/`, `check_logs/`, `search.jsonl`, `pathaware.jsonl`, `independent_validation.json`.
- `industrial/public_records/` raw upstream API and workflow payloads with retrieval stamps and hashes; `industrial/historical/` pre/post published releases and zero-coverage results; `industrial/rendered/` version-specific HTML docs; `feature_footprint.json`.
- `industrial/consumer_gate.py` and `github_actions_gate.yml` are reproducible integration templates only. They were not deployed to the upstream runs enumerated here.
