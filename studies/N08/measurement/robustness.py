#!/usr/bin/env python3
"""Robustness of identifiability: budgets, grace windows, filters, dedup.

Source cohort and model rankings come from prior frozen, public real PR traces.
Outputs are conditional identification regions, not statistical uncertainty.
"""

import collections
import json
import statistics
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from analyze import observe,read_json
from run_measurement import sharp_delta_bounds,mean

OUT=ROOT/'measurement'/'results'


def bound_summary(rows):
    by_event=collections.defaultdict(list)
    n_switch,n_hist,n_dual=0,0,0
    for r in rows:
        A=set(r['suggestions']['current_path']);B=set(r['suggestions']['windowed_handoff'])
        O=set(r['actual_reviewers']);H=set(r['pre_source_reviewer_pool'])|set(r['previous_target_reviewer_pool'])
        bO=sharp_delta_bounds(O,A,B,1)
        bH=sharp_delta_bounds(O|H,A,B,1)
        by_event[r['event']].append((bO,bH))
        n_switch+=int(A!=B)
        n_hist+=int(bool((A-B)&H and (B-A)&H))
        n_dual+=int(bool((A-B)&O and (B-A)&O))
    def macro(i,which):
        return mean([mean([v[i][which] for v in cells if v[i] is not None])
                     for cells in by_event.values()])
    return {'n_pairs':len(rows),'n_events':len(by_event),'switched':n_switch,
            'two_world_witnesses_with_historical_reviewers':n_hist,
            'two_world_witnesses_with_actual_decision_reviewers':n_dual,
            'bounds_observed_only_one_expert':[macro(0,0),macro(0,1)],
            'bounds_observed_or_prior_module_one_expert':[macro(1,0),macro(1,1)]}


def main():
    events=[read_json(p) for p in sorted((ROOT/'data/events').glob('*.json'))]
    settings={}
    for k in (1,2,3,5):
        rows,_=observe(events,k=k,max_train=12,max_test=20)
        settings[f'budget_{k}']=bound_summary(rows)
    for grace in (30,90,180,365):
        rows,_=observe(events,k=2,max_train=12,max_test=20,grace_days=grace)
        settings[f'grace_{grace}d']=bound_summary(rows)
    base,_=observe(events,k=2,max_train=12,max_test=20)
    code,_=observe(events,k=2,max_train=12,max_test=20,code_only=True)
    focus,_=observe(events,k=2,max_train=12,max_test=20,focused_only=True)
    settings['all_path_touching']=bound_summary(base)
    settings['code_touching_mechanical']=bound_summary(code)
    settings['focused_posthoc']=bound_summary(focus)
    researcher=read_json(ROOT/'results/single_researcher_patch_annotation.json')['annotations']
    yes={(x['event'],x['pr']) for x in researcher
         if x['semantic_continuity_researcher_yes_no_unknown']=='yes'}
    settings['semantic_researcher_yes_nonblind']=bound_summary([x for x in base if (x['event'],x['pr']) in yes])
    # Select one migration pairing per unique PR. This changes the estimand
    # and is explicitly a sensitivity analysis, NOT the main sample.
    event_time={event['id']:event['merged_at'] for event in events}
    for order in ('first','last'):
        pick={}
        for r in sorted(base,key=lambda x:(x['repo'],x['pr'],event_time[x['event']],x['event']),
                        reverse=(order=='last')):
            pick.setdefault((r['repo'],r['pr']),r)
        settings[f'unique_pr_{order}_event_sensitivity']=bound_summary(list(pick.values()))
    for repo in sorted({r['repo'] for r in base}):
        settings[f'repository_{repo}']=bound_summary([r for r in base if r['repo']==repo])
    for label,filter_rule in (
        ('opened_within90d',lambda x:x['days_after_handoff']<=90),
        ('opened_after90d',lambda x:x['days_after_handoff']>90)):
        settings[label]=bound_summary([r for r in base if filter_rule(r)])
    out={'method':'exact optimization over unknown one-person expert identity',
         'all_settings_are_sensitivity_not_independent_confirmation':True,
         'settings':settings}
    (OUT/'robustness.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    for key in ('budget_1','budget_2','budget_3','budget_5','code_touching_mechanical',
                'focused_posthoc','unique_pr_first_event_sensitivity','unique_pr_last_event_sensitivity'):
        row=settings[key]
        print(key,'n',row['n_pairs'],'switched',row['switched'],'O_bounds',
              [round(x,3) for x in row['bounds_observed_only_one_expert']],
              'H_bounds',[round(x,3) for x in row['bounds_observed_or_prior_module_one_expert']])


if __name__=='__main__':main()
