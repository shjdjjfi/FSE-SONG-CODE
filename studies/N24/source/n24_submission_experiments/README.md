# N24 cross-platform npm lockfile experiments

The third idea in `FINAL_4_IDEAS.md` is **N24**, measuring the cost and limits of repairing missing platform-specific optional native dependencies in npm lockfiles. This directory is isolated from the pre-existing `n21-fse-benchmark` branch.

## Evidence types and limits

1. The supplied 2026-11-18 B0001 pilot (9 successes across 3 families, 3 arms, 3 seeds) is **exploratory**, not independent industrial validation. Original input and scripts are preserved in the uploaded archive, not relabeled as new data.
2. `lock_lab.py` creates *actual npm 10.9.2 warm-regeneration defects* using published registry packages, then checks npm 11.4.2, npm 12.2.3, a conservative donor repair, and clean regeneration. These are **controlled reproductions**; they are not naturally occurring CI incidents.
3. GitHub Actions workflow first captures **Linux-produced npm10 broken locks** and then imports those same locks on Windows/macOS hosts. A lock produced on its own host usually keeps its own native binary, so a cross-host transfer is indispensable to demonstrate an actual loader failure. Each successful run supplies logs and JSON artifacts. Merely committing the workflow is not execution.
4. The historical GitHub audit identifies public lockfile provenance, but Git history **alone** does not prove an incident or its business cost.

5. `historical_replay.py` restores exactly three immutable GitHub project manifests/locks *after* they were selected for observable gaps. It tries strict `npm ci` first, then records any `--legacy-peer-deps` compatibility retry separately; it never hides peer-resolution conflicts as optional-package failures. This post-hoc exercise measures today's native loader behavior, not the original build/test outcomes.

## Setup and run

Python 3.10+, Node 24+, npm registry access. Avoid postinstall script execution (`--ignore-scripts` enforced). From the repository root:

```bash
npm install --prefix n24_submission_experiments/tools/npm10 --no-save --no-package-lock --ignore-scripts --no-audit --no-fund npm@10.9.2
npm install --prefix n24_submission_experiments/tools/npm11 --no-save --no-package-lock --ignore-scripts --no-audit --no-fund npm@11.4.2
npm install --prefix n24_submission_experiments/tools/npm12 --no-save --no-package-lock --ignore-scripts --no-audit --no-fund npm@12.2.3
python -m unittest discover -s n24_submission_experiments/tests -v
python n24_submission_experiments/lock_lab.py --families rollup,esbuild,biome,swc,lightningcss --output n24_submission_experiments/results/local
python n24_submission_experiments/analyze.py n24_submission_experiments/results/local --output n24_submission_experiments/results/summary.json
python n24_submission_experiments/historical_scan.py --output n24_submission_experiments/results/audit
python n24_submission_experiments/historical_replay.py --output n24_submission_experiments/results/replay
python n24_submission_experiments/analyze_history.py n24_submission_experiments/results/replay --output n24_submission_experiments/results/replay_summary.json
```

The complete three-host workflow [run 44245392156](https://github.com/shjdjjfi/FSE-EXP-1/actions/runs/44245392156) finished with all four jobs successful. Its eight downloadable artifacts contain three controlled `runs.json` files, three historical `runs.json` files and their original aggregate summaries. The validated, corrected aggregate results are committed at repository root as `N24_RECOMPUTED_CONTROLLED_AGGREGATES.json` and `N24_CORRECTED_HISTORICAL_AGGREGATES.json`, with the methodology and interpretations in `N24_FSE2027_EXPERIMENT_REPORT.md`. For a paper, **use the corrected historical file**: the initial workflow aggregate counted Cloudreve's non-target version churn once per native parent rather than once per project–host lock. The corrected analysis and regression test are in this branch; underlying runner observations are unchanged.

Data output contains the environment, source versions, return codes, lockfile hashes, paths, node loader results, and all five strategy outcomes. `strict-donor` intentionally rejects non-leaf or ambiguous metadata. Do not generalize its correctness to arbitrary dependency graphs.

## Interpretation

Failures from actual published graph and live loader runs count. A missing entry that does not affect the host is an at-risk portability defect, **not** a demonstrated failure. Treat public incident discussions as external motivation, not independently verified outcome labels. Report strong baselines (including already existing Next.js targeted SWC patch) prominently.
