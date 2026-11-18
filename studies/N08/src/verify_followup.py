#!/usr/bin/env python3
"""Internal consistency and anti-fabrication guard for follow-up evidence."""

import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def read(p):return json.loads((ROOT/p).read_text(encoding='utf-8'))

def main():
    rows=read('results/predictions.json')
    a=read('results/single_researcher_patch_annotation.json')
    idx=read('results/researcher_evidence_index.json')
    team=read('results/historical_team_membership_audit.json')
    cv=read('results/hybrid_strong_baselines_cv.json')
    roi=read('results/shadow_replay_and_roi_bounds.json')
    gate=read('results/FINAL_SUBMISSION_GATE_AUDIT.json')
    assert len(rows)==114==len(a['annotations'])==roi['n_pr_event_pairs']
    assert len({(r['event'],r['pr']) for r in rows})==len(rows)
    assert idx['collected']+len(idx['errors'])==len(rows)
    assert sum(a['semantic_counts_single_researcher_not_blinded'].values())==len(rows)
    assert a['independent_expert_oracle_usable_prs']==gate['strict_independent_truth_n']==0
    assert gate['team_rosters_independently_verified_n']==0
    for item in a['annotations']:
        assert item['annotator'].startswith('single model-assisted researcher')
        assert not item['strict_oracle_usable'] and item['independent_named_expert_handle'] is None
        if item['semantic_continuity_researcher_yes_no_unknown']!='unknown':
            assert item['has_patch_excerpts']
        if item['has_patch_excerpts']:
            src=ROOT/'data/semantic_evidence'/f"{item['annotation_id']}.json"
            assert src.exists()
            assert read(src.relative_to(ROOT))['sha256']==item['patch_sha256']
    for row in roi['per_pr']:
        assert len(row['strategies']['current_path']['selected'])==2
        assert len(row['strategies']['windowed_handoff']['selected'])==2
        added=set(row['strategies']['windowed_handoff']['selected'])-set(row['strategies']['current_path']['selected'])
        assert sorted(added)==row['handoff_new_contacts_vs_current_path']
    assert roi['additional_contacts_if_supplementing_current_path']==sum(len(r['handoff_new_contacts_vs_current_path']) for r in roi['per_pr'])
    assert not gate['real_realized_industrial_roi_measured']
    assert not gate['original_confirmatory_expert_coverage_plus_10pp_gate_met']
    assert len(team['events'])==9
    assert all(r['team_membership_at_handoff']=='NOT_IDENTIFIABLE_FROM_PUBLIC_DATA' for r in team['events'])
    assert len(cv['prequential_strict_time_replay']['rows'])==len(rows)
    assert cv['tuning_grid_size']==80
    assert cv['gate_met_for_confirmatory_expert_gain'] is False
    assert (ROOT/'results'/'FOLLOWUP_EXPERIMENT_REPORT_CN.md').is_file()
    for stem in ('fig4_followup_observed_reviewer_recall','fig5_hypothetical_roi_breakeven'):
        assert (ROOT/'results'/'figures'/f'{stem}.png').is_file()
        assert (ROOT/'results'/'figures'/f'{stem}.svg').is_file()
    for name in ('PROSPECTIVE_INDUSTRIAL_EVALUATION_PLAN.md','REVISED_EXPERIMENTS_SECTION_EN.md',
                 'SINGLE_RESEARCHER_ANNOTATIONS.csv'):
        assert (ROOT/'results'/name).is_file()
    print('VERIFY FOLLOWUP PASS:',len(rows),'PR event pairs;',idx['collected'],'patch sources;',
          len(team['events']),'team-mapping audits; no false independent expert or ROI claims')


if __name__=='__main__':main()
