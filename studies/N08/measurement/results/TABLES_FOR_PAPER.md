# Reproducible paper tables (observational and assumption-conditional)

All denominators are PR–migration-event pairs unless noted. One PR may enter more than one event.

## Table 1. Observable evidence channels

| Source / validation level | Observations | Per-PR-event rate |
|---|---:|---:|
| Verified old/new CODEOWNERS team handle | 114/114 | 100.0% |
| HTML displays anonymized team request | 110/114 | 96.5% |
| Named individual request ever (author excluded) | 96/114 | 84.2% |
| Named individual request within first 72h | 56/114 | 49.1% |
| Observed formal human decision reviewer | 114/114 | 100.0% |
| Verified historical individual team roster | 0/114 | 0.0% |
| Independently verified named technical expert | 0/114 | 0.0% |

**Cross-surface API case check:** 2 / 2 available PR-event pairs exposed a team slug by REST; 36 PR-event pairs were prespecified, but the API stopped early with HTTP 403. These two cases are **not** a prevalence estimator. The team names are requests on the whole PR, not necessarily for the moved component.

## Table 2. Exact sharp policy-difference identification regions

| Expert identity assumption | PR-event pairs | Sharp lower bound | Sharp upper bound |
|---|---:|---:|---:|
| Exactly one expert from actual decision reviewers | 114 | -7.1 pp | +12.7 pp |
| One expert from decision or prior module reviewers | 114 | -33.6 pp | +40.5 pp |
| One expert from any public-signal candidate | 114 | -40.5 pp | +40.5 pp |
| Exactly two experts from actual decision reviewers | 75 | -2.7 pp | +9.7 pp |
| Two experts from decision or prior module reviewers | 114 | -20.9 pp | +25.5 pp |

The intervals are **identified sets, not confidence intervals**. Different candidate sets and fixed expert counts condition on different assumptions; two-expert rows may exclude PRs with fewer eligible candidates.

## Table 3. Proxy-dependent observed Recall@2

| Proxy used as though it were a label | N | Current path | 180-day handoff | Difference |
|---|---:|---:|---:|---:|
| Formal APPROVED/CHANGES_REQUESTED | 114 | 30.1% | 33.3% | +3.2 pp |
| Any submitted review | 113 | 29.1% | 32.4% | +3.3 pp |
| Named requests in 24h | 47 | 23.9% | 27.5% | +3.6 pp |
| Named requests in 72h | 56 | 39.3% | 41.1% | +1.8 pp |
| Named requests in 168h | 65 | 40.4% | 40.6% | +0.1 pp |
| Named requests ever | 96 | 31.4% | 34.0% | +2.6 pp |
| Previous source reviewers (circular) | 114 | 10.2% | 12.4% | +2.2 pp |
| Previous target reviewers (circular) | 101 | 42.8% | 35.2% | -7.6 pp |

Proxy sizes differ; no row above is independently adjudicated person-level expertise. Proxy source/target history is endogenous to both recommender algorithms.

## Table 4. Robustness of one-expert reviewer-only sharp region

| Sample / budget | N | Switches | Lower | Upper |
|---|---:|---:|---:|---:|
| All, K=1 | 114 | 41 | -15.0 pp | +5.5 pp |
| All, K=2 | 114 | 48 | -7.1 pp | +12.7 pp |
| All, K=3 | 114 | 56 | -5.7 pp | +11.5 pp |
| All, K=5 | 114 | 63 | -11.0 pp | +6.5 pp |
| Source-code touched | 102 | 44 | -6.8 pp | +17.3 pp |
| Focused (post hoc) | 58 | 25 | +0.9 pp | +13.5 pp |
| Single researcher yes (non-blind) | 46 | 23 | -2.7 pp | +12.8 pp |
| Deduplicate, first transfer | 103 | 44 | -6.1 pp | +11.6 pp |
| Deduplicate, last transfer | 103 | 45 | -5.4 pp | +12.2 pp |
| Opened ≤90d | 46 | 34 | -17.0 pp | +16.6 pp |
| Opened >90d | 68 | 14 | -2.3 pp | +6.0 pp |
