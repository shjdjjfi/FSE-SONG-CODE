# N08: Reproducible observational pilot — results and limitations

All numbers below are computed from publicly visible pull requests in the selected repositories. They are **not** randomized interventions, independently adjudicated expertise labels, or estimates of causal reduction in review delays.

## Dataset validation

| Event | Migration PR | Verified cross-team renames | Historical PRs with timelines | Follow-up PRs with timelines | With human decision reviews | Truncated commit query |
|---|---:|---:|---:|---:|---:|---|
| BW10818 | [#10818](https://github.com/bitwarden/clients/pull/10818) | 8 | 10 | 14 | 14 | no |
| BW11709 | [#11709](https://github.com/bitwarden/clients/pull/11709) | 5 | 12 | 17 | 17 | no |
| BW12407 | [#12407](https://github.com/bitwarden/clients/pull/12407) | 3 | 10 | 5 | 5 | no |
| BW12927 | [#12927](https://github.com/bitwarden/clients/pull/12927) | 2 | 5 | 6 | 6 | no |
| BW13285 | [#13285](https://github.com/bitwarden/clients/pull/13285) | 2 | 11 | 15 | 15 | no |
| BW14571 | [#14571](https://github.com/bitwarden/clients/pull/14571) | 52 | 12 | 16 | 16 | no |
| BW14987 | [#14987](https://github.com/bitwarden/clients/pull/14987) | 9 | 8 | 4 | 4 | no |
| BW15093 | [#15093](https://github.com/bitwarden/clients/pull/15093) | 10 | 11 | 19 | 19 | no |
| GF104424 | [#104424](https://github.com/grafana/grafana/pull/104424) | 21 | 10 | 19 | 18 | no |

The commit-path API may include a migration commit timestamped before its merge; that PR is explicitly removed. Events are checked against the CODEOWNERS revision on each side of the migration and their actual Git-detected rename pairs. A future PR must open after the migration and merge to be evaluated.

## Reviewer-retrieval task: fixed budget

The observed positive label is a distinct human account that submitted APPROVED or CHANGES_REQUESTED before that PR merged. Reviewers are ranked using only earlier merged PRs; the PR author is excluded. K=2 recommendations. 'Current path' has no cross-path memory; 'source only' inherits pre-move reviewers; 'git follow' permanently pools both; 'recency follow' uses a fixed 180-day reviewer half-life; 'sampled load balanced' penalizes activity observed in a sampled 30-day window; 'windowed handoff' gives source-history a linearly decreasing weight over 180 days. The pooled popularity and workload fallback are learned from this *sampled* repository history, not the whole repository.

| Reviewer strategy | Event-macro Recall@2 | Event-cluster bootstrap 95% CI | Hit@2 |
|---|---:|---:|---:|
| popularity | 0.079 | [0.025, 0.144] | 0.242 |
| current_path | 0.315 | [0.256, 0.372] | 0.563 |
| source_only | 0.203 | [0.074, 0.349] | 0.379 |
| git_follow | 0.287 | [0.168, 0.418] | 0.506 |
| recency_follow | 0.303 | [0.200, 0.414] | 0.531 |
| sampled_load_balanced | 0.240 | [0.142, 0.326] | 0.487 |
| windowed_handoff | 0.372 | [0.297, 0.462] | 0.611 |

### Paired comparisons (event-level; exploratory)

| Comparator | Recall@2 difference (pp) | Two-sided exact sign-flip p | Events better / worse |
|---|---:|---:|---:|
| current_path | +5.6 | 0.484 | 5 / 3 |
| source_only | +16.9 | 0.023 | 7 / 1 |
| git_follow | +8.4 | 0.203 | 6 / 1 |
| recency_follow | +6.8 | 0.062 | 5 / 0 |
| sampled_load_balanced | +13.2 | 0.188 | 6 / 1 |
| popularity | +29.3 | 0.004 | 9 / 0 |

## Scientific boundary

- This dataset comes from **2 public repositories**, with unbalanced event counts. The migrations within each repository are correlated; simple event bootstrap cannot fully recover cross-company generalization.
- Review participation is selected by the *existing* routing process and is not an independent 'true expert' label. The proposed thesis of missing expert coverage therefore remains **untested**.
- Teams in CODEOWNERS are not publicly resolvable to their complete historical individual membership. The company CODEOWNERS policy is verified, but no claim is made that the `current_path` strategy is literal GitHub CODEOWNERS assignment.
- Candidate sampling is path-based; Git commit histories may include broadly changed files, documentation-only changes, refactors, and later renames. Mechanically retrieved PR diffs and maintainer adjudication are needed before claiming semantically substantive PRs. For a partial team transfer, the source-reviewer pool includes members of retained and removed teams.
- Neither review requests nor independent handoff/triage decisions were extracted. Response time or industrial ROI cannot be estimated causally from this data.
- Exactly three bootstrap seeds (17, 29, 43) validate numerical reproducibility; they do not constitute three independent experimental worlds.
- Strong competitors such as full history-aware recommendation, codeowners-diff, and workload-aware ranking need additional implementation and equivalent input data before formal submission.

## Submission gate

The pre-registered improvement target was ≥10 pp expert coverage over the strongest baseline at equal budget. Observed reviewer Recall@2 is only a diagnostic proxy; **do not claim this submission gate passed**, irrespective of its numeric value. Minimum remaining evidence: independent expert labels, additional repositories, controls, complete review requests/events, semantic PR adjudication, and workload calibration.
