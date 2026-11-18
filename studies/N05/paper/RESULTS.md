# N05 — Measured experimental results (automatically generated)

**All result counts below are from actual Cargo compilations. They must not be interpreted as population prevalence.**

- Source: 24 pinned crates.io releases; 2,212 syntactically extracted Rustdoc fences.
- Pre-registered assignments: 195 over three seeds, 141 distinct snippets.
- Screened: 141/141 distinct snippets; remaining 0.
- Labels: {'eligible_mismatch': 25, 'default_compiles': 79, 'invalid_doc_sample': 30, 'cfg_dependent': 7}.
- Feature mismatch in consumer-compile-admissible set: 25/86 (stratified sample; no population estimator).
- Strict negative controls passing both profiles: 61. Default-works/docs-fails samples excluded from that denominator: 18.
- Crates with one or more independently observed gap witnesses: 8.
- Search outcomes: 25/25 eligible witnesses completed; fixed budget of eight additional Cargo checks per method.
- Independent post-discovery subset minimizations: 25 performed, 25 verified.
- One-flag feature additions with trivial global minimum cardinality: 18. Other fixes have **no** global minimum claim.
- Search effort: guided 1.68 vs random 5.2667 additional compiles per positive.
- Lexical-only post-hoc ablation: 25 cases, success@8=0.92.
- Visible-copy ablations: 23 performed, 6 failed without Rustdoc-hidden preparation.
- Guided success@8 = 1.0; lexical explicit-hint baseline = 0.52; random order (3 seeds) = 0.64.
- Guided minus random project-cluster bootstrap 95% interval = (0.2, 0.5067).
- Random minus guided Cargo checks project-cluster bootstrap 95% interval = (2.2879, 4.6667).

## Per-project breakdown

| Crate | Compiled samples | Gap witnesses | Default works | Invalid document sample |
|---|---:|---:|---:|---:|
| axum 0.8.4 | 5 | 2 | 2 | 1 |
| bitflags 2.9.1 | 3 | 0 | 3 | 0 |
| chrono 0.4.41 | 9 | 0 | 3 | 6 |
| clap 4.5.40 | 3 | 3 | 0 | 0 |
| flate2 1.1.2 | 6 | 0 | 6 | 0 |
| futures-util 0.3.31 | 1 | 0 | 0 | 1 |
| hyper 1.6.0 | 4 | 0 | 0 | 3 |
| indexmap 2.10.0 | 9 | 0 | 8 | 1 |
| indicatif 0.17.11 | 5 | 0 | 5 | 0 |
| itertools 0.14.0 | 9 | 0 | 9 | 0 |
| petgraph 0.8.1 | 7 | 0 | 7 | 0 |
| prost 0.13.5 | 0 | 0 | 0 | 0 |
| rand 0.9.1 | 9 | 0 | 9 | 0 |
| rayon 1.10.0 | 8 | 0 | 8 | 0 |
| regex 1.11.1 | 8 | 0 | 7 | 1 |
| reqwest 0.12.19 | 8 | 0 | 2 | 0 |
| serde 1.0.219 | 1 | 0 | 0 | 1 |
| sqlx 0.8.6 | 3 | 0 | 0 | 3 |
| strum 0.27.1 | 3 | 3 | 0 | 0 |
| tinyvec 1.9.0 | 5 | 3 | 2 | 0 |
| tokio 1.45.1 | 8 | 7 | 0 | 1 |
| tokio-util 0.7.15 | 9 | 2 | 0 | 7 |
| tracing-subscriber 0.3.19 | 9 | 1 | 3 | 5 |
| uuid 1.17.0 | 9 | 4 | 5 | 0 |

## Operational definitions and limits

- Gap witness: the **same** published-source Rustdoc code fence compiles in an external consumer Cargo package under docs.rs's declared *feature* profile but fails under default Cargo features.
- This tests the documentation's code against consumer build configurations; it does **not** establish that docs.rs ran the individual doctest or that the snippet is visible on every rendered item page.
- Rustdoc-hidden lines were compiled, as in Rustdoc itself; the visible-only copy/paste analysis is a separate future/ablation question. External test dependencies were not guessed.
- Doctest `ignore` and `compile_fail` code fences were excluded; `no_run` fences were compiled but never executed. This guards against mistaking intentional behavior for a defect.
- docs.rs-specific rustdoc `--cfg` and nightly flags are not applied to consumer Cargo. The documented **feature** profiles are tested separately; platform is fixed to x86_64-unknown-linux-gnu.
- Samples deliberately oversample code mentioning extra feature names. Reported conditional rates are not unbiased estimates of Rust ecosystem prevalence.
- `invalid_doc_sample` means the synthetic consumer did not compile even with the docs feature set (possibly an external dev dependency, context, cfg or a true doc bug); it is excluded from a feature-gap finding.
- Feature search is budgeted and heuristic. The current guided `features` lists are *not* proven cardinality-minimal; a separate minimization oracle or bounded exhaustive test is needed before claiming minimality.
- The selected 24 popular projects are a convenience sample, not an independent random sample of crates.io; results have no demonstrated industrial adoption outcome.
- Lockfile transitive dependencies and compiler/toolchain need to be preserved to reproduce exact behavior in the future.

## Evidence files

`data/crates_manifest.json` (SHA-256 per official .crate); `data/frozen_sample.json` (pre-registered selection); `results/screen.jsonl`; `results/search.jsonl`; `results/checks/*.json` and corresponding compressed Cargo logs; `results/per_project.csv`.
