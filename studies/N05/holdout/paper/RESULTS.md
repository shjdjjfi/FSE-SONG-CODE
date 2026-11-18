# N05 — Measured experimental results (automatically generated)

**All result counts below are from actual Cargo compilations. They must not be interpreted as population prevalence.**

- Source: 8 pinned crates.io releases; 909 syntactically extracted Rustdoc fences.
- Pre-registered assignments: 72 over three seeds, 60 distinct snippets.
- Screened: 60/60 distinct snippets; remaining 0.
- Labels: {'default_compiles': 33, 'invalid_doc_sample': 20, 'eligible_mismatch': 7}.
- Feature mismatch in consumer-compile-admissible set: 7/32 (stratified sample; no population estimator).
- Strict negative controls passing both profiles: 25. Default-works/docs-fails samples excluded from that denominator: 8.
- Crates with one or more independently observed gap witnesses: 3.
- Search outcomes: 7/7 eligible witnesses completed; fixed budget of eight additional Cargo checks per method.
- Independent post-discovery subset minimizations: 6 performed, 6 verified.
- One-flag feature additions with trivial global minimum cardinality: 5. Other fixes have **no** global minimum claim.
- Search effort: guided 2.2857 vs random 3.9048 additional compiles per positive.
- Lexical-only post-hoc ablation: 0 cases, success@8=None.
- Visible-copy ablations: 11 performed, 3 failed without Rustdoc-hidden preparation.
- Guided success@8 = 0.8571; lexical explicit-hint baseline = 0.5714; random order (3 seeds) = 0.8571.
- Guided minus random project-cluster bootstrap 95% interval = (0.0, 0.0).
- Random minus guided Cargo checks project-cluster bootstrap 95% interval = (-0.6667, 2.25).

## Per-project breakdown

| Crate | Compiled samples | Gap witnesses | Default works | Invalid document sample |
|---|---:|---:|---:|---:|
| bytes 1.10.1 | 9 | 0 | 9 | 0 |
| dashmap 6.1.0 | 8 | 1 | 7 | 0 |
| hashbrown 0.15.4 | 8 | 0 | 8 | 0 |
| miette 7.6.0 | 7 | 0 | 2 | 5 |
| serde_json 1.0.140 | 5 | 0 | 3 | 2 |
| tokio-stream 0.1.17 | 6 | 0 | 2 | 4 |
| tower 0.5.2 | 8 | 4 | 1 | 3 |
| tower-http 0.6.6 | 9 | 2 | 1 | 6 |

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
