#!/usr/bin/env python3
"""Build submission-gap audit and model-safe experiment tables from real data."""

import collections
import datetime as dt
import json
import math
import random
import statistics

from analyze import RESULTS, exact_sign_flip, read_json, save_json


def grouped_delta(rows, left, right):
    vals=collections.defaultdict(list)
    for row in rows:
        vals[row['event']].append(left(row)-right(row))
    means={e:statistics.mean(xs) for e,xs in sorted(vals.items())}
    rng=random.Random(17)
    arr=list(means.values())
    draws=sorted(statistics.mean(rng.choices(arr,k=len(arr))) for _ in range(12000))
    return {'n_events':len(arr), 'delta':statistics.mean(arr),
            'event_bootstrap_ci_95':[draws[299],draws[11699]],
            'two_sided_exact_sign_flip_p':exact_sign_flip(arr),
            'per_event':means,
            'note':'Event-level clusters only. With two independent repositories these CIs do not support industry-level inference.'}


def main():
    base=read_json(RESULTS/'predictions.json')
    a=read_json(RESULTS/'single_researcher_patch_annotation.json')
    h=read_json(RESULTS/'hybrid_strong_baselines_cv.json')
    roi=read_json(RESULTS/'shadow_replay_and_roi_bounds.json')
    team=read_json(RESULTS/'historical_team_membership_audit.json')
    patches=read_json(RESULTS/'researcher_evidence_index.json')
    yes={(r['event'],r['pr']) for r in a['annotations']
         if r['semantic_continuity_researcher_yes_no_unknown']=='yes'}
    yrows=[r for r in base if (r['event'],r['pr']) in yes]
    all_delta=grouped_delta(base,lambda r:r['method_outcomes']['windowed_handoff']['recall'],
                           lambda r:r['method_outcomes']['current_path']['recall'])
    code_delta=grouped_delta(yrows,lambda r:r['method_outcomes']['windowed_handoff']['recall'],
                            lambda r:r['method_outcomes']['current_path']['recall'])
    cv_delta=grouped_delta(h['prequential_strict_time_replay']['rows'],lambda r:r['recall'],
                           lambda r:r['baseline_current_path'])
    results={'computed_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
             'patches_downloaded':patches['collected'],'patches_missing':len(patches['errors']),
             'researcher_labels':a['semantic_counts_single_researcher_not_blinded'],
             'strict_independent_truth_n':0,
             'team_rosters_independently_verified_n':0,
             'team_endpoint_status_codes':dict(collections.Counter(str(x['http_status'])
                  for x in team['public_team_endpoint_probes'].values())),
             'retrospective_180day_vs_path_all':all_delta,
             'posthoc_single_researcher_yes_subset_vs_path':code_delta,
             'prequential_hybrid_vs_path':cv_delta,
             'supplemental_shuffled_reviewer_contacts_not_actual_invites':roi['additional_contacts_if_supplementing_current_path'],
             'contacts_naturally_reviewing_not_causal_new_reviews':roi['supplemental_new_contacts_who_actually_reviewed'],
             'real_realized_industrial_roi_measured':False,
             'original_confirmatory_expert_coverage_plus_10pp_gate_met':False}
    save_json('FINAL_SUBMISSION_GATE_AUDIT.json',results)
    p=lambda x:f'{100*x:+.1f}pp'
    ci=lambda x:f"[{100*x['event_bootstrap_ci_95'][0]:+.1f}, {100*x['event_bootstrap_ci_95'][1]:+.1f}]pp"
    status=team['public_team_endpoint_probes']
    lines=['# N08 — Follow-up experimental evidence and submission readiness', '',
      '**Audit status: COMPLETED ALL FEASIBLE PUBLIC-DATA CHECKS; FOUR ORIGINAL ACCEPTANCE CRITERIA NOT MET.**',
      '',
      'This report does not assert two independent human experts, employee team rosters, causal savings, or a confirmed ≥10pp gain.',
      '',
      '## Additional experiments (previous pilot preserved)', '',
      '| Evidence or experiment | Executed result | Scientific status |',
      '|---|---:|---|',
      f"| Source PR patch snapshots | {patches['collected']} / 114 | 21 hit GitHub HTTP 429; no evasion/retry |",
      f"| Single researcher semantic judgment | {a['semantic_counts_single_researcher_not_blinded'].get('yes',0)} yes / {a['semantic_counts_single_researcher_not_blinded'].get('no',0)} no / {a['semantic_counts_single_researcher_not_blinded'].get('unknown',0)} unknown | Not blind; not expert oracle |",
      f"| Historical CODEOWNERS team API audit | {len(status)} teams; statuses {results['team_endpoint_status_codes']} | Old-path reviewers verified only as participants |",
      '| Public review-request replay | 114 PR; 9 events | Observed, non-causal |',
      f"| Equal-K contact switch | {roi['additional_contacts_if_supplementing_current_path']} unique PR×person introductions in {roi['switch_prs']} PR | Inferred; no real deployment |",
      f"| New-candidate naturally reviewed | {roi['supplemental_new_contacts_who_actually_reviewed']} PR×person | Already observed, not created by method |",
      '| Forward-time online hybrid CV | 80 candidate configurations, 114 PR | Exploratory; no external dataset |',
      '', '## Main method comparisons (all are OBSERVED reviewer recall, not independent expert coverage)', '',
      '| Contrast | Event-macro difference | Event bootstrap 95% CI | Exact sign-flip p |',
      '|---|---:|---|---:|',
      f"| Original 180d handoff vs current | {p(all_delta['delta'])} | {ci(all_delta)} | {all_delta['two_sided_exact_sign_flip_p']:.3f} |",
      f"| Handoff on 46 one-researcher 'yes' PRs vs current | {p(code_delta['delta'])} | {ci(code_delta)} | {code_delta['two_sided_exact_sign_flip_p']:.3f} |",
      f"| Forward-time hybrid vs current | {p(cv_delta['delta'])} | {ci(cv_delta)} | {cv_delta['two_sided_exact_sign_flip_p']:.3f} |",
      '',
      f"- Forward-time hybrid observed Recall@2: **{100*h['prequential_strict_time_replay']['event_macro_recall']:.1f}%** (current-path about 30.1%).",
      f"- Event-held-out hybrid observed Recall@2: **{100*h['leave_one_event_out_retrospective']['event_macro_recall']:.1f}%**. The LOEO result is worse than current-path, even before stronger independent tests.",
      f"- Original preregistered target: **≥10 percentage points over strongest equal-budget baseline, on independently judged expert truth**. Not met. Current +3.2pp, single-researcher yes subset +4.8pp, online hybrid +4.9pp. None establishes +10pp true expert coverage.",
      '', '## Historical membership and coverage are not identifiable', '',
      'Original CODEOWNERS team handles and timestamped code reviews are separately verified. Across 10 team endpoints, no public team roster was returned. The pre-migration individual reviewers in `historical_team_membership_audit.json` are **candidate historical subject-matter contributors**, NOT proven members of the historical team. Public PR timeline entries that say “a team” cannot reconstruct membership at the old merge date.',
      '', '## Observational shadow replay versus actual industrial ROI', '',
      f"- {roi['n_pr_event_pairs']} post-transfer PR-event pairs, K=2 fixed. Candidate switch in {roi['switch_prs']} PRs with {roi['additional_contacts_if_supplementing_current_path']} new suggested contact slots, of whom {roi['supplemental_new_contacts_who_actually_reviewed']} naturally took formal review actions.",
      '- Equal-budget **replacement** costs no *additional* slots, but whether it displaces the right experts is not established.',
      '- For an alternative **supplemental** policy, 62 extra reviewer invitations × hypothetical 15 minutes of human attention = **15.5 hours**, assuming all require that work. Avoiding one 8-hour incident would be insufficient to break even; the scenario needs about **1.94 such incidents** averted across 114 PRs. No avoided incidents were observed or inferred.',
      '- Median observed time until review by somebody on the K=2 suggestion list differs across methods, but those times are conditioned on **who actually participated**. They do not estimate intervention effects.',
      '', '## Four research-to-submission gaps', '',
      '1. **Independent expert oracle:** one assistant-reviewed patch-label sheet is delivered, with raw source links and provenance, but not a second independent human evaluator or named true experts. All strict membership-specific expert labels remain `unknown`.',
      '2. **Historical team membership:** public team member endpoints returned no roster. Authenticated historical organization/audit exports or maintainer confirmation are needed; a current roster alone would still not prove historical membership.',
      '3. **Real industrial benefit:** the full replay and break-even grid are executed; no prospective routing change was deployed, so causal savings, bug prevention, and true reviewer-workload changes remain unmeasured.',
      '4. **Performance gate:** all credible exploratory comparisons remain below +10pp against strongest equivalent-budget baselines; therefore the original positive-effect submission hypothesis fails the declared gate.',
      '', '## Recommended scientific disposition', '',
      'Do not describe this as a complete positive-result FSE 2027 Industry Track submission. Either (a) secure a real maintainer partnership for historical roster/independent adjudication and a preregistered prospective evaluation, or (b) reframe as an observational negative finding/measurement study with adjusted claims and acquire more independent repositories. Do not relabel simulated researcher judgments or cost scenarios as real expert verification or ROI.',
      '', '## Reproducibility', '',
      '`python src/verify.py` and `python src/verify_followup.py` check prior data and new outputs. Scripts: `augment_evidence.py`, `audit_membership.py`, `shadow_roi.py`, `experiment_cv.py`, `researcher_annotations.py`, `finalize_followup.py`. Exact source links and per-record reasoning live in the JSON/CSV; all new metrics are reproducible without a GPU.',
      '', '## Documentation sources', '',
      '- [GitHub — CODEOWNERS rules](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)',
      '- [GitHub — REST team members](https://docs.github.com/en/rest/teams/members)',
      '- [GitHub — team review assignment settings](https://docs.github.com/en/organizations/organizing-members-into-teams/managing-code-review-settings-for-your-team)', '']
    (RESULTS/'FOLLOWUP_EXPERIMENT_REPORT_CN.md').write_text('\n'.join(lines),encoding='utf-8')
    print('FINAL',f"main {p(all_delta['delta'])}",f"researcher_yes {p(code_delta['delta'])}",f"prequential {p(cv_delta['delta'])}")


if __name__=='__main__':main()
