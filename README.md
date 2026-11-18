# FSE-SONG-CODE

Code and experimental evidence for nine software engineering studies prepared for the FSE 2027 Industry Track.

本仓库汇集 12 个原始实验包。各研究目录提供代码、复现说明、冻结结果与局限性。原始包来源和 SHA-256 见 [档案清单](docs/PROVENANCE.md)。

## Study index

| Study | Research question | Reproduction and evidence |
| --- | --- | --- |
| I01 | Are advertised Python security fixes installable on target environments? | [CPU extension](studies/I01/i01_industry/README.md) · [120-project baseline](studies/I01/i01_full/README.md) |
| N02 | What configuration intent is lost across Helm chart upgrades? | [Phases 1–3](studies/N02/README.md) · [Initial protocol and results](studies/N02/README_PHASE1.md) |
| N04 | How can flaky-test history be recovered across test renames and splits? | [Base study](studies/N04/base/README.md) · [Expanded study](studies/N04/expanded/REPRODUCE_EXTENSION.md) |
| N05 | Do published Rust examples work under consumer feature profiles? | [Experiment](studies/N05/README.md) · [中文说明](studies/N05/README_CN.md) |
| N06 | Can alert timing be preserved across metric identity changes? | [Simulation](studies/N06/README.md) · [Field-readiness evidence](studies/N06/results_field/README.md) |
| N08 | What can public traces establish about expertise after CODEOWNERS transfers? | [Study](studies/N08/README.md) · [Identifiability analysis](studies/N08/measurement/README.md) |
| N21 | Can incomplete TypeScript build outputs be detected and recovered? | [Experiment](studies/N21/README.md) · [Hosted-run evidence](studies/N21/github_actions/README.md) |
| N22 | Can converging database migration paths produce different data outcomes? | [Initial experiment](studies/N22/base/N22/README.md) · [Django and OpenCode follow-up](studies/N22/addendum-20261118/README.md) |
| N24 | How much collateral lockfile churn occurs during npm platform repair? | [Source and evidence guide](studies/N24/START_HERE.md) · [Corrected report](studies/N24/source/N24_FSE2027_EXPERIMENT_REPORT.md) |

Start from each study's linked guide and run commands from the directory that
guide specifies. The [publication notes](docs/PUBLICATION_NOTES.md) list the
offline checks, external inputs, and known limits. The archived GitHub Actions
workflows live under the relevant study directories for reference.

## License

This repository applies the [MIT License](LICENSE) to the original research
code. Third-party materials retain their upstream terms. Source attributions,
upstream licenses where supplied, and study-specific data provenance are
documented alongside each study.
