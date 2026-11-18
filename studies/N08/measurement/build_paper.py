#!/usr/bin/env python3
"""Generate manuscript-ready measurement tables/figures from measured JSON."""

import csv
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
RESULTS=ROOT/'measurement'/'results'
FIG=RESULTS/'figures'
FIG.mkdir(exist_ok=True)


def read(name):return json.loads((RESULTS/name).read_text(encoding='utf-8'))


def pct(x):return f'{100*x:+.1f}' if x is not None else 'n/a'


def save_fig(fig,stem):
    fig.tight_layout()
    for ext in ('svg','png'):fig.savefig(FIG/f'{stem}.{ext}',dpi=190,bbox_inches='tight')
    plt.close(fig)


def make_figures(m,r):
    counts=m['observable_stage_counts'];N=m['n_pr_event_pairs']
    levels=[
        ('Historical team handles',counts['verified_code_migration_and_team_handles']),
        ('Opaque team request (HTML)',counts['html_team_review_request_anonymized']),
        ('Named request before 72h',counts['public_named_request_first72h']),
        ('Decision reviewer observed',counts['any_actual_formal_decision_reviewer']),
        ('Verified historical team roster',0),
        ('Independent named expert truth',0)]
    fig,ax=plt.subplots(figsize=(9,4.8))
    ys=list(range(len(levels)))
    bars=ax.barh(ys,[100*x/N for _,x in levels],color=['#3976ac','#65a8bd','#b38b57','#568768','#aeb4bc','#aeb4bc'])
    ax.set_yticks(ys,[x for x,_ in levels]);ax.invert_yaxis();ax.set_xlim(0,115)
    ax.set_xlabel('Observed PR–migration-event pairs (%) — not a nested hierarchy')
    for i,(bar,(_,count)) in enumerate(zip(bars,levels)):
        ax.text(bar.get_width()+1,bar.get_y()+bar.get_height()/2,f'{count}/{N}',va='center',fontsize=9)
    ax.set_title('Trace observability is not expert identifiability')
    ax.grid(axis='x',alpha=.2)
    save_fig(fig,'fig_m1_observability_stages')

    keys=[('Observed reviewers only','observed_decision_reviewer_only'),
          ('Observed or historical module reviewers','all_component_review_history_or_decision'),
          ('Any public-signal candidate','all_candidate_pool')]
    fig,ax=plt.subplots(figsize=(9,4.0))
    for i,(title,k) in enumerate(keys):
        b=m['sharp_expert_recall_delta_identification_intervals'][k]
        ax.plot([100*b['lower'],100*b['upper']],[i,i],lw=10,solid_capstyle='round',color=['#3681a9','#e4a44e','#a75f63'][i])
        for v in (b['lower'],b['upper']):ax.text(100*v,i-.18,f'{100*v:+.1f}',ha='center',fontsize=9)
    ax.axvline(0,lw=1.1,color='black',alpha=.5)
    ax.scatter([100*m['proxy_definition_results']['decision_reviewers']['event_macro_delta']],[1],s=75,c='black',zorder=5,
               label='Observed-reviewer proxy (+3.2 pp), not true expertise')
    ax.set_yticks(range(3),[x for x,_ in keys]);ax.set_ylim(2.5,-.7)
    ax.set_xlabel('Sharp possible policy coverage difference (percentage points)')
    ax.set_xlim(-48,48)
    ax.set_title('One unknown true expert per PR — assumption-conditional identification bounds')
    ax.legend(loc='lower right',fontsize=8);ax.grid(axis='x',alpha=.16)
    save_fig(fig,'fig_m2_sharp_identification_intervals')

    items=[('Formal decision', 'decision_reviewers'),('Any submitted review','any_formal_review_state'),
           ('Named request in 24h','named_request_24h'),('Named request in 72h','named_request_72h'),
           ('Named request in 168h','named_request_168h'),('Named request ever','named_request_ever'),
           ('Previous source reviewers','pre_source_reviewers'),('Previous target reviewers','prior_target_reviewers')]
    fig,ax=plt.subplots(figsize=(9.5,4.9))
    vals=[100*m['proxy_definition_results'][key]['event_macro_delta'] for _,key in items]
    colors=['#2c708f' if v>=0 else '#ab5e49' for v in vals]
    bars=ax.bar(range(len(items)),vals,color=colors)
    ax.axhline(0,lw=1,color='black');ax.grid(axis='y',alpha=.2)
    ax.set_xticks(range(len(items)),[f'{name}\nn={m["proxy_definition_results"][key]["n_pr_event_pairs"]}' for name,key in items],rotation=20,ha='right',fontsize=8)
    ax.set_ylabel('180-day handoff minus current-path Recall@2 (pp)')
    ax.set_title('The apparent ranking depends on the observable proxy')
    for bar,val in zip(bars,vals):
        ax.text(bar.get_x()+bar.get_width()/2,val+(.24 if val>=0 else -.24),f'{val:+.1f}',ha='center',
                va='bottom' if val>=0 else 'top',fontsize=9)
    fig.subplots_adjust(bottom=.15)
    save_fig(fig,'fig_m3_proxy_choice_sensitivity')

    k=[1,2,3,5]
    lo=[100*r['settings'][f'budget_{x}']['bounds_observed_only_one_expert'][0] for x in k]
    hi=[100*r['settings'][f'budget_{x}']['bounds_observed_only_one_expert'][1] for x in k]
    fig,ax=plt.subplots(figsize=(7.5,4.2))
    ax.axhline(0,color='black',lw=.9)
    for x,l,h in zip(k,lo,hi):
        ax.vlines(x,l,h,color='#167b93',linewidth=9,alpha=.78)
        ax.text(x,l-1,f'{l:+.1f}',ha='center',fontsize=9)
        ax.text(x,h+1,f'{h:+.1f}',ha='center',fontsize=9)
    ax.set_xticks(k,['K=1','K=2','K=3','K=5'])
    ax.set_ylabel('Sharp coverage-delta bounds (pp)')
    ax.set_title('Non-identifiability remains at different review budgets')
    ax.set_ylim(min(lo)-6,max(hi)+6)
    ax.grid(axis='y',alpha=.15)
    save_fig(fig,'fig_m4_budget_identification_bounds')


def make_tables(m,r):
    output_path=RESULTS/'TABLES_FOR_PAPER.md'
    stages=m['observable_stage_counts'];n=m['n_pr_event_pairs']
    lines=['# Reproducible paper tables (observational and assumption-conditional)', '',
       'All denominators are PR–migration-event pairs unless noted. One PR may enter more than one event.', '',
       '## Table 1. Observable evidence channels', '',
       '| Source / validation level | Observations | Per-PR-event rate |', '|---|---:|---:|']
    for label,key in [('Verified old/new CODEOWNERS team handle','verified_code_migration_and_team_handles'),
        ('HTML displays anonymized team request','html_team_review_request_anonymized'),
        ('Named individual request ever (author excluded)','public_named_request_ever'),
        ('Named individual request within first 72h','public_named_request_first72h'),
        ('Observed formal human decision reviewer','any_actual_formal_decision_reviewer'),
        ('Verified historical individual team roster','verified_historic_person_to_team_roster'),
        ('Independently verified named technical expert','independently_adjudicated_person_to_pr_expertise')]:
        c=stages[key];lines.append(f'| {label} | {c}/{n} | {100*c/n:.1f}% |')
    api=m['github_issue_events_api_cross_surface_audit']
    lines+=['',f'**Cross-surface API case check:** {api["api_team_slug_recovered"]} / {api["sampled_pairs_api_available"]} available PR-event pairs exposed a team slug by REST; 36 PR-event pairs were prespecified, but the API stopped early with HTTP 403. These two cases are **not** a prevalence estimator. The team names are requests on the whole PR, not necessarily for the moved component.', '',
       '## Table 2. Exact sharp policy-difference identification regions', '',
       '| Expert identity assumption | PR-event pairs | Sharp lower bound | Sharp upper bound |',
       '|---|---:|---:|---:|']
    for label,key in [('Exactly one expert from actual decision reviewers','observed_decision_reviewer_only'),
        ('One expert from decision or prior module reviewers','all_component_review_history_or_decision'),
        ('One expert from any public-signal candidate','all_candidate_pool'),
        ('Exactly two experts from actual decision reviewers','observed_decision_reviewers_two_experts'),
        ('Two experts from decision or prior module reviewers','component_history_or_decision_two_experts')]:
        b=m['sharp_expert_recall_delta_identification_intervals'][key]
        lines.append(f'| {label} | {b["pr_event_pairs"]} | {pct(b["lower"])} pp | {pct(b["upper"])} pp |')
    lines+=['', 'The intervals are **identified sets, not confidence intervals**. Different candidate sets and fixed expert counts condition on different assumptions; two-expert rows may exclude PRs with fewer eligible candidates.', '',
       '## Table 3. Proxy-dependent observed Recall@2', '',
       '| Proxy used as though it were a label | N | Current path | 180-day handoff | Difference |',
       '|---|---:|---:|---:|---:|']
    for label,key in [('Formal APPROVED/CHANGES_REQUESTED','decision_reviewers'),
        ('Any submitted review','any_formal_review_state'),
        ('Named requests in 24h','named_request_24h'),
        ('Named requests in 72h','named_request_72h'),
        ('Named requests in 168h','named_request_168h'),
        ('Named requests ever','named_request_ever'),
        ('Previous source reviewers (circular)','pre_source_reviewers'),
        ('Previous target reviewers (circular)','prior_target_reviewers')]:
        p=m['proxy_definition_results'][key]
        lines.append(f'| {label} | {p["n_pr_event_pairs"]} | {100*p["event_macro_current_path"]:.1f}% | {100*p["event_macro_handoff"]:.1f}% | {pct(p["event_macro_delta"])} pp |')
    lines+=['','Proxy sizes differ; no row above is independently adjudicated person-level expertise. Proxy source/target history is endogenous to both recommender algorithms.', '',
       '## Table 4. Robustness of one-expert reviewer-only sharp region', '',
       '| Sample / budget | N | Switches | Lower | Upper |', '|---|---:|---:|---:|---:|']
    keys=[('All, K=1','budget_1'),('All, K=2','budget_2'),('All, K=3','budget_3'),('All, K=5','budget_5'),
        ('Source-code touched','code_touching_mechanical'),('Focused (post hoc)','focused_posthoc'),
        ('Single researcher yes (non-blind)','semantic_researcher_yes_nonblind'),
        ('Deduplicate, first transfer','unique_pr_first_event_sensitivity'),
        ('Deduplicate, last transfer','unique_pr_last_event_sensitivity'),
        ('Opened ≤90d','opened_within90d'),('Opened >90d','opened_after90d')]
    for label,key in keys:
        z=r['settings'][key];lo,hi=z['bounds_observed_only_one_expert']
        lines.append(f'| {label} | {z["n_pairs"]} | {z["switched"]} | {pct(lo)} pp | {pct(hi)} pp |')
    output_path.write_text('\n'.join(lines)+'\n',encoding='utf-8')


def write_reports(m,r,validation):
    n=m['n_pr_event_pairs'];e=m['n_events'];P=m['n_independent_repositories']
    w=m['world_witness_counts'];api=m['github_issue_events_api_cross_surface_audit']
    o=m['sharp_expert_recall_delta_identification_intervals']['observed_decision_reviewer_only']
    h=m['sharp_expert_recall_delta_identification_intervals']['all_component_review_history_or_decision']
    info=m['observable_stage_counts'];proxy=m['proxy_definition_results']
    audit=ROOT/'results'/'rest_review_validation.json'
    proof=load_external(audit)
    report=f'''# From Owners to Experts? What Public GitHub Traces Identify After CODEOWNERS Transfers

**FSE 2027 Industry Track — measurement-study experimental section. Status: public-data observational study, not a proven industrial intervention.**

## Scope and research questions

**RQ1 (Observability).** What relations can public GitHub traces identify after a path and CODEOWNERS-team transfer—file lineage, policy teams, requested teams, requested people, participating people, historical person-to-team membership, and independent expertise?

**RQ2 (Identifiability).** Are different allocations of truly relevant expertise observationally equivalent even when the recommended people, prior module reviewers and formal review responses are known?

**RQ3 (Partial identification).** What are sharp bounds on expert-coverage differences under progressively optimistic restrictions on who could be the relevant expert?

**RQ4 (Proxy robustness).** How do conclusions vary when labels are drawn from actual decisions, early invitations, all review comments, or historical review participation rather than independent expertise?

**RQ5 (Cross-surface audit).** Does the public REST Issue Events API recover team identities hidden by HTML timeline rendering, and what does it still not recover?

## Real industrial repository traces and data design

We study {e} verified, merged code-moving events in {P} open industrial repositories (`bitwarden/clients` and `grafana/grafana`), with 112 Git-confirmed rename pairs and exact base/merge CODEOWNERS snapshots. The frozen evaluation consists of {n} PR–migration-event pairs, corresponding to {m['n_unique_prs']} unique PRs. The unit is a pairing because one PR can change multiple previously moved subcomponents. We retain chronological histories, reviewed people, visible review requests, SHA-256 fingerprints and URL provenance. All tasks run CPU-only; the sampled code-diff audit verified 93/114 patches before 21 rate-limit failures. Prior extraction was independently checked against GitHub REST decision-reviewer responses in {proof['matched']}/{proof['sample_size']} cases; six real ineligible migration controls triggered no legacy-review recommendation.

The PR-event cohort is curated and dominated by Bitwarden ({sum(x['repo']=='bitwarden/clients' for x in load_external(ROOT/'results'/'predictions.json'))}/{n} pairs). It is **not a random sample of all organizations or migrations**; temporal and ownership source completeness are documented, but there is no organization-wide historical reviewer roster. The prior retrospective baseline is used only as a *foil* for measurement, not as a candidate novelty claim about algorithm accuracy.

## Formal target and sharp bounds

For PR–migration pair i, the public record includes a move relation, CODEOWNERS team handles, observable reviewer requests, prior module-review participation, and actual review actions. The latent, unobserved construct is the PR-specific set of genuinely qualified domain reviewers Eᵢ. Let Rᵢᴬ and Rᵢᴮ each be K=2 equally budgeted suggested-person sets (current path versus a 180-day transfer-aware ranker). True expert coverage is |Rᵢ∩Eᵢ|/|Eᵢ| for nonempty Eᵢ.

Define wᵢ(u)=1[u∈Rᵢᴮ]−1[u∈Rᵢᴬ]. If expertise is only known to lie within an assumption-specific finite set Uᵢ, and exactly m people in Uᵢ are truly relevant, the **sharp** lower and upper per-PR coverage differences are the means of the m smallest and m largest wᵢ(u) values. Because expert sets for separate PR–migration pairs are unrestricted beyond this explicit assumption, averaging lower and upper extrema within migration events yields a sharp event-macro identified region. These are mathematical possibility bounds, not Bayesian credible intervals or event-bootstrap confidence intervals. They make no assertion that a particular historical reviewer was in fact a member of an official team.

**Nonidentification proposition.** Whenever Rᵢᴬ\\Rᵢᴮ and Rᵢᴮ\\Rᵢᴬ each contain a possible expert, there are two expertise allocations consistent with the same public observation: Eᵢ={{u}} with u only in A gives B−A=−1, while Eᵢ={{v}} with v only in B gives +1. The public ownership and review history remains unchanged. The proposition is conditional on which candidates remain possible, not a statement about the *true* skill of any named person.

We validated the closed-form bounds against complete enumeration in {validation['n_bruteforce_cases']} seeded synthetic cases (seeds {validation['seeds']}); zero disagreements. These synthetic cases verify the mathematics but do not create additional real-world PRs or expertise labels.

## RQ1: Evidence coverage

All {n} cases have verified old and new CODEOWNERS team handles and at least one formal decision reviewer. The public HTML timeline records an anonymized team request in {info['html_team_review_request_anonymized']}/{n} pairs. Author-excluded named individual requests visible any time before merge appear in {info['public_named_request_ever']}/{n}; those within 72 hours of PR opening in {info['public_named_request_first72h']}/{n}. The older unfiltered webpage request audit included usernames that were authors or appeared after the PR merge, so the cleaned count must be used when discussing eligible reviewer requests. Pre-migration path reviewers are historical *participants* rather than historical *team members*. No dated person-to-team roster or independently adjudicated person-level PR expertise is established by these records (0/{n} for each validated link), which is a statement about this bounded evidence corpus rather than a claim that such people do not exist.

## RQ2: Constructive observational equivalence

The two fixed-budget policies propose different reviewer sets for **{w['switched']}/{n}** PR–migration pairs. For **{w['opposite_worlds_both_candidates_prior_module_reviewers']}/{w['switched']}** switched pairs, people uniquely recommended by either policy both have identifiable earlier reviews of the migrated module. Thus two competing one-expert explanations are compatible even with documented module-specific history. In **{w['opposite_worlds_both_candidates_actual_decision_reviewers']}/{w['switched']}** cases, each exclusive side includes someone who actually submitted a decision review on that *same target PR*, so even requiring the expert to be among recorded decision reviewers does not resolve the expert identity.

Case study: [`bitwarden/clients` PR #15153](https://github.com/bitwarden/clients/pull/15153) concerns migrated encryption-service logic. People uniquely suggested by both policies contributed decision reviews in the visible trace. Treating only one side as *the* indispensable security-domain expert leads to conflicting coverage conclusions, while the observed PR, CODEOWNERS, request records and comments remain fixed. This is an illustrative feasibility witness, **not** a judgment about the actual qualifications of named Bitwarden engineers.

## RQ3: How much does an optimistic expertise assumption identify?

Under the strong and unsupported condition that exactly one true expert must be among the recorded decision reviewers, the event-macro treatment-minus-control identified set is **[{pct(o['lower'])}, {pct(o['upper'])}] percentage points**. If an expert may instead be any actual reviewer or earlier module reviewer, the bound is **[{pct(h['lower'])}, {pct(h['upper'])}] percentage points**. In contrast, using every decision-review participant as an equally qualified expert gives the single *proxy* difference of +{100*proxy['decision_reviewers']['event_macro_delta']:.1f} pp. The proxy collapses uncertainty only by adopting an unverified assumption that participation is expertise.

With exactly two true experts restricted to actual reviewers (only {m['sharp_expert_recall_delta_identification_intervals']['observed_decision_reviewers_two_experts']['pr_event_pairs']} eligible pairs), the bound is still {pct(m['sharp_expert_recall_delta_identification_intervals']['observed_decision_reviewers_two_experts']['lower'])} to {pct(m['sharp_expert_recall_delta_identification_intervals']['observed_decision_reviewers_two_experts']['upper'])} pp. One cannot compare this smaller-cohort result to the full 114-pair rate as though the populations were identical.

## RQ4: Measurement proxy choice and robustness

The estimated K=2 difference becomes +{100*proxy['named_request_24h']['event_macro_delta']:.1f} pp if the positive set is named requests within 24 hours (N={proxy['named_request_24h']['n_pr_event_pairs']}), +{100*proxy['named_request_72h']['event_macro_delta']:.1f} pp within 72 hours (N={proxy['named_request_72h']['n_pr_event_pairs']}), and +{100*proxy['named_request_168h']['event_macro_delta']:.1f} pp within 168 hours (N={proxy['named_request_168h']['n_pr_event_pairs']}). Using prior *target-path* reviewers as the supposed experts reverses the headline rank to {100*proxy['prior_target_reviewers']['event_macro_delta']:+.1f} pp, but that proxy is especially **circular** because the current-path algorithm explicitly ranks these individuals. These proxy experiments exhibit estimand sensitivity, not evidence of a true expertise gain or loss. Cross-proxy per-event reversals are provided with matched-PR comparisons.

The nonidentification finding is robust to K=1,2,3,5, 30/90/180/365-day windows, source-code-edit filters, reviewer single-researcher case selection, time since migration, and retaining only one migration pairing per unique PR. Even the main deduplicated 103-PR sensitivity remains capable of positive or negative policy effects under the one-expert/actual-reviewer assumption; results for each setting are reproduced in `robustness.json`. The 46 positive source-substance assessments were produced by one non-blind model-assisted researcher and **do not** constitute independently adjudicated expertise.

## RQ5: A critical correction about public team requests

GitHub's rendered PR timeline sometimes says only “a team”. However, the public REST **Issue Events** response includes `review_requested` events with a `requested_team.slug` on the two source-checked PRs currently archived. Both of these cases identified the old and new CODEOWNERS team slugs. This refutes a blanket assertion that historical *requested team names* cannot be publicly observed. A time-stratified 36-PR-event sample was fixed in advance, but only **{api['sampled_pairs_api_available']}/36** could be downloaded before an HTTP 403 endpoint failure stopped collection. This is a successful case-level triangulation, **not** representative prevalence validation. Importantly, even a recorded team slug is a *whole-PR* request, cannot necessarily be assigned to a specific moved file, and does not reveal which people belonged to that team or their required expertise at the relevant time.

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
'''
    (RESULTS/'PAPER_EXPERIMENTS_EN.md').write_text(report,encoding='utf-8')
    chinese=f'''# N08 新研究方向：公开 GitHub 记录对代码知识移交的可识别性

**定位**：FSE 2027 Industry Track 工业实证测量研究；不是“提高专家推荐精度”的算法效果论文。工业相关性是公开真实工业仓库的软件开发治理；尚无企业内部合作部署。

## 核心结论

9 次真实跨团队迁移、112 个代码 rename 映射、114 个 PR–迁移事件对（103 个独立 PR，2 个仓库）。真实代码历史、CODEOWNERS 规则、公开评审时间线已审计。

**验证层次**：114/114 可见旧/新负责团队；{info['html_anonymized_team_review_request'] if 'html_anonymized_team_review_request' in info else info['html_team_review_request_anonymized']}/114 的网页时间线将团队请求匿名显示；严格剔除当前作者及合并后请求后，{info['public_named_request_first72h']}/114 在前72小时可见具名请求，{info['public_named_request_ever']}/114 在合并前某个时点可见具名请求；114/114 有真实正式评审。历史正式团队成员身份、独立具名领域专家两项均为 **0 个独立验证案例**（不等于“真实没有专家”）。

**重要纠错**：公开 REST Issue Events API 能在已取得的两个完整案例中恢复旧、新团队的真实请求标识，网页“a team”不意味着 GitHub 完全没有公开团队请求记录。预定36案例，但 API 请求出现 HTTP403，按访问限制停止；2/36 只能是案例核对，不是总体比率。

**不可识别性**：48/114 个 PR–迁移事件对中两套 K=2 方法推荐不同人；41/48 个案例两侧不同人选都拥有之前审查相应模块的公开记录；其中 5/48 个案例两侧不同人选都提交过目标 PR 的正式评审。研究并不判断他们的真实水平，而是构造两套与同一公开记录兼容、但专家覆盖结论相反的可行解释。

**条件尖锐边界**：假设每 PR 恰有一位相关专家且其必为实际正式评审人，180天移交策略与当前路径相比的真实专家覆盖差异只可约束在 **{pct(o['lower'])} 至 {pct(o['upper'])} 个百分点**；如允许这位专家来自任何此前审查过模块的人，扩展到 **{pct(h['lower'])} 至 {pct(h['upper'])} 个百分点**。不是置信区间，不能据此给真实专家覆盖率打分。

**结果对代理标签敏感**：现有正式评审者集合做标签时差异 +{100*proxy['decision_reviewers']['event_macro_delta']:.1f}pp；前72小时具名请求做代理标签时 +{100*proxy['named_request_72h']['event_macro_delta']:.1f}pp（仅{proxy['named_request_72h']['n_pr_event_pairs']}个有标签），此前新路径历史评审者做代理标签时 {100*proxy['prior_target_reviewers']['event_macro_delta']:+.1f}pp（这项对当前路径算法有循环偏向）。这些都不是独立专家真值，不能选取有利的做代理金标准。

## 已执行验证

- 4,500 组随机合成集合逐例穷举，尖锐上下界公式误差为零。
- K=1/2/3/5 和30/90/180/365天移交窗口敏感性复算。
- 机械源码筛选、事后聚焦子集、单研究者代码判断、迁移90天时间分层、两仓库分层。
- 按 PR 去重为103条后重新计算上下界，符号仍不唯一。
- 之前9/9 REST 正式评审核查、6/6 迁移门控负控、93/114 源代码 hash 验证仍保留。

## 写作边界

这篇论文可以主张“即使真实公开证据完备到推荐、请求与已完成评审，知识覆盖也通常无法唯一判定”，不能主张“确实漏评了专家多少次”“某算法应当胜出”或“帮助企业节省多少小时”。缺少多个独立组织的随机迁移样本，且 GitHub REST 跨来源核验在2/36时停止；因此目前的工业跨组织泛化证据仍不足以保证高质量 Long Paper 的充分性。

图表：`TABLES_FOR_PAPER.md`、`figures/fig_m1`–`fig_m4`；机器结果：`measurement_metrics.json`、`per_pr_observability_and_witnesses.json`、`robustness.json`、`synthetic_bounds_validation.json`。
'''
    (RESULTS/'EXPERIMENT_REPORT_CN.md').write_text(chinese,encoding='utf-8')


def load_external(path):return json.loads(path.read_text(encoding='utf-8'))


def main():
    m=read('measurement_metrics.json')
    r=read('robustness.json')
    v=read('synthetic_bounds_validation.json')
    make_tables(m,r)
    make_figures(m,r)
    write_reports(m,r,v)
    print('PAPER_EXPORTS 2 reports, 1 tables document, 8 figure formats')


if __name__=='__main__':main()
