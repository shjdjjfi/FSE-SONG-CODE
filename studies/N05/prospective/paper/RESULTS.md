# N05 — Measured experimental results (automatically generated)

**All result counts below are from actual Cargo compilations. They must not be interpreted as population prevalence.**

- Source: 30 pinned crates.io releases; 1,983 syntactically extracted Rustdoc fences.
- Pre-registered assignments: 261 over three seeds, 193 distinct snippets.
- Screened: 193/193 distinct snippets; remaining 0.
- Labels: {'eligible_mismatch': 24, 'default_compiles': 89, 'invalid_doc_sample': 80}.
- Feature mismatch in consumer-compile-admissible set: 24/105 (stratified sample; no population estimator).
- Strict negative controls passing both profiles: 81. Default-works/docs-fails samples excluded from that denominator: 8.
- Crates with one or more independently observed gap witnesses: 9.
- Search outcomes: 24/24 eligible witnesses completed; fixed budget of eight additional Cargo checks per method.
- Independent post-discovery subset minimizations: 24 performed, 24 verified.
- One-flag feature additions with trivial global minimum cardinality: 19. Other fixes have **no** global minimum claim.
- Search effort: guided 1.5833 vs random 4.4306 additional compiles per positive.
- Lexical-only post-hoc ablation: 0 cases, success@8=None.
- Visible-copy ablations: 33 performed, 13 failed without Rustdoc-hidden preparation.
- Guided success@8 = 1.0; lexical explicit-hint baseline = 0.3333; random order (3 seeds) = 0.75.
- Guided minus random project-cluster bootstrap 95% interval = (0.0, 0.4301).
- Random minus guided Cargo checks project-cluster bootstrap 95% interval = (1.0, 4.2258).

## Per-project breakdown

| Crate | Compiled samples | Gap witnesses | Default works | Invalid document sample |
|---|---:|---:|---:|---:|
| async-compression 0.4.23 | 2 | 2 | 0 | 0 |
| bincode 2.0.1 | 5 | 0 | 5 | 0 |
| chrono-tz 0.10.3 | 7 | 0 | 0 | 7 |
| clap_complete 4.5.55 | 6 | 0 | 1 | 5 |
| config 0.15.11 | 5 | 0 | 3 | 2 |
| crossterm 0.28.1 | 5 | 0 | 5 | 0 |
| deadpool 0.12.2 | 5 | 0 | 1 | 4 |
| figment 0.10.19 | 9 | 2 | 1 | 6 |
| http-body-util 0.1.3 | 2 | 0 | 0 | 2 |
| hyper-util 0.1.15 | 6 | 2 | 3 | 1 |
| mio 1.0.4 | 5 | 2 | 3 | 0 |
| notify 8.0.0 | 3 | 0 | 3 | 0 |
| opentelemetry 0.29.1 | 7 | 0 | 5 | 2 |
| poem 3.1.12 | 9 | 4 | 1 | 4 |
| quick-xml 0.37.5 | 8 | 0 | 2 | 6 |
| rand_distr 0.5.1 | 8 | 0 | 0 | 8 |
| ratatui 0.29.0 | 9 | 2 | 6 | 1 |
| redis 0.32.1 | 9 | 0 | 3 | 6 |
| rust_decimal 1.37.2 | 7 | 0 | 0 | 7 |
| schemars 0.8.22 | 8 | 0 | 6 | 2 |
| sea-query 0.32.5 | 9 | 6 | 3 | 0 |
| semver 1.0.26 | 5 | 0 | 5 | 0 |
| serde_with 3.12.0 | 8 | 0 | 8 | 0 |
| slog 2.7.0 | 9 | 0 | 7 | 2 |
| sqlparser 0.56.0 | 5 | 3 | 2 | 0 |
| time 0.3.41 | 8 | 1 | 1 | 6 |
| tonic 0.13.1 | 8 | 0 | 4 | 4 |
| ulid 1.2.1 | 7 | 0 | 5 | 2 |
| utoipa 5.3.1 | 7 | 0 | 6 | 1 |
| validator 0.20.0 | 2 | 0 | 0 | 2 |

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
