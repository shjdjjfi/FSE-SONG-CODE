# Sensitivity analyses (all observational)

All values below are event-macro Recall@K against observed human review participants; *not* independently verified experts.

## Recommendation budget

| Code-edit filter | K | Reviewed PRs | Events | Current path | Git-follow | 180-day handoff | Δ vs current (pp) | Δ vs git-follow (pp) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| all path-touching | 1 | 114 | 9 | 0.197 | 0.119 | 0.161 | -3.6 | +4.2 |
| all path-touching | 2 | 114 | 9 | 0.301 | 0.250 | 0.333 | +3.2 | +8.3 |
| all path-touching | 3 | 114 | 9 | 0.329 | 0.302 | 0.356 | +2.7 | +5.4 |
| all path-touching | 5 | 114 | 9 | 0.437 | 0.371 | 0.424 | -1.3 | +5.3 |
| code-touching | 1 | 102 | 9 | 0.199 | 0.129 | 0.178 | -2.1 | +4.8 |
| code-touching | 2 | 102 | 9 | 0.315 | 0.287 | 0.372 | +5.6 | +8.4 |
| code-touching | 3 | 102 | 9 | 0.348 | 0.336 | 0.396 | +4.8 | +6.0 |
| code-touching | 5 | 102 | 9 | 0.475 | 0.403 | 0.467 | -0.8 | +6.4 |
| focused code (post-hoc) | 1 | 58 | 7 | 0.245 | 0.173 | 0.282 | +3.6 | +10.9 |
| focused code (post-hoc) | 2 | 58 | 7 | 0.372 | 0.360 | 0.442 | +6.9 | +8.2 |
| focused code (post-hoc) | 3 | 58 | 7 | 0.407 | 0.406 | 0.462 | +5.6 | +5.6 |
| focused code (post-hoc) | 5 | 58 | 7 | 0.571 | 0.512 | 0.575 | +0.4 | +6.3 |

## Handoff-duration ablation (exploratory)

| Grace window | Handoff Recall@2 | Δ vs current (pp) | Δ vs permanent lineage (pp) |
|---|---:|---:|---:|
| 0 days | 0.301 | +0.0 | +5.1 |
| 30 days | 0.327 | +2.5 | +7.7 |
| 90 days | 0.318 | +1.7 | +6.9 |
| 180 days | 0.333 | +3.2 | +8.3 |
| 365 days | 0.292 | -0.9 | +4.3 |

## Time since migration and repository

| Stratum | Reviewed PRs | Events | Current path Recall@2 | Handoff Recall@2 | Δ (pp) |
|---|---:|---:|---:|---:|---:|
| early_le_90_days | 46 | 8 | 0.154 | 0.165 | +1.0 |
| late_gt_90_days | 68 | 8 | 0.383 | 0.399 | +1.6 |
| bitwarden/clients | 96 | 8 | 0.288 | 0.318 | +2.9 |
| grafana/grafana | 18 | 1 | 0.403 | 0.458 | +5.6 |

## Descriptive latency

First *observed* decision review: median 2.75 days (n=111). No treatment was deployed; no causal latency effect is estimated.

The code-touching filter is mechanical, not a semantic gold label. The 'focused code' filter was added after seeing the initial results (>=10% of changed files within the migrated subtree and <=100 files per PR), so it is exploratory and must not be treated as pre-registered confirmation. The grace-window sweep also explores test outcomes after the initial 180-day specification; do not select the highest-scoring window on this same test cohort. The same events can contribute to both time strata; project-level inference is not valid with so few independent projects.
