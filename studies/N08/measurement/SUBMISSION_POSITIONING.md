# Submission positioning and evidence gates — 2026-11-15

## Working title

**From Owners to Experts? What Public GitHub Traces Identify After CODEOWNERS Transfers**

## Abstract draft (claim strength constrained by recorded data)

Cross-team file transfers alter CODEOWNERS routing, but a recorded reviewer
is not necessarily the engineer whose expertise a changed component requires.
We investigate which parts of this distinction can be empirically resolved
from public GitHub histories. We reconstruct nine verified ownership handoffs
in two industrial open-source repositories, comprising 112 moved-file pairs
and 114 pull-request–transfer pairs (103 unique pull requests). For each pair
we map source lineage, historical code-owner teams, public review requests,
module-review history and recorded human review decisions. We find that 48
pairs cause a change between fixed-budget current-path and transfer-aware
reviewer lists. In 41 of these, both exclusively recommended sides have prior
module-review evidence; in five, both sides even reviewed the target PR.
Consequently the same trace admits opposing plausible expert-coverage
assessments without assuming who is genuinely qualified. We derive sharp
partial-identification bounds: under the restrictive assumption that each PR
has exactly one expert drawn from its observed decision reviewers, the
event-macro coverage difference is identified only within −7.1 to +12.7
percentage points, versus the +3.2-point observed-reviewer proxy. A public
Issue Events case check additionally recovers team-request handles absent
from the rendered HTML, while leaving historical human team membership and
expertise unresolved. The study distinguishes observable policy and behavior
from latent knowledge, identifies which fields organizations would need to
archive, and explicitly does not claim realized productivity improvements.

## What this paper contributes beyond generic ground-truth warnings

1. A **transfer-specific longitudinal evidence graph**, distinguishing the
   old and new policy owner, whole-PR team request, person request, submitted
   review, dated team membership and *person × PR* expertise.
2. A **constructive nonidentification result on real public cases**: fixed
   observable records permit different true expertise allocations and even
   opposite method rankings; public data alone cannot select one allocation.
3. **Sharp conditional identification regions** under increasingly restrictive
   person-candidate and expert-count assumptions, with exhaustive mathematics
   tests and transparent PR/event aggregation.
4. **Source-surface correction**: rendered opaque team requests are not proof
   that public GitHub API calls cannot reveal the requested team slug; two
   audited cases recover it. Historical membership remains a different link.
5. **Measurement sensitivity** across decision, invitation, comment and
   historical-review proxies, plus dedup, time and ranking-budget checks.

The conceptual concern is anticipated by Doğan et al., *Investigating the
Validity of Ground Truth in Code Reviewer Recommendation Studies*, ESEM 2019.
This paper's novelty claim must stay focused on **ownership transfers,
identifiability, and explicit evidence-tier measurement** rather than claim to
be the first paper to criticize reviewer-derived ground truth.

## Reporting ledger

| Required factual claim or experiment | State | Claim boundary |
| --- | --- | --- |
| Real historical migration and owner-policy anchors | **Done** | 9 events, 112 git renames, 2 repos |
| PR-level multi-source review and request trace | **Done** | 114 PR–event pairs; 103 unique PRs |
| Exact visible versus missing construct matrix | **Done** | Team/PR participant observability, no roster oracle |
| Constructive real observational-equivalence witnesses | **Done** | 48 switches, 41 historical, 5 actual-reviewer two-sided witnesses |
| Sharp conditional expert-coverage identification bounds | **Done** | Not confidence bounds or known true expertise |
| Mathematical bound correctness tests | **Done** | 4,500 brute force checks |
| K/grace/code/dedup/time/repo robustness | **Done** | No independent organizations added |
| Public HTML versus REST team-slug cross-check | **Partial** | 2/36 sample due HTTP403; no prevalence estimate |
| Historical human team-member map on move date | **Unavailable** | 0 independently established; do not manufacture |
| Independent qualified-expert gold standard | **Unavailable** | 0; the paper studies this very identification gap |
| Independent multi-company representative generalization | **Not established** | Two selected repositories, 8/9 events from one org |
| Real causal industrial productivity or cost savings | **Not measured** | Not a required outcome for the revised measurement question |
| Independent organizational confirmation of recommendations | **Not done** | Would require engineers/maintainers, missing from public traces |

**Publication judgment:** The completed offline evidence could support a
carefully scoped empirical/experience **short paper** if its transfer-specific
novelty and industry lessons withstand reviewer scrutiny. The sample and
API audit are not strong enough to claim a general multi-company industrial
deployment evaluation or an independently validated expertise ground truth.
No acceptance likelihood is promised. Check the venue's active 2027 call,
page limits, industry relevance and reproducibility policy when formatting.

## Future work requiring new authority or evidence

- Extend independent project coverage by a prospectively defined migration
  sampling frame, rather than selecting cases where an effect is favorable.
- Obtain a rate-compliant, authorized Issue Events audit in many companies;
  do not retry an access-denied endpoint with an identity workaround.
- Seek maintainer-consented dated roster/rotation snapshots and a multi-rater
  expertise rubric, with a blind adjudication protocol and disagreement rate.
- If industrial efficiency is separately claimed, prospectively record actual
  time on review allocation, reviewer availability and escalations, and define
  a deployment-appropriate causal control.

None of those steps can be represented by an AI assistant pretending to be
an independent company engineer. A model-written technical assessment is a
single researcher's analysis, not independent expert ground truth.
