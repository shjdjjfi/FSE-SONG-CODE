# N04 — Recovering Flaky Test History Across Test Identity Changes

**Research experiment/reproducibility bundle, extended 2026-11-15. Real linked quarantine decision and cross-project independent refactoring target oracle added; still not a completed FSE Industry Track validation.**

This project addresses the **fourth numbered idea, N04**, in the seven-idea screening ZIP. It is about whether CI test-history/quarantine identifiers should survive test renames, source moves, JUnit parameterization, or ambiguous splits.

The bundle contains the actual evaluated scripts, machine-readable measurements, manually inspected source cases, source-and-runtime mappings, statistics, and figures. It **does not fabricate any CI decision or experimental result**. Read **[ADDENDUM_20261115_ZH.md](ADDENDUM_20261115_ZH.md)** for the new three-gap investigation and [REPORT_ZH.md](REPORT_ZH.md) for the prior experiment. The addendum supersedes prior statements that no real identity-linked quarantine example or independent target labels exist.

## Read the measured results without external downloads

From the directory containing this README:

```bash
python3 -m pip install -r requirements.txt
python3 -m unittest discover -s tests -v
python3 src/verify_results.py
python3 src/verify_addendum.py
python3 src/make_figures.py --results results --output figures
```

The `results/` directory contains frozen measured JSON outputs, not invented examples. All **six** figures are supplied in PNG and PDF, including the independent holdout comparison and real quarantine transfer. `src/verify_results.py` and `src/verify_addendum.py` validate the principal numerical claims and fail loudly if data are absent or contradictory. The optional `src/record_provenance.py` can check source Git HEADs if the original Git clones are present.

## Experiment matrix

| ID | Experiment | Source | Status |
|---|---|---|---|
| E1 | Reproduce stale pytest `lastfailed`-ID selection | Real pytest 8.4.2, 3 controlled variants | **Completed (controlled)** |
| E2 | Ingest repeated test results | FTW Zenodo 2024, 330 CSV.xz, 11 tracks | **Completed** |
| E3 | Align result histories with Git ancestry | Public Git source revisions, all available FTW repositories | **Completed (see aligned JSON)** |
| E4 | Source-diff independently auditable lineage cases | java-cas-client, delight-nashorn-sandbox | **6 cases, small observational pilot** |
| E5 | IDoFT label-conditioned baseline/ablation comparison | 7 public Java projects, 74 cases, 15 events | **Completed, but oracle target partly inferred** |
| E6 | Three-seed migration-cluster bootstrap and exact CIs | IDoFT sample | **Completed; does not certify 2% target** |
| E7 | Actual Java revision execution & parameter identity | Java-WebSocket, 2 classes, pre/post commit, 3 repeats | **Completed: 240 outcomes, 27 candidate links** |
| E8 | Audit independent real Actions failures | Test Flare snapshots; Prefect and Home Assistant | **Completed: labels insufficient for quarantine** |
| E9 | Offline counterfactual policy on real repeated outcomes | Six source-labeled boundaries | **Completed; zero observed flaky antecedents** |
| E10 | Real source-controlled quarantine decisions and migration | Fusion, trycua, real Actions metadata | **264 add events; one verified file-split-linked quarantine event; no causal cost saving** |
| E11 | Third-party independently verified source successors | RefactoringMiner, 22-project corpus; source evaluation 4 independent projects | **54 TP code-refactoring edges; guarded 40/54 vs name 39/54; not CI truth** |
| E12 | Four original `Deleted` conflict re-audit | Riptide maintainer commit and Git rename detection | **All four found with Git R94–R98; raw 4/9 preserved** |
| E13 | Actual before/follow-up workflow job elapsed time | Two GitHub Actions run IDs, seven jobs each | **522 vs 529 seconds; both failed; no causal conclusion** |

## Rebuild experiments from public inputs

**Download datasets and clone the pinned public repositories yourself.** The roughly 510 MB FTW archive and Git checkout histories are intentionally excluded from this portable ZIP. Dataset provenance and commit pins are in `SOURCE_PROVENANCE.md` and `results/provenance.json`. The scripts assume an external directory with this layout:

```text
inputs/
  flaky_histories_dataset/  # extract the Zenodo archive here
  idoft/                    # TestingResearchIllinois/idoft Git clone
  flaky-test-dataset/       # test-flare/flaky-test-dataset Git clone
  java-cas-client/
  delight-nashorn-sandbox/
  java-websocket/
  openhtmltopdf/
  riptide/
  json-io/
  spring-cloud-kubernetes/
  graphhopper/
  activiti/
  tyrus/
  yawp/
  fluent-logger-java/
  helios/
  nexus-repository-helm/
  guava/
  alibaba-druid/
  c2mon/
  maven-doxia/
```

Commands below are run from this bundle's root, with external clones at `../inputs/` (adapt the paths for your machine):

```bash
python3 src/ingest_histories.py --help
python3 src/align_git.py --help
python3 src/build_idoft.py --help
python3 src/evaluate_idoft.py --help
python3 src/evaluate_source_gold.py --help
python3 src/replay_maven.py --help
python3 src/replay_pytest.py --help
python3 src/replay_history_policy.py --help
python3 src/audit_real_ci.py --help
```

The full per-experiment commands are in `REPRODUCE_COMMANDS.md`. **Do not overwrite the frozen `results/` until you have preserved them**, especially if you are using a different Java runtime, Git checkout, or dependency version. Results depend on several historical snapshots: `SHA Detected` and `migration^` are different source revisions and are tracked separately in JSON.

The complete new study can be reproduced separately using [REPRODUCE_ADDENDUM.md](REPRODUCE_ADDENDUM.md); it requires additional source clones of Fusion, trycua/cua, RefactoringMiner, Cassandra, Checkstyle, Closure Compiler and Infinispan. The 510 MB archive and other original input repositories are still omitted from this ZIP.

## Key validity constraints

- `MovedOrRenamed` is an IDoFT **status**; the dataset does not supply a complete independent successor-FQN oracle. The exploratory target-FQN score must not be sold as independently validated recovery accuracy.
- Four raw `Deleted` labels conflict with source-level same-body/path-move evidence; both the **raw 4/9** and the **filtered 0/5** results are reported. The latter is not a corrected ground truth.
- The actual JUnit refactor yields 27 *candidate* instance links, not 27 independent maintainer-confirmed transfers, and contains **no measured flaky failure**.
- Offline repeated executions are not production CI logs. `test-flare` captures failing CI candidates only, not full passing histories or quarantine actions.
- A **real Fusion file-level quarantine transfer** is verified across a one-test split, with the same original failed Actions run cited by the old and new ledger entries. This is not an N04 Java method-level production deployment. Workflow runtimes are observed, but causal CI cost savings and retry savings are **not**.
- The new independent RefactoringMiner oracle confirms method-refactoring identities on four previously unseen projects. Its `FP` labels **cannot be used as false-quarantine-transfer labels**, and a third-party validated *method refactoring* need not certify equivalent runtime fixtures or flakiness semantics.
- The originally proposed criterion **false inheritance ≤2%, recovery gain ≥15 percentage points at matched risk** is not demonstrated; the **submission-ready industry claim must be stopped** under the idea's own stop-loss rule.

## Files

- `REPORT_ZH.md` — bilingual-source Chinese research report, exact statistics, claim limitations, go/no-go decision.
- `ADDENDUM_20261115_ZH.md` — newest three-gap investigation, linked real quarantine/CI evidence and independent holdout results.
- `REPRODUCE_ADDENDUM.md` — source pins, new commands and experiment meaning.
- `PAPER_EXPERIMENTS_EN.md` — academically cautious English experiments/limitations section draft.
- `SOURCE_PROVENANCE.md` — public research source URLs, repository pins and licensing notes.
- `evidence/source_events_gold.json` — manual provenance of 6 source-diff identity cases.
- `results/*.json` — input summaries, predictions, individual local test executions, audit results.
- `results/provenance_v1.json` preserves the previous bundle's integrity manifest; the updated `results/provenance.json` covers this extended package.
- `src/` — source parsers, comparators, CPU-only runners, verification and figures.
- `figures/` — six vector PDF figures plus corresponding PNGs.

No GPU is used. Actual historical rerun of Java tests requires a JDK and Maven plus Internet on first dependency resolution; the Python-only experiments need a CPU. No source or production data was modified remotely.
