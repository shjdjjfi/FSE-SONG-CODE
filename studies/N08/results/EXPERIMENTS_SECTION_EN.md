# Experimental Evaluation — N08 (Exploratory Draft; Not Submission-Ready)

**Research question.** Does preserving former reviewers' historical knowledge for a bounded time after a cross-team code move improve reviewer retrieval beyond path-specific and full-history baselines at a fixed recommendation budget?

**Important scope statement.** This section reports a fully executed *observational reviewer-retrieval pilot*, not independently adjudicated expertise recall or a deployed industrial intervention. It is not sufficient by itself to support the proposed FSE Industry Track paper's central claim.

## RQ1. Can real handoffs and follow-up reviews be reconstructed without synthetic events?

We curated eight merged cross-team module moves in Bitwarden/clients and one merged partial ownership handoff in grafana/grafana. Inclusion required (i) the migration PR to be merged, (ii) a Git patch confirming old-to-new file rename mappings, and (iii) historically versioned CODEOWNERS rules showing that at least one responsible team for an affected source path was absent from the target path after the migration. The nine events contain **112 independently detectable rename mappings**; Grafana #104424 is a partial transfer because the Alerting Backend team retained ownership while the former App Platform co-owner did not.

For each event we extracted the prior 365 days of source-prefix commit history and the subsequent 365 days of target-prefix history using publicly accessible GitHub APIs. We selected at most 12 recent historical merged PRs for the source reviewer pool and the first 20 eligible subsequent PRs for evaluation. A candidate subsequent PR had to open after the migration was merged; only reviews attached to PRs merged before the candidate opened could inform the recommender. We filtered out bot-authored outcome PRs and excluded each PR's own author from reviewer suggestions. The final evaluation comprises **114 human-reviewed post-handoff PRs** across two repositories and nine migration events.

To characterize semantic relevance, we independently fetched each evaluated PR's patch. **102/114** PRs changed at least one source-code hunk under the destination subtree. A post-hoc focused sample of **58 PRs across seven events** additionally required the destination subtree to account for at least 10% of the files changed by the whole PR, and at most 100 changed files. This is a mechanical screen, not manually confirmed semantic continuity.

## RQ2. Does a temporary handoff improve retrieval of observed reviewers?

For every candidate PR, we treated the distinct human GitHub accounts that submitted `APPROVED` or `CHANGES_REQUESTED` before its merge as **observed review participants**. This observable target is endogenous to incumbent reviewer routing and should *not* be described as an independent expert oracle.

We evaluated seven time-safe strategies: repository-sampled reviewer popularity; destination-path history; source-path history; permanent union of source and destination history (Git-follow); a 180-day reviewer half-life across both paths; the latter penalized by a 30-day load proxy computed on the sampled PR pool; and our candidate bounded handoff, which linearly reduces source-path reviewer weight to zero over 180 days while retaining new-path history. All strategies used the same observed candidate pool and a fixed K=2 recommendation budget, with author exclusion.

| Strategy | Event-macro Recall@2 |
|---|---:|
| Sampled reviewer popularity | 0.072 |
| Destination-path history | 0.301 |
| Source-path history | 0.165 |
| Permanent Git-follow | 0.250 |
| 180-day half-life, both paths | 0.284 |
| Half-life plus sampled load penalty | 0.230 |
| **Bounded 180-day handoff** | **0.333** |

The event-macro gain over the destination-path history comparator was **+0.032 (3.2 percentage points)**, with an exploratory two-sided exact event-level sign-flip test **p=0.539**. The bounded method yielded +8.3 percentage points against permanent Git-follow (p=0.125), and +4.9 points against the time-decayed follow baseline (p=0.188). A three-seed event bootstrap (seeds 17, 29, 43) produced a 95% interval of **[0.259, 0.403]** for bounded-handoff Recall@2 with seed 17. These inferential summaries are limited by dependence among migrations within the same repository and by the small number of independent organizations; neither a causal interpretation nor a claim of superiority is justified. In particular, the candidate falls below the original target of an improvement of at least ten percentage points over the strongest equal-budget comparator.

## RQ3. Are the findings robust to budget and sample definition?

The bounded handoff improved on destination history at K=2 (+3.2 points) and K=3 (+2.7 points), but **underperformed at K=1 (−3.6 points) and K=5 (−1.3 points)**. Restricting to the 102 mechanically code-changing PRs increased the K=2 difference to +5.6 points. The post-hoc focused sample yielded +6.9 points across 58 PRs and seven events; this filter is explicitly exploratory and cannot be used as a pre-registered confirmatory result.

As an ablation, bounded windows of 0, 30, 90, 180, and 365 days yielded event-macro Recall@2 of **0.301, 0.327, 0.318, 0.333, and 0.292**, respectively. We did not select a best window on an independent validation set. No robustness analysis resolves the missing independent expert ground truth.

## RQ4. Do actual review requests support a loss-of-expertise narrative?

We recovered **369 visible review-request events** from the 114 evaluated PRs. A total of 110 PRs included a request to an anonymized code-owner team, and 113 had a named person requested. An old-path historical reviewer received a named request within the first 72 hours in 60 PRs; such a reviewer actually performed a decision review in 86 PRs. In 12 PRs, we saw neither a named request to any observed source-path reviewer nor a review by one. This is *not* evidence of 12 expert-routing failures: the source reviewer pool is only a proxy, and GitHub anonymizes some team requests.

Observed time from opening to the first decision review had a median of 2.75 days across 111 PRs with valid timestamps. No system was deployed or randomized, so reductions in response time, review quality, defects, or cost cannot be estimated.

## Reliability checks, negative controls, and threats

Six merged real-world negative controls (same-team directory moves, codeowner edits without file moves, and a test-fixture-only transfer) produced **zero erroneous source-expert routing triggers**. Public PR HTML review labels were compared with GitHub's REST reviews endpoint for one PR from each event; all **9/9** manually sampled human reviewer sets matched. Controlled unit tests additionally checked prefix precedence, real rename parsing, eligibility gating, timing leakage, bot and author exclusion, and finite grace periods.

This exploratory study is subject to several limitations: (1) real reviewers are not independent expert truth; (2) historical team membership and CODEOWNERS routing to individuals could not be fully reconstructed; (3) one organization contributes eight of nine cases; (4) sampled-history workload differs from an organization's true reviewer workload; (5) broad mechanical changes confound path-touching PR selection; (6) post-hoc filtering/window sweeps should not be treated as independent confirmations; and (7) no intervention was deployed.

**Submission gate.** Do not present this as a complete positive-effect study. A defensible next stage requires independently blinded expertise labels for each PR (two raters and adjudication), historical team-to-person mapping, robust full-history and workload-aware baselines on equivalent inputs, additional organizations, and a prospective design for industrial ROI. Blank labeling sheets and an auditable annotation protocol are provided, not fabricated adjudications.

**Primary public sources**: [Bitwarden code review process](https://contributing.bitwarden.com/contributing/pull-requests/community-pr-process/), [GitHub CODEOWNERS semantics](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners), and the exact migration pull requests recorded in `config/events.json` and `data/events/*.json`.
