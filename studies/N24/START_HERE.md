# N24 / FSE 2027 Industry — complete reproducibility bundle

**Study:** Measuring Collateral Version Churn When Repairing npm Platform Lockfiles (third of four candidate ideas).

**Frozen source:** `shjdjjfi/FSE-EXP-1`, branch `n24-fse-benchmark`, commit `5024f7708184a9c341165b7bf3ecd659b990788c`.

**Actual hosted run:** https://github.com/shjdjjfi/FSE-EXP-1/actions/runs/44245392156 (four successful jobs: Linux, macOS, Windows, aggregation).

## Where to start

1. Read `source/N24_FSE2027_EXPERIMENT_REPORT.md` for the methodology, real results, caveats, and paper framing.
2. Read `source/n24_submission_experiments/README.md` for commands, npm and Node pinning, and exact rerun instructions.
3. Run the 11 deterministic guardrail/regression tests from `source/`:
   `python3 -m unittest discover -s n24_submission_experiments/tests -v`.
4. Inspect the source implementation, preregistered conditions and hosted workflow under `source/n24_submission_experiments/` and `source/.github/workflows/`.
5. Use `source/N24_RECOMPUTED_CONTROLLED_AGGREGATES.json` and `source/N24_CORRECTED_HISTORICAL_AGGREGATES.json` for paper tables; the same two files are copied to `evidence/corrected_analysis/` for convenient independent inspection.
6. Verify the eight **original, unmodified** hosted artifacts against the digests and artifact IDs in `source/N24_HOSTED_ARTIFACT_MANIFEST.md`; they are in `evidence/runner_artifacts/`.

## Contents

| Path | Contents |
|---|---|
| `source/` | Exact GitHub source-branch snapshot: workflow, complete experiment code, tests, research report, corrected JSON summaries |
| `evidence/runner_artifacts/` | Eight original downloaded ZIPs: per-host controlled and historical data plus original GitHub aggregate outputs |
| `evidence/historical_audit/` | Frozen public repository audit, source SHAs and three original committed project snapshots |
| `evidence/local_reproductions/` | Local Linux pilot/reproduction JSON, clean/defective lockfile evidence and per-family results |
| `evidence/original_input/` | Original supplied set of four ideas and report for provenance |
| `evidence/corrected_analysis/` | Manuscript-ready report, correct summary JSONs and hosted artifact digest manifest |

## What the experiments do—and do not—establish

- **Controlled:** 5 native-package families × 3 actual runner platforms × 2 lock conditions × 5 methods = 150 recorded observations.
- **Actual project replays:** 3 frozen public GitHub projects × 3 actual runner platforms × 5 methods = 45 project–host–method records, containing 75 native parent checks.
- **Public audit:** 17 fixed repository snapshots containing 39 target parent instances; five instances in three repositories exhibited 59 entirely absent variant paths.
- **Crucial strong baseline:** npm 12.2.3 matches the targeted strategy on the controlled experiment and outperforms it in some inconsistent real project locks. The data do **not** establish a generally novel superior repair algorithm or a measured production financial benefit.
- The original hosted `aggregate_history.zip` contains a **known analysis error** (duplicate counting version churn for multiple native parents in one project). The corrected summary is in `source/N24_CORRECTED_HISTORICAL_AGGREGATES.json`, and its fix is regression-tested in `source/n24_submission_experiments/tests/test_analyze_history.py`; raw per-host observations are unchanged.

No installation caches, `node_modules`, or full temporary `npm ci` trees are bundled. Those are generated on demand by the reproducibility scripts rather than being scientific source evidence.
