#!/usr/bin/env python3
"""N08: evidence observability, sharp partial ID and proxy-choice sensitivity.

No reviewer selection is treated as validated expertise. Explicitly distinguish
public team request *handles* from historic team *human members*.
"""

import collections
import datetime as dt
import itertools
import json
import math
import random
import statistics
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
RESULTS=ROOT/'results'
OUT=ROOT/'measurement'/'results'
OUT.mkdir(parents=True,exist_ok=True)
METHOD_A='current_path'
METHOD_B='windowed_handoff'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(name,obj):
    p=OUT/name
    p.write_text(json.dumps(obj,indent=2,sort_keys=True,ensure_ascii=False)+'\n',encoding='utf-8')


def parse_time(s):
    return dt.datetime.fromisoformat(s.replace('Z','+00:00')) if s else None


def mean(rows):
    return statistics.mean(rows) if rows else None


def exact_sign_flip(vals):
    nonzero=[x for x in vals if abs(x)>1e-12]
    if not nonzero:return 1.
    obs=abs(sum(nonzero))
    return sum(abs(sum(sign*v for sign,v in zip(signs,nonzero)))>=obs-1e-12
               for signs in itertools.product((-1,1),repeat=len(nonzero)))/2**len(nonzero)


def event_macro(records,key):
    groups=collections.defaultdict(list)
    for r in records:
        v=r.get(key)
        if v is not None:groups[r['event']].append(v)
    return mean([mean(v) for v in groups.values()])


def sharp_delta_bounds(U,A,B,m=1):
    """Exact min/max normalized expert coverage gain over all |E|=m subsets U.

    For a selected expert x, contribution is 1(x in B)-1(x in A).
    Additivity makes m-lowest/m-highest feasible; not a probabilistic CI.
    """
    U=set(U)
    if not U or m<1 or len(U)<m:return None
    weights=sorted(int(x in B)-int(x in A) for x in U)
    return [sum(weights[:m])/m,sum(weights[-m:])/m]


def sharp_coverage_bounds(U,recommended,m=1):
    U=set(U)
    if not U or m<1 or len(U)<m:return None
    hit=len(U&set(recommended))
    return [max(0,m-(len(U)-hit))/m,min(m,hit)/m]


def proxy_score(row,allowed):
    if not allowed:return None
    A=set(row['A']);B=set(row['B'])
    return {'current_path':len(A&allowed)/len(allowed),
            'handoff_180d':len(B&allowed)/len(allowed),
            'delta':(len(B&allowed)-len(A&allowed))/len(allowed)}


def event_deltas(recs,key):
    d=collections.defaultdict(list)
    for x in recs:
        y=x['proxies'].get(key)
        if y is not None:d[x['event']].append(y['delta'])
    return {ev:mean(v) for ev,v in sorted(d.items())}


def macro_bounds(records,key):
    return {'lower':event_macro(records,key+'_lower'),'upper':event_macro(records,key+'_upper'),
            'pr_event_pairs':sum(x.get(key+'_lower') is not None for x in records),
            'events':len({x['event'] for x in records if x.get(key+'_lower') is not None})}


def infer_prob_proxy(rows,field):
    groups=collections.defaultdict(list)
    for row in rows:
        if row[field] is not None:groups[row['event']].append(row[field])
    v=[mean(x) for x in groups.values()]
    return {'mean_event_macro':mean(v), 'num_events':len(v),
            'num_pr_event_pairs':sum(len(x) for x in groups.values())}


def make_record(row,events,researcher):
    repo,pr,ev=row['repo'],row['pr'],row['event']
    author=row['pr_author'].lower()
    A=set(row['suggestions'][METHOD_A]);B=set(row['suggestions'][METHOD_B])
    O=set(row['actual_reviewers'])-{author}
    old=set(row['pre_source_reviewer_pool'])-{author}
    target=set(row['previous_target_reviewer_pool'])-{author}
    H=old|target
    req_file=DATA/'request_timelines'/f"{repo.replace('/','__')}__{pr}.json"
    requests=load(req_file)['request_events']
    pr_file=DATA/'pr_timelines'/f"{repo.replace('/','__')}__{pr}.json"
    timeline=load(pr_file)
    opened=parse_time(row['opened_at']);merged=parse_time(timeline['merged_at'])
    named_windows={24:set(),72:set(),168:set()}
    named_all=set();html_opaque=False;html_opaque_72=False
    for req in requests:
        at=parse_time(req.get('datetime'))
        if not at or at>merged:continue
        people={x.lower() for x in req['requested_people']}-{author}
        named_all|=people
        html_opaque|=bool(req['team_request_anonymized'])
        for hour in named_windows:
            if opened<=at<=opened+dt.timedelta(hours=hour):named_windows[hour]|=people
        if opened<=at<=opened+dt.timedelta(hours=72):html_opaque_72|=bool(req['team_request_anonymized'])
    any_review=set()
    for x in timeline['reviews']:
        at=parse_time(x.get('submitted_at'))
        if x['login'].lower()!=author and x['state'] in ('APPROVED','CHANGES_REQUESTED','COMMENTED') and at and opened<=at<=merged:
            any_review.add(x['login'].lower())
    api_file=DATA/'issue_events'/f"{repo.replace('/','__')}__{pr}.json"
    api=load(api_file) if api_file.exists() else None
    api_teams=set();api_people=set();api_team_72=set();api_people_72=set()
    if api:
        for x in api['request_events']:
            if x['event']!='review_requested':continue
            at=parse_time(x.get('at'))
            if not at or at>merged:continue
            team=(x.get('team_slug') or '').lower()
            person=(x.get('reviewer') or '').lower()
            if team:api_teams.add(team)
            if person and person!=author:api_people.add(person)
            if opened<=at<=opened+dt.timedelta(hours=72):
                if team:api_team_72.add(team)
                if person and person!=author:api_people_72.add(person)
    old_teams={x.split('/')[-1].lower() for x in events[ev]['old_owner']}
    new_teams={x.split('/')[-1].lower() for x in events[ev]['new_owner']}
    # Full public evidence envelope: formal reviewer, prior component reviewer,
    # named request, or candidate from a timestamp-safe repository reviewer pool.
    U=O|H|named_all|A|B
    worlds={'all_candidate_pool':sharp_delta_bounds(U,A,B,1),
            'observed_decision_reviewer_only':sharp_delta_bounds(O,A,B,1),
            'all_component_review_history_or_decision':sharp_delta_bounds(O|H,A,B,1),
            'observed_decision_reviewers_two_experts':sharp_delta_bounds(O,A,B,2),
            'component_history_or_decision_two_experts':sharp_delta_bounds(O|H,A,B,2)}
    formal_rev=proxy_score({'A':A,'B':B},O)
    proxies={
        'decision_reviewers':formal_rev,
        'any_formal_review_state':proxy_score({'A':A,'B':B},any_review),
        'named_request_24h':proxy_score({'A':A,'B':B},named_windows[24]),
        'named_request_72h':proxy_score({'A':A,'B':B},named_windows[72]),
        'named_request_168h':proxy_score({'A':A,'B':B},named_windows[168]),
        'named_request_ever':proxy_score({'A':A,'B':B},named_all),
        'pre_source_reviewers':proxy_score({'A':A,'B':B},old),
        'prior_target_reviewers':proxy_score({'A':A,'B':B},target),
    }
    assert abs(formal_rev['current_path']-row['method_outcomes'][METHOD_A]['recall'])<1e-9
    assert abs(formal_rev['handoff_180d']-row['method_outcomes'][METHOD_B]['recall'])<1e-9
    return {
        'event':ev,'repo':repo,'pr':pr,'url':row['url'],'opened_at':row['opened_at'],
        'old_team_handles':events[ev]['old_owner'],'new_team_handles':events[ev]['new_owner'],
        'historical_team_membership_verified':False,'independent_named_expertise_verified':False,
        'semantic_researcher_nonblind':researcher[(ev,pr)],
        'A':sorted(A),'B':sorted(B),'decision_reviewers':sorted(O),'prior_old_module_reviewers':sorted(old),
        'prior_new_module_reviewers':sorted(target),'named_requested_72h':sorted(named_windows[72]),
        'named_requested_ever':sorted(named_all),'html_anonymized_team_event':html_opaque,
        'html_anonymized_team_event_72h':html_opaque_72,
        'api_issues_events_available':api is not None,'api_issues_events_page_truncated':bool(api and api.get('pagination_link')),
        'api_team_slugs':sorted(api_teams),'api_team_slugs_72h':sorted(api_team_72),
        'api_individual_requests':sorted(api_people), 'api_individual_requests_72h':sorted(api_people_72),
        'api_requested_old_team':bool(old_teams&api_teams),
        'api_requested_new_team':bool(new_teams&api_teams),
        'observed_review_count':len(O),'historical_module_reviewer_count':len(H),
        'same_pr_reappears_in_another_event':False,
        'proxies':proxies,
        'bounds':worlds,
        'switched':A!=B,
        'opposite_worlds_exist_if_any_suggestion_may_be_expert':bool(A-B and B-A),
        'opposite_worlds_both_candidates_prior_module_reviewers':bool((A-B)&H and (B-A)&H),
        'opposite_worlds_both_candidates_actual_decision_reviewers':bool((A-B)&O and (B-A)&O),
        'world_A_candidate':sorted((A-B)&H)[0] if (A-B)&H else (sorted(A-B)[0] if A-B else None),
        'world_B_candidate':sorted((B-A)&H)[0] if (B-A)&H else (sorted(B-A)[0] if B-A else None),
    }


def summarize(data):
    n=len(data)
    prs={(x['repo'],x['pr']) for x in data}
    seen=collections.Counter((x['repo'],x['pr']) for x in data)
    for x in data:x['same_pr_reappears_in_another_event']=seen[(x['repo'],x['pr'])]>1
    grade={
        'verified_code_migration_and_team_handles':n,
        'html_team_review_request_anonymized':sum(x['html_anonymized_team_event'] for x in data),
        'public_named_request_ever':sum(bool(x['named_requested_ever']) for x in data),
        'public_named_request_first72h':sum(bool(x['named_requested_72h']) for x in data),
        'any_actual_formal_decision_reviewer':sum(bool(x['decision_reviewers']) for x in data),
        'api_team_slug_query_available':sum(x['api_issues_events_available'] for x in data),
        'api_public_team_slug_observed':sum(bool(x['api_team_slugs']) for x in data if x['api_issues_events_available']),
        'verified_historic_person_to_team_roster':0,
        'independently_adjudicated_person_to_pr_expertise':0,
    }
    bounds={}
    for key in data[0]['bounds']:
        subset=[]
        for row in data:
            b=row['bounds'][key]
            subset.append({'event':row['event'],key+'_lower':b[0] if b else None,
                           key+'_upper':b[1] if b else None})
        bounds[key]=macro_bounds(subset,key)
    world_counts={key:sum(row[key] for row in data) for key in (
        'switched','opposite_worlds_exist_if_any_suggestion_may_be_expert',
        'opposite_worlds_both_candidates_prior_module_reviewers',
        'opposite_worlds_both_candidates_actual_decision_reviewers')}
    proxy_summary={};proxy_events={}
    for name in data[0]['proxies']:
        eligible=[row for row in data if row['proxies'][name] is not None]
        e=event_deltas(eligible,name)
        proxy_events[name]=e
        proxy_summary[name]={'n_pr_event_pairs':len(eligible),'n_events':len(e),
            'event_macro_current_path':event_macro([{'event':r['event'],'x':r['proxies'][name]['current_path']} for r in eligible],'x'),
            'event_macro_handoff':event_macro([{'event':r['event'],'x':r['proxies'][name]['handoff_180d']} for r in eligible],'x'),
            'event_macro_delta':mean(list(e.values())),'sign_flip_p':exact_sign_flip(list(e.values())),
            'per_event_delta':e}
    # Within-event comparisons on the SAME PR subset avoid spurious reversal
    # caused by different missing label populations.
    reversals={}
    for name in ('named_request_24h','named_request_72h','named_request_168h','named_request_ever',
                 'any_formal_review_state','pre_source_reviewers','prior_target_reviewers'):
        e=collections.defaultdict(list)
        for row in data:
            p=row['proxies'][name]
            if p is not None:
                e[row['event']].append((row['proxies']['decision_reviewers']['delta'],p['delta']))
        flips={ev: {'n':len(values),'decision_delta':mean(x for x,_ in values),
                    'alternate_delta':mean(y for _,y in values)} for ev,values in e.items()}
        reversals[name]={'comparable_events':len(flips),
                        'opposite_sign_events':sum(x['decision_delta']*x['alternate_delta']<-1e-12 for x in flips.values()),
                        'event_details':flips}
    api=[row for row in data if row['api_issues_events_available']]
    pagecomplete=[row for row in api if not row['api_issues_events_page_truncated']]
    api_check=[]
    for row in pagecomplete:
        html_names=set(row['named_requested_ever'])
        api_names=set(row['api_individual_requests'])
        api_check.append({'event':row['event'],'pr':row['pr'],
          'web_anon_team':row['html_anonymized_team_event'],
          'api_team_slug_found':bool(row['api_team_slugs']),
          'html_named_count':len(html_names),'api_named_count':len(api_names),
          'html_extra_names':len(html_names-api_names),'api_missing_from_html':len(api_names-html_names)})
    api_summary={
        'sampled_pairs_api_available':len(api),
        'sampled_unique_prs_api_available':len({(x['repo'],x['pr']) for x in api}),
        'api_pages_with_pagination':len(api)-len(pagecomplete),
        'api_team_slug_recovered':sum(bool(x['api_team_slugs']) for x in api),
        'api_old_team_slug_requested':sum(x['api_requested_old_team'] for x in api),
        'api_new_team_slug_requested':sum(x['api_requested_new_team'] for x in api),
        'api_both_old_and_new_requested':sum(x['api_requested_old_team'] and x['api_requested_new_team'] for x in api),
        'html_opaque_but_api_team_named':sum(x['html_anonymized_team_event'] and bool(x['api_team_slugs']) for x in api),
        'api_named_requests_present':sum(bool(x['api_individual_requests']) for x in api),
        'html_vs_api_named_audit_only_non_paginated':api_check,
        'request_team_is_whole_PR_not_proof_of_changed_file_owner':True,
    }
    semantic=collections.Counter(x['semantic_researcher_nonblind'] for x in data)
    good=[x for x in data if x['semantic_researcher_nonblind']=='yes']
    semantic_bounds={}
    for key in ('observed_decision_reviewer_only','all_component_review_history_or_decision'):
        eligible=[{'event':row['event'],key+'_lower':row['bounds'][key][0],
                   key+'_upper':row['bounds'][key][1]} for row in good if row['bounds'][key]]
        semantic_bounds[key]=macro_bounds(eligible,key) if eligible else None
    overall={'design':'Observability and sharp identification bounds, not expert-recommender improvement',
       'unit':'PR-event pair; one PR can be associated with multiple migrations',
       'n_pr_event_pairs':n,'n_unique_prs':len(prs),
       'duplicated_pr_event_pairs':sum(x['same_pr_reappears_in_another_event'] for x in data),
       'n_events':len({x['event'] for x in data}),'n_independent_repositories':len({x['repo'] for x in data}),
       'observable_stage_counts':grade,'world_witness_counts':world_counts,
       'sharp_expert_recall_delta_identification_intervals':bounds,
       'proxy_definition_results':proxy_summary,
       'per_event_proxy_ranking_reversal_on_same_prs':reversals,
       'github_issue_events_api_cross_surface_audit':api_summary,
       'researcher_single_nonblind_semantic_labels':dict(semantic),
       'researcher_semantic_yes_subset_bounds':semantic_bounds,
       'interpretation_limits':[
          'A nonempty historical reviewer pool is a plausibility bound, not verified knowledge or membership.',
          'Bounds are conditional on their explicitly assumed finite candidate universe and latent expert-set size.',
          'Observed reviewer labels are selected by existing workflow and do not certify expertise.',
          'API review_requested team slugs are PR-level events: cannot assign cause to a migrated file.',
          'A team request may be expanded by private auto-assignment and does not reveal historic team people.',
          'Two repositories and event overlap prevent population-level generalization.',
          'No industrial deployment, causal work-hour savings, or individual expert oracle is claimed.'
       ]}
    return overall


def main():
    rows=load(RESULTS/'predictions.json')
    events={p.stem:load(p) for p in (DATA/'events').glob('*.json')}
    annotations=load(RESULTS/'single_researcher_patch_annotation.json')['annotations']
    researcher={(r['event'],r['pr']):r['semantic_continuity_researcher_yes_no_unknown'] for r in annotations}
    records=[make_record(r,events,researcher) for r in rows]
    report=summarize(records)
    write('per_pr_observability_and_witnesses.json',records)
    write('measurement_metrics.json',report)
    print('DATA',report['n_pr_event_pairs'],'PR-event /',report['n_unique_prs'],'unique PR;',
          report['n_events'],'migrations',report['n_independent_repositories'],'repos')
    print('PUBLIC_LEVELS',report['observable_stage_counts'])
    print('WORLD_WITNESSES',report['world_witness_counts'])
    for tier,b in report['sharp_expert_recall_delta_identification_intervals'].items():
        print('BOUND',tier,'N',b['pr_event_pairs'],'[',round(b['lower'],4),',',round(b['upper'],4),']')
    for p,v in report['proxy_definition_results'].items():
        print('PROXY',p,'N',v['n_pr_event_pairs'],'GAP',round(v['event_macro_delta'],4))
    print('API',report['github_issue_events_api_cross_surface_audit'])


if __name__=='__main__':main()
