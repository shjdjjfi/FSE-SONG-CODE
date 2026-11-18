# Executed GitHub-hosted Attest cache evaluation

**Remote execution: COMPLETE, 3 independently provisioned runs, 2026-11-18.**

Dedicated authorized public research repository: https://github.com/shjdjjfi/FSE-EXP-1

Branch: n21-fse-benchmark. The production default branch was not given the
experiment workflow. Three valid runs, each with 15 successful GitHub-hosted
Ubuntu 22.04 jobs and 14 validated strategy/fault outputs:

- https://github.com/shjdjjfi/FSE-EXP-1/actions/runs/44237916114
- https://github.com/shjdjjfi/FSE-EXP-1/actions/runs/44238758566
- https://github.com/shjdjjfi/FSE-EXP-1/actions/runs/44238773494

**Total: 45 real jobs / 42 per-strategy result records, all individually
checked against an independently cold-compiled path-and-SHA-256 oracle.**
Of the 42 controlled cases, 30 have correct output; the 12 intentionally
incorrect cases reveal baseline failure modes, not failing CI jobs.

Full per-run logs, runner job/step timestamps, REST provenance, raw ZIP
artifacts and JSON payloads are archived under
results/github_actions_run_<RUN_ID>/. A separate auditor
github_actions/analyze_gha.py rejects missing cells, inconsistent fault
conditions, missing cache hits/misses, missing raw logs, and incorrect
input-drift classification; its generated rollup is
results/github_actions_aggregate.md, .json and .csv.

## Executed design

1. "warm" independently builds two TypeScript 5.9.3 project-reference units,
   produces four output files, uploads independent source/output SHA truth,
   saves a complete output + buildinfo cache with the real Attest save action,
   deliberately removes one JS output and saves a *partial* cache.
2. "verify" launches 14 true GitHub-hosted jobs. Each executes
   Attest/typescript-cache-action@7227052c996c38afb0aece6e05d185b2d45a28a5
   on a fresh runner, with complete, deliberately incomplete or missing
   cache keys; some inject declaration corruption or stale extra output.
3. Five strategies/controls (no additional repair, guarded SHA repair,
   clean-all, force-all as applicable) are each verified against SHA truth.
   Records include wall/child CPU seconds, hash bytes scanned and rebuild
   projects. Nested action logs include millisecond cache restore duration,
   actual cache hit/miss keys and compressed bytes transferred.
4. Three commits differ only in harmless replication-marker comments and
   metadata documents, NOT in fixture source or benchmark logic. The
   auditor confirms an identical fixture-source SHA across all valid runs.

The first real pilot run 44237397496 is retained separately in
results/github_actions_run_44237397496/EXCLUDED_PILOT.md and excluded from
cost comparisons: its prototype fingerprint accidentally treated generated
declarations as source changes. Corrected run 44237916114 and both following
replicates do not have this defect.

## Strict limitations

- **All observed damage was explicitly injected by experimenters. No natural
  incident or continuous industrial N21 failure-rate denominator exists.**
- Two-project/four-file compressed caches are 3.85–3.91 KB, not industrial
  workloads; the zero-to-few-second timings and toy break-even threshold do
  not measure deployment benefit, maintenance effort, or economic ROI.
- Different matrix strategies ran on different ephemeral hosted runners:
  within-run comparisons are not same-machine deterministic microbenchmarks.
- The real action demonstrates that its own restore process can truthfully
  report a cache hit while the **stored** snapshot was deliberately partial;
  this does not mean Attest caused the incompleteness.
- The two default-happy-path controls work correctly. We do not claim
  Attest is generally incorrect or that every cache is incomplete.
- The action and upstream sub-actions can evolve; the tested top-level action
  is pinned to its exact commit. GitHub artifact retention is limited, so the
  raw logs and ZIPs are preserved in this replication package.

## Reproduction

The remote repository contains
.github/workflows/n21-attest-benchmark.yml and
n21_submission_experiments/github_actions/gha_n21.py.
Local workflow and script copies are equivalent to the tested versions except
for documentation/replication-marker comments. A push to the isolated
n21-fse-benchmark branch touching either path triggers a fresh 15-job matrix.
That consumes GitHub-hosted Actions compute minutes and creates short-lived
cache/artifact entries; do not run without authorization for the target repo.

To re-audit archived observations without rerunning CI:
python3 github_actions/analyze_gha.py
python3 validate_results.py
