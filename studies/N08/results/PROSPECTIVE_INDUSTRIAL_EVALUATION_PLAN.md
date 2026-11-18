# Preregistered prospective protocol required before claiming industrial benefit

**Status:** Design only. Nothing in this file describes an experiment that has been deployed or a company that has approved participation.

## Essential inputs that public GitHub history could not provide

1. An authorized, date-stamped historical team-membership export at every migration date, including membership changes during the following 180 days. An authenticated **current** roster alone is insufficient. Store a salted stable ID for each account, a team ID, effective dates, and an attestation that the export is complete; do not publish private membership.
2. A maintainer-approved, independently adjudicated expert set for each evaluation PR. Two different humans with relevant component knowledge individually read the migration design, code before/after, the target PR diff and independently available *pre-opening* design notes. Neither sees the ranking output nor the actual review request/review outcome. Unknown is not negative. A third independent human resolves disagreement. Store individual rating, confidence, evidence source and adjudicated decision; publish only consented, non-sensitive data.
3. Complete review request/assignment events, including the people auto-assigned when an anonymized team was requested; acceptance/rejection times; actual human time spent reviewing; and post-merge regression incident links.
4. Authorization to instrument review routing in a real workflow without exposing credentials or personal staff lists to the artifact. Obtain written opt-in from repo maintainers and comply with organizational privacy and research policies.

## Treatment and control

- **Unit:** independent migrated component (not an individual PR when review teams span PRs), randomized after the migration plan is frozen.
- **Strata:** application and team; pre-migration review volume; security-criticality; components with less than 20 post-migration PRs. A component whose reviewers would handle both treatment and control may require project-level cluster randomization due to contamination.
- **Control A:** real CODEOWNERS automatic routing (resolved to actual historical members), followed by the strongest available equal-budget historical reviewer recommendation.
- **Treatment B:** a transfer-aware 180-day policy that recommends from the old and new component evidence; the time-window and model configuration are **fixed before** test outcomes are observed.
- **Budget:** K=2 named requests per eligible PR in both arms. If a team request already expands to named reviewers, treat those assignments as consuming slots; log who receives the request. Do not quietly add a third expert to treatment PRs.
- **Eligibility:** substantively changed moved code, judged from a code-diff classifier trained entirely on earlier migration events; lock eligibility rules before randomization and report the full intention-to-treat population.
- **Safety:** maintain mandatory security/release sign-offs independently of the randomized K=2 recommendations; nonmandatory invites alone may vary. Obtain participant consent as required.

## Preregistered primary endpoint

For each PR with nonempty, independently adjudicated expert set \(E_i\), define expert coverage \(c_i=|R_i\cap E_i|/|E_i|\), where \(R_i\) contains the **actually invited identifiable human** reviewers within the preregistered request window, excluding the author. Estimate \(\Delta=\mathbb{E}[c_i\mid B]-\mathbb{E}[c_i\mid A]\) using intention-to-treat, with migrated-component cluster bootstrap and project fixed effects where feasible.

**Confirmatory success** must require (a) a point-estimate advantage of at least +10 percentage points over the strongest equal-budget control, (b) an uncertainty interval that excludes 0, and (c) no meaningful deterioration in reviewer cost and required security-review compliance. Report all unknown-label and missing-outcome rates. Do not substitute observed participating reviewers for \(E_i\).

## Industrial value: measured, not imagined

Collect the following *real operational logs* in both randomized arms:

| Outcome | Precise definition | Limitations |
|---|---|---|
| Time to actionable review | Request timestamp to earliest substantive review with traceable code feedback | Review author must be a real, available assignee; stratify by PR size |
| Availability / response | Requested person's response or decline; reviewer reassignment count | Request time is distinct from PR-open time |
| Attention cost | Explicitly measured minutes active per PR, or a small calibrated, voluntary time diary | Comment count is not a measured time cost |
| Review-quality process | Corrected defects in review, nontrivial change requests, acceptance of corrected patch | No guarantee reviewers see all bugs |
| Downstream quality | Relevant revert, regression, incident or reopening within 30/90 days | Needs independent incident attribution; often rare |
| Total industrial net value | Avoided documented engineering/incident cost minus added measured attention and coordination | Price assumptions and currency must be registered in advance |

Analyze time-to-event outcomes with cluster-aware survival methods, repeated-measures outcomes with mixed models and per-project effects; show intention-to-treat and missingness sensitivity. Distinguish administrative censorship (closed/abandoned PR) from no action.

## Power and stop criteria

- The 9 migrations in this artifact are concentrated in only two organizations and cannot provide a defensible power guarantee for new industrial teams. Run a pilot at **at least three otherwise independent organizations**; then calculate a cluster-correlation-adjusted sample size before confirming the exact power target. Do not call an arbitrary fixed PR count independent replicates.
- Hold out complete migration events and at least one separate organization for final evaluation. Declare any tuning of a transfer window using held-out outcomes exploratory and reset with a truly fresh test cohort.
- Stop if intervention creates more than the approved reviewer burden or violates security sign-offs. Record negative/zero effects rather than dropping unfavorable migrations.

## What would constitute closure

External closure requires signed maintainer authorization, date-specific human/team mapping, two independent human oracle sheets with agreement and disagreements, frozen code and assignment logs, raw de-identified cost observations, and a prospective primary-effect estimate meeting the above gate. None is present in the current public-data archive. The `SINGLE_RESEARCHER_ANNOTATIONS.csv` file must never be retitled an independent human oracle.
