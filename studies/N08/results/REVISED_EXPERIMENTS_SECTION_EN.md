# N08 — Additional experiments and results (manuscript draft; observational)

**Scope statement.** This section is suitable only for a carefully qualified observational work-in-progress or negative-result submission. It is **not** evidence that the original positive-effect FSE Industry submission gate has passed.

## Data and replication protocol

We reconstruct nine merged code-path/ownership-transfer events involving two public repositories, `bitwarden/clients` (eight events) and `grafana/grafana` (one). All events have verified migrations, dated before/after CODEOWNERS configurations and 112 source-to-destination Git rename pairs. We use 114 post-migration, human-reviewed PR-event pairs. Timestamps and SHA-256 content fingerprints are stored alongside reproducible reviewer request and review-event derivatives. Each candidate reviewer recommendation excludes the target PR's author; only historical PRs merged before the target opening are used to construct ranking features.

The original outcome is normalized retrieval of individuals who later submitted an `APPROVED` or `CHANGES_REQUESTED` review—not independently verified code experts. We therefore call the outcome *observed participation recall* throughout.

## Follow-up A: code-grounded researcher screening

We attempted re-reading all 114 original PR patches and verified 93 downloaded patch hashes against the previous independent diff-audit fingerprints. The other 21 were blocked by rate-limit responses (HTTP 429). A single model-assisted researcher then reviewed available changed-line samples, component paths and PR descriptions: 46 likely substantive inherited-code changes, two presentational-only changes, and 66 unknown. The researcher had already seen earlier algorithm results; labels are not blind. No specific member's historic-team status was established by these judgments. Every positive label retains a precise PR URL, a patch SHA-256 and a code-grounded rationale. We provide the non-blinded labeling sheet to allow independent future challenge.

On the 46 exploratory, non-blinded positives, the time-window policy achieved 39.8% observed reviewer Recall@2 versus 35.0% for the current-path baseline (+4.8 percentage points; event-bootstrap 95% CI [-7.8, +21.5] pp; event-level exact sign-flip p=0.750). Selection was post hoc and 66 other labels remain unknown, so this cannot validate expert quality or an effect-size gate.

## Follow-up B: historical team-member identification

The names in historical CODEOWNERS rules refer to teams, not to verified historical people. We audited ten distinct referenced team handles against the public GitHub team endpoints and received eight 401 and two 403 responses, without any member roster. We therefore provide lists of people with verifiable *pre-transfer code-review participation* and their PR links, but never equate those contributors with official members of the old CODEOWNERS team. GitHub's team review-assignment settings may also convert a team request to selected individual review requests, making the mapping from public timeline entries to actual old-team coverage unidentifiable without organization-level records.

## Follow-up C: shadow deployment and industrial cost bounds

We replayed each policy's fixed K=2 recommendations against the saved public review-request history, including visible named requests within 72 hours of PR opening. Compared with current-path routing, the 180-day transfer strategy selected 62 different person–PR recommendation slots across 48 PRs; 17 selected candidates also naturally submitted decision reviews. These are *observations of the original workflow*, not additional reviews caused by the experimental policy. The policy was never deployed and no reduction in latency, review labor, or production defects was observed.

To make the workload tradeoff transparent, we calculate purely hypothetical break-even thresholds. Supplementing rather than replacing the original policy by 62 new invitations, each assumed to cost 15 minutes of reviewer attention, costs 15.5 reviewer-hours. With an assumed eight hours of labor saved per prevented incident, at least 1.94 such incidents would need to be avoided in the sample to break even. Both assumed values are exogenous sensitivity parameters; no incidents were observed to have been avoided. The equal-K replacement policy has no *additional recommendation slots*, but its true net benefit remains unidentified.

## Follow-up D: stronger historical hybrid and forward-time evaluation

We additionally include time-safe reviewer-request counts and Git commit-author frequency, in addition to source and destination historical reviewers. A grid of 80 candidate weight tuples is evaluated with (i) retrospective leave-one-migration-event-out training and (ii) a stricter prequential procedure that selects weights only using PR outcomes already **merged before** each target PR opened. The method uses historic commit authors only after the commit's associated PR is verifiably merged. All methods operate at the same K=2 recommendation budget.

| Outcome: observed decision-reviewer Recall@2 | Event macro |
|---|---:|
| Current-path history | 30.1% |
| Original 180-day handoff | 33.3% |
| Prequential reviewer-request/commit hybrid | 35.0% |
| Leave-one-event-out hybrid (exploratory) | 28.8% |

The prequential hybrid's improvement over current-path is +4.9 pp (event-bootstrap 95% CI [-2.1, +13.1] pp; exact sign-flip p=0.297). Improvement over the original 180-day policy is +1.7 pp (p=0.750). The leave-one-event-out result is worse than the current-path baseline; leave-one-repository-out is strongly underpowered because only two repositories are available. All feature choices were investigated on the previously explored public corpus, and none of these measurements is a pre-registered independent expert-label assessment.

## Threats, limitations, and proper conclusion

1. **Endogenous outcome:** approval and change-request accounts are selected by actual CODEOWNERS/social routing, so participant recall cannot establish missing expert coverage.
2. **Incomplete human truth:** 46 source-based judgments are from one non-blind model researcher, 66 are unknown, and no independently verified named expertise oracle exists.
3. **Unknown historic rosters:** GitHub team member APIs did not yield legally usable historic person-to-team maps; public pre-migration reviewers are not equivalent to official team members.
4. **Selection bias and dependence:** migration cases were curated; repeated Bitwarden components are correlated. Event bootstrap intervals are not industry-level confidence intervals. Filtered code-change results are post hoc.
5. **No intervention:** review time and industrial net value were not causally evaluated; workload scenarios are assumption-driven only.
6. **No positive gate:** no observed proxy result reaches +10 pp over the strongest equal-budget baseline on an independently held-out expert-label cohort. A manuscript claiming such a result would be unsupported.

Our additional public-data evidence is consistent with a *limited, uncertain* role for transfer-aware reviewer suggestion, and it demonstrates the critical identification gap between path history and independently validated review expertise. An industry-deployed, blinded, multi-organization study is required before making a productivity or safety claim. The fully specified deployment protocol is in `PROSPECTIVE_INDUSTRIAL_EVALUATION_PLAN.md`.
