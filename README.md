# FSE-SONG-CODE

**Reproducible software-engineering experiments for the FSE 2027 Industry Track research portfolio.**

This repository organizes **12 dated experiment packages for 9 distinct studies**. The original research questions, executable source, frozen observations, negative results, provenance, and explicit submission gaps are documented separately. **A public artifact is not a claim that a paper is submission-ready.**

> 中文说明：本仓库按研究编号整理现有实验，不将合成数据称作真实工业生产记录，不将 AI 模拟评审称作独立真人评审，也不把受控故障注入当作自然发生的事故。

## Study index

| ID | Topic | Entry point | Evidence boundary |
|---|---|---|---|
| **I01** | Whether advertised Python security fixes are installable on real targets (*Patchability Cliff*) | [studies/I01](studies/I01) | CPU resolution/installation checks; **not** complete production CI |
| **N02** | Configuration intent lost across Helm chart upgrades | [studies/N02](studies/N02) | Real upstream charts, constructed states, external challenge; **no** production cluster or human timing |
| **N04** | Flaky-test history across test renames and splits | [studies/N04](studies/N04) | Public histories and test replays; original deployment/industrial benefit gate remains open |
| **N05** | Published Rust examples under consumer feature profiles | [studies/N05](studies/N05) | Compiled public crate examples; superiority and prospective ROI not established |
| **N06** | Preserving alert timing across metric identity churn | [studies/N06](studies/N06) | Synthetic event traces and public rules; real clusters and native end-to-end validation missing |
| **N08** | Whether expertise coverage after CODEOWNERS transfers is identifiable | [studies/N08](studies/N08) | Public observations and sharp bounds; **no** independent expertise oracle |
| **N21** | Partial TypeScript cache recovery with the Attest action | [studies/N21](studies/N21) | 45 real GitHub-hosted jobs with **controlled** cache defects, not natural incidents |
| **N22** | Data contracts across converging database migrations | [studies/N22](studies/N22) | Two separately documented experimental phases; no general prospective ROI |
| **N24** | Collateral npm lockfile churn during platform repair | [studies/N24](studies/N24) | Controlled multiplatform jobs and historical public locks; strongest npm baseline remains competitive |

## Repository layout

```text
studies/
  I01/                       security-fix reachability and CPU validation
  N02/                       cumulative Helm phases 1–3
  N04/                       expanded experiment and historical phase snapshot
  N05/                       Rust feature-profile experiment
  N06/                       alert-identity experiment
  N08/                       CODEOWNERS identifiability study
  N21/                       TypeScript CI cache experiment
  N22/base/                  initial DB-migration experiment
  N22/addendum-20261118/     later Django/OpenCode study
  N24/                       npm platform-lockfile experiment
docs/
  PROVENANCE.md              inventory and hashes of supplied ZIP files
  PUBLICATION_NOTES.md       evidence boundaries and redistribution choices
```

Each study keeps its **original internal layout** as far as possible, so commands in its own README continue to apply when run from that study's folder. Multiple versions were never silently merged into a single new experiment: N02's newest package includes earlier phases, while N04 and N22 expose their distinct stages explicitly.

## Reproduction

1. Open the corresponding `studies/<ID>/README.md` (for N22, choose `base/` or `addendum-20261118/`).
2. Run its **offline verification** or local tests first; verification of an archived result is not the same as independently re-executing an industrial system.
3. Only run network-dependent replays, package installation, or hosted workflows after reviewing the pinned environment and expected cost. Workflows provided inside study directories are examples and **do not automatically execute** from the repository root.
4. Read the study-specific limitations and the [publication notes](docs/PUBLICATION_NOTES.md) before using any result in a manuscript.

The [provenance file](docs/PROVENANCE.md) records the exact names and SHA-256 hashes of all 12 supplied ZIP packages, including earlier versions that have been superseded in the navigable source tree. The original archives are preserved outside this index by their original filenames; publication copies may exclude sensitive logs and upstream distributables (see [publication notes](docs/PUBLICATION_NOTES.md)).

## License and third-party material

Unless an individual file says otherwise, the **original research code** in this collection is offered under the [MIT License](LICENSE). Public-source fixtures, published crate and Helm distributions, source excerpts, cached dependency metadata, and upstream work retain their own licenses; see [publication notes](docs/PUBLICATION_NOTES.md). This license does not relicense third-party material.

**Research integrity:** archived estimates are descriptive of their documented cohorts. Do not convert exploratory results, simulations, user-written fixtures, proxy labels, model-assisted annotations, or controlled faults into claims of independently confirmed industrial field performance.
