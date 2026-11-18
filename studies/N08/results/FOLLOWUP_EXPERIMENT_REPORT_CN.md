# N08 — Follow-up experimental evidence and submission readiness

**Audit status: COMPLETED ALL FEASIBLE PUBLIC-DATA CHECKS; FOUR ORIGINAL ACCEPTANCE CRITERIA NOT MET.**

This report does not assert two independent human experts, employee team rosters, causal savings, or a confirmed ≥10pp gain.

## Additional experiments (previous pilot preserved)

| Evidence or experiment | Executed result | Scientific status |
|---|---:|---|
| Source PR patch snapshots | 93 / 114 | 21 hit GitHub HTTP 429; no evasion/retry |
| Single researcher semantic judgment | 46 yes / 2 no / 66 unknown | Not blind; not expert oracle |
| Historical CODEOWNERS team API audit | 10 teams; statuses {'401': 8, '403': 2} | Old-path reviewers verified only as participants |
| Public review-request replay | 114 PR; 9 events | Observed, non-causal |
| Equal-K contact switch | 62 unique PR×person introductions in 48 PR | Inferred; no real deployment |
| New-candidate naturally reviewed | 17 PR×person | Already observed, not created by method |
| Forward-time online hybrid CV | 80 candidate configurations, 114 PR | Exploratory; no external dataset |

## Main method comparisons (all are OBSERVED reviewer recall, not independent expert coverage)

| Contrast | Event-macro difference | Event bootstrap 95% CI | Exact sign-flip p |
|---|---:|---|---:|
| Original 180d handoff vs current | +3.2pp | [-1.8, +10.6]pp | 0.539 |
| Handoff on 46 one-researcher 'yes' PRs vs current | +4.8pp | [-7.8, +21.5]pp | 0.750 |
| Forward-time hybrid vs current | +4.9pp | [-2.1, +13.1]pp | 0.297 |

- Forward-time hybrid observed Recall@2: **35.0%** (current-path about 30.1%).
- Event-held-out hybrid observed Recall@2: **28.8%**. The LOEO result is worse than current-path, even before stronger independent tests.
- Original preregistered target: **≥10 percentage points over strongest equal-budget baseline, on independently judged expert truth**. Not met. Current +3.2pp, single-researcher yes subset +4.8pp, online hybrid +4.9pp. None establishes +10pp true expert coverage.

## Historical membership and coverage are not identifiable

Original CODEOWNERS team handles and timestamped code reviews are separately verified. Across 10 team endpoints, no public team roster was returned. The pre-migration individual reviewers in `historical_team_membership_audit.json` are **candidate historical subject-matter contributors**, NOT proven members of the historical team. Public PR timeline entries that say “a team” cannot reconstruct membership at the old merge date.

## Observational shadow replay versus actual industrial ROI

- 114 post-transfer PR-event pairs, K=2 fixed. Candidate switch in 48 PRs with 62 new suggested contact slots, of whom 17 naturally took formal review actions.
- Equal-budget **replacement** costs no *additional* slots, but whether it displaces the right experts is not established.
- For an alternative **supplemental** policy, 62 extra reviewer invitations × hypothetical 15 minutes of human attention = **15.5 hours**, assuming all require that work. Avoiding one 8-hour incident would be insufficient to break even; the scenario needs about **1.94 such incidents** averted across 114 PRs. No avoided incidents were observed or inferred.
- Median observed time until review by somebody on the K=2 suggestion list differs across methods, but those times are conditioned on **who actually participated**. They do not estimate intervention effects.

## Four research-to-submission gaps

1. **Independent expert oracle:** one assistant-reviewed patch-label sheet is delivered, with raw source links and provenance, but not a second independent human evaluator or named true experts. All strict membership-specific expert labels remain `unknown`.
2. **Historical team membership:** public team member endpoints returned no roster. Authenticated historical organization/audit exports or maintainer confirmation are needed; a current roster alone would still not prove historical membership.
3. **Real industrial benefit:** the full replay and break-even grid are executed; no prospective routing change was deployed, so causal savings, bug prevention, and true reviewer-workload changes remain unmeasured.
4. **Performance gate:** all credible exploratory comparisons remain below +10pp against strongest equivalent-budget baselines; therefore the original positive-effect submission hypothesis fails the declared gate.

## Recommended scientific disposition

Do not describe this as a complete positive-result FSE 2027 Industry Track submission. Either (a) secure a real maintainer partnership for historical roster/independent adjudication and a preregistered prospective evaluation, or (b) reframe as an observational negative finding/measurement study with adjusted claims and acquire more independent repositories. Do not relabel simulated researcher judgments or cost scenarios as real expert verification or ROI.

## Reproducibility

`python src/verify.py` and `python src/verify_followup.py` check prior data and new outputs. Scripts: `augment_evidence.py`, `audit_membership.py`, `shadow_roi.py`, `experiment_cv.py`, `researcher_annotations.py`, `finalize_followup.py`. Exact source links and per-record reasoning live in the JSON/CSV; all new metrics are reproducible without a GPU.

## Documentation sources

- [GitHub — CODEOWNERS rules](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)
- [GitHub — REST team members](https://docs.github.com/en/rest/teams/members)
- [GitHub — team review assignment settings](https://docs.github.com/en/organizations/organizing-members-into-teams/managing-code-review-settings-for-your-team)
