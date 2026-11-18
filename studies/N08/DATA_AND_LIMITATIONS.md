# Dataset, provenance, and inferential boundaries

**Selection**: Eight verified Bitwarden cross-team code transfers (2024–2025) and one Grafana partial ownership transfer with actual renamed files (2025), not a representative sample of all migrations. The source short list was selected from public CODEOWNERS-change commit history and publicly documented migration PRs. Six additional controls are drawn from both repositories.

**Time leakage rule**: Old path PRs must merge before the handoff. Test PRs must open after the handoff. Only PRs merged before the test PR's opening contribute to candidate reviewer scores, and the evaluated PR's author is excluded. A PR's actual review labels are revealed only after the prediction is formed.

**What counts as a case**: A verified merge, a source-prefix-to-target-prefix Git rename, and a historical CODEOWNERS team removed from at least one migrated path. Some migrations, such as Grafana #104424, remove only one of two teams. The recorded `old_owner` and `new_owner` fields are exact historical CODEOWNERS **team handles**, not resolved team members.

**Reviewer outcomes**: Distinct public GitHub handles submitting an APPROVED or CHANGES_REQUESTED review before PR merge. Public review requests are separately measured. Human-comment-only reviewers are not ground-truth positives. Review requests and review outcomes are *endogenous to current assignments* and not a gold standard for expertise.

**Substantive-code screens**: The primary sample includes path-touching PRs. A mechanical code-touching screen requires actual source-code hunks under the destination subtree. A more selective `focused_code_touched` screen requires >=10% of changed PR files under the target and <=100 files in the whole PR. This latter threshold was added **after initial outcome exploration**; it is exploratory and cannot be used as confirmatory evidence.

**Statistical estimand**: For every event with at least one labeled post-handoff PR, mean reviewer Recall@K across PRs, then mean across events. CIs resample *migration events*, with three reproducible bootstrap seeds (17,29,43), not independent experiments. Exact paired sign-flip tests are descriptive with 9 correlated events from only 2 companies; no familywise multiplicity correction or causal interpretation.

**Public source snapshots**: PR URLs, historical merged/base commit hashes, before/after CODEOWNERS and patch SHA-256, extracted timeline SHA-256, and API commit response SHA-256 are included. Raw PR HTML and patches are not republished. Anonymous GitHub REST rate limits may prevent full source re-fetching; no failure is silently counted as a negative example.

**Important limitations**:

1. No independently labeled expert set, and no independent adjudicator has verified semantic requirement for any target PR.
2. Historic team membership and individual permission/availability at the PR's opening are not publicly recoverable for every event. `current_path` is a path-history reviewer baseline, not literal GitHub CODEOWNERS assignment.
3. The historical and workload baselines use only the sampled PR pool, not every company review and task. Time-decay and load-balancing models added after the original minimal pilot are exploratory comparators.
4. Automatic CODEOWNERS prefix matching handles the selected literal directory rules and their precedence, not every GitHub CODEOWNERS wildcard. The historical owner pairs have been independently checked for these selected paths; a formal system-wide CODEOWNERS audit would require GitHub-compatible matching and authorization checks.
5. Many PRs are cross-cutting; the primary sample includes changes with few moved-module lines. A mechanical post-hoc subset reduces, but does not remove, this confounding.
6. No live review recommendation was actually deployed. Review delay, quality, correctness, incident reduction, and costs are descriptive or unmeasured—not causal treatment effects.
7. Case selection is non-random and observational, with eight migrations from Bitwarden and only one from Grafana. Project-level generalization cannot be supported.

**Ethics**: Evidence concerns public professional GitHub behavior; the user-facing report does not rank or criticize individual engineers. The paper should anonymize individual handles in aggregate charts, document permitted source use, and avoid performance claims about people.
