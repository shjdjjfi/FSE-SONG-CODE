# From Owners to Experts? What Public GitHub Traces Identify After CODEOWNERS Transfers

**FSE 2027 Industry Track — measurement-study experimental section. Status: public-data observational study, not a proven industrial intervention.**

## Scope and research questions

**RQ1 (Observability).** What relations can public GitHub traces identify after a path and CODEOWNERS-team transfer—file lineage, policy teams, requested teams, requested people, participating people, historical person-to-team membership, and independent expertise?

**RQ2 (Identifiability).** Are different allocations of truly relevant expertise observationally equivalent even when the recommended people, prior module reviewers and formal review responses are known?

**RQ3 (Partial identification).** What are sharp bounds on expert-coverage differences under progressively optimistic restrictions on who could be the relevant expert?

**RQ4 (Proxy robustness).** How do conclusions vary when labels are drawn from actual decisions, early invitations, all review comments, or historical review participation rather than independent expertise?

**RQ5 (Cross-surface audit).** Does the public REST Issue Events API recover team identities hidden by HTML timeline rendering, and what does it still not recover?

## Real industrial repository traces and data design

We study 9 verified, merged code-moving events in 2 open industrial repositories (`bitwarden/clients` and `grafana/grafana`), with 112 Git-confirmed rename pairs and exact base/merge CODEOWNERS snapshots. The frozen evaluation consists of 114 PR–migration-event pairs, corresponding to 103 unique PRs. The unit is a pairing because one PR can change multiple previously moved subcomponents. We retain chronological histories, reviewed people, visible review requests, SHA-256 fingerprints and URL provenance. All tasks run CPU-only; the sampled code-diff audit verified 93/114 patches before 21 rate-limit failures. Prior extraction was independently checked against GitHub REST decision-reviewer responses in 9/9 cases; six real ineligible migration controls triggered no legacy-review recommendation.

The PR-event cohort is curated and dominated by Bitwarden (96/114 pairs). It is **not a random sample of all organizations or migrations**; temporal and ownership source completeness are documented, but there is no organization-wide historical reviewer roster. The prior retrospective baseline is used only as a *foil* for measurement, not as a candidate novelty claim about algorithm accuracy.

## Formal target and sharp bounds

For PR–migration pair i, the public record includes a move relation, CODEOWNERS team handles, observable reviewer requests, prior module-review participation, and actual review actions. The latent, unobserved construct is the PR-specific set of genuinely qualified domain reviewers Eᵢ. Let Rᵢᴬ and Rᵢᴮ each be K=2 equally budgeted suggested-person sets (current path versus a 180-day transfer-aware ranker). True expert coverage is |Rᵢ∩Eᵢ|/|Eᵢ| for nonempty Eᵢ.

Define wᵢ(u)=1[u∈Rᵢᴮ]−1[u∈Rᵢᴬ]. If expertise is only known to lie within an assumption-specific finite set Uᵢ, and exactly m people in Uᵢ are truly relevant, the **sharp** lower and upper per-PR coverage differences are the means of the m smallest and m largest wᵢ(u) values. Because expert sets for separate PR–migration pairs are unrestricted beyond this explicit assumption, averaging lower and upper extrema within migration events yields a sharp event-macro identified region. These are mathematical possibility bounds, not Bayesian credible intervals or event-bootstrap confidence intervals. They make no assertion that a particular historical reviewer was in fact a member of an official team.

**Nonidentification proposition.** Whenever Rᵢᴬ\Rᵢᴮ and Rᵢᴮ\Rᵢᴬ each contain a possible expert, there are two expertise allocations consistent with the same public observation: Eᵢ={u} with u only in A gives B−A=−1, while Eᵢ={v} with v only in B gives +1. The public ownership and review history remains unchanged. The proposition is conditional on which candidates remain possible, not a statement about the *true* skill of any named person.

We validated the closed-form bounds against complete enumeration in 4500 seeded synthetic cases (seeds [17, 29, 43]); zero disagreements. These synthetic cases verify the mathematics but do not create additional real-world PRs or expertise labels.

## RQ1: Evidence coverage

All 114 cases have verified old and new CODEOWNERS team handles and at least one formal decision reviewer. The public HTML timeline records an anonymized team request in 110/114 pairs. Author-excluded named individual requests visible any time before merge appear in 96/114; those within 72 hours of PR opening in 56/114. The older unfiltered webpage request audit included usernames that were authors or appeared after the PR merge, so the cleaned count must be used when discussing eligible reviewer requests. Pre-migration path reviewers are historical *participants* rather than historical *team members*. No dated person-to-team roster or independently adjudicated person-level PR expertise is established by these records (0/114 for each validated link), which is a statement about this bounded evidence corpus rather than a claim that such people do not exist.

## RQ2: Constructive observational equivalence

The two fixed-budget policies propose different reviewer sets for **48/114** PR–migration pairs. For **41/48** switched pairs, people uniquely recommended by either policy both have identifiable earlier reviews of the migrated module. Thus two competing one-expert explanations are compatible even with documented module-specific history. In **5/48** cases, each exclusive side includes someone who actually submitted a decision review on that *same target PR*, so even requiring the expert to be among recorded decision reviewers does not resolve the expert identity.

Case study: [`bitwarden/clients` PR #15153](https://github.com/bitwarden/clients/pull/15153) concerns migrated encryption-service logic. People uniquely suggested by both policies contributed decision reviews in the visible trace. Treating only one side as *the* indispensable security-domain expert leads to conflicting coverage conclusions, while the observed PR, CODEOWNERS, request records and comments remain fixed. This is an illustrative feasibility witness, **not** a judgment about the actual qualifications of named Bitwarden engineers.

## RQ3: How much does an optimistic expertise assumption identify?

Under the strong and unsupported condition that exactly one true expert must be among the recorded decision reviewers, the event-macro treatment-minus-control identified set is **[-7.1, +12.7] percentage points**. If an expert may instead be any actual reviewer or earlier module reviewer, the bound is **[-33.6, +40.5] percentage points**. In contrast, using every decision-review participant as an equally qualified expert gives the single *proxy* difference of +3.2 pp. The proxy collapses uncertainty only by adopting an unverified assumption that participation is expertise.

With exactly two true experts restricted to actual reviewers (only 75 eligible pairs), the bound is still -2.7 to +9.7 pp. One cannot compare this smaller-cohort result to the full 114-pair rate as though the populations were identical.

## RQ4: Measurement proxy choice and robustness

The estimated K=2 difference becomes +3.6 pp if the positive set is named requests within 24 hours (N=47), +1.8 pp within 72 hours (N=56), and +0.1 pp within 168 hours (N=65). Using prior *target-path* reviewers as the supposed experts reverses the headline rank to -7.6 pp, but that proxy is especially **circular** because the current-path algorithm explicitly ranks these individuals. These proxy experiments exhibit estimand sensitivity, not evidence of a true expertise gain or loss. Cross-proxy per-event reversals are provided with matched-PR comparisons.

The nonidentification finding is robust to K=1,2,3,5, 30/90/180/365-day windows, source-code-edit filters, reviewer single-researcher case selection, time since migration, and retaining only one migration pairing per unique PR. Even the main deduplicated 103-PR sensitivity remains capable of positive or negative policy effects under the one-expert/actual-reviewer assumption; results for each setting are reproduced in `robustness.json`. The 46 positive source-substance assessments were produced by one non-blind model-assisted researcher and **do not** constitute independently adjudicated expertise.

## RQ5: A critical correction about public team requests

GitHub's rendered PR timeline sometimes says only “a team”. However, the public REST **Issue Events** response includes `review_requested` events with a `requested_team.slug` on the two source-checked PRs currently archived. Both of these cases identified the old and new CODEOWNERS team slugs. This refutes a blanket assertion that historical *requested team names* cannot be publicly observed. A time-stratified 36-PR-event sample was fixed in advance, but only **2/36** could be downloaded before an HTTP 403 endpoint failure stopped collection. This is a successful case-level triangulation, **not** representative prevalence validation. Importantly, even a recorded team slug is a *whole-PR* request, cannot necessarily be assigned to a specific moved file, and does not reveal which people belonged to that team or their required expertise at the relevant time.

## Industrial implications

Policy teams, request addressees, final reviewers, team membership and relevant expertise are distinct socio-technical objects. Companies evaluating reviewer routing or claiming handoff compliance should archive dated team membership/rotation snapshots, link review requests to specific changed components, record reviewer availability and type of substantive review, and collect independently adjudicated expertise for any claimed expert-coverage KPI. Otherwise a metric based only on completed GitHub reviews can be precise and reproducible yet answer a different question from “was the correct expert consulted?”.

This is a **measurement limitation** demonstrated with real public industrial project traces; it does not establish actual lost experts, defects, reduced response time or savings from any algorithm. The key novelty beyond ESEM 2019's general ground-truth criticism is the concrete **post-ownership-transfer** evidence graph, cross-surface team-request check, and sharp partial-identification analysis rather than treating any participation proxy as a sufficient ground truth. The large-scale 2025 CODEOWNERS adoption study offers complementary usage statistics rather than reconstructing an expert oracle after specific path handoffs.

## Limitations and open confirmation

Only two repositories provide events, eight of nine migrations come from the same company, the selection is curated, repeated PRs create dependence, and the 36-case cross-surface request audit was blocked after two cases. None of the identification regions is a random-sampling 95% confidence interval. The single model researcher's semantic judgments are not blind external truth. As a result, **do not claim externally validated generality to other organizations**. The current artifact supports a falsifiable real-data methodological **measurement / limitation finding**, not a completed multi-company industrial field deployment or a guaranteed FSE acceptance outcome.

## Primary source and literature anchors

- [GitHub CODEOWNERS docs](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)
- [GitHub Issue Events REST API](https://docs.github.com/en/rest/issues/events)
- [GitHub team member REST API](https://docs.github.com/en/rest/teams/members)
- [GitHub team code review assignment docs](https://docs.github.com/en/organizations/organizing-members-into-teams/managing-code-review-settings-for-your-team)
- [Doğan, Tüzün, Tecimer and Güvenir, ESEM 2019: Validity of Ground Truth](https://repository.bilkent.edu.tr/bitstreams/4124c08b-fe5b-4fbb-bc4f-ab877745e136/download)
- [Lulla, Kula and Treude, 2025: Automated Code Review Assignments](https://arxiv.org/abs/2512.05551)
- [FSE 2027 Industry Track official CFP](https://conf.researchr.org/track/fse-2027/fse-2027-industry-papers)
