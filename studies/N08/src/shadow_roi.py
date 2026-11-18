#!/usr/bin/env python3
"""Shadow replay: *observable* review contacts, not real-world causal ROI.

The team membership of anonymized GitHub review requests is unknown; these
measurements are therefore neither actual CODEOWNERS invitation recall nor
real reductions in review duration, security incidents, or company expense.
"""

import collections
import datetime as dt
import math
import statistics

from analyze import DATA, RESULTS, parse_time, pr_data, read_json, reviewed_users, save_json

METHODS = ('current_path', 'windowed_handoff', 'git_follow', 'recency_follow')


def average(xs):
    return statistics.mean(xs) if xs else None


def main():
    rows = read_json(RESULTS / 'predictions.json')
    replay = []
    for row in rows:
        path = DATA / 'request_timelines' / f"{row['repo'].replace('/', '__')}__{row['pr']}.json"
        req = read_json(path)
        opened = parse_time(row['opened_at'])
        early = set()
        all_named = set()
        for event in req['request_events']:
            at = parse_time(event['datetime'])
            all_named.update(event['requested_people'])
            if opened <= at <= opened + dt.timedelta(hours=72):
                early.update(event['requested_people'])
        full = pr_data(row['repo'], row['pr'])
        review_times = collections.defaultdict(list)
        for item in full['reviews']:
            if item['state'] not in ('APPROVED', 'CHANGES_REQUESTED'):
                continue
            at = parse_time(item['submitted_at'])
            if opened <= at <= parse_time(full['merged_at']):
                review_times[item['login'].lower()].append(round((at - opened).total_seconds()/3600, 3))
        results = {}
        for method in METHODS:
            recs = set(row['suggestions'][method])
            active = recs & set(review_times)
            results[method] = {'selected': sorted(recs), 'named_request_overlap_within_72h': len(recs & early),
                               'selected_not_in_named_first_72h': len(recs - early),
                               'selected_ultimately_decision_reviewed': len(active),
                               'first_observed_selected_reviewer_review_hours': min(
                                   (x for u in active for x in review_times[u]), default=None)}
        fresh = set(row['suggestions']['windowed_handoff']) - set(row['suggestions']['current_path'])
        replay.append({'event': row['event'], 'pr': row['pr'], 'repo': row['repo'],
                       'pr_url': row['url'], 'first_72h_named_requests': len(early),
                       'any_anonymized_team_request': any(e['team_request_anonymized'] for e in req['request_events']),
                       'actual_reviewers': sorted(review_times),
                       'handoff_new_contacts_vs_current_path': sorted(fresh),
                       'handoff_new_contacts_actually_reviewed': sorted(fresh & set(review_times)),
                       'strategies': results})
    totals = {}
    grouped = collections.defaultdict(list)
    for r in replay:
        grouped[r['event']].append(r)
    for method in METHODS:
        event_hit = [average([int(x['strategies'][method]['selected_ultimately_decision_reviewed']>0) for x in prs])
                     for prs in grouped.values()]
        times = [r['strategies'][method]['first_observed_selected_reviewer_review_hours'] for r in replay]
        totals[method] = {'event_macro_hit_at_two_on_observed_decision_reviewers': average(event_hit),
                          'reviewer_recommendations': 2*len(replay),
                          'selected_not_in_public_named_first_72h_total': sum(
                              r['strategies'][method]['selected_not_in_named_first_72h'] for r in replay),
                          'observed_selected_reviewer_review_time_median_hours_conditional_on_review':
                          statistics.median([x for x in times if x is not None]) if any(x is not None for x in times) else None,
                          'prs_with_selected_reviewer_reviewed': sum(x is not None for x in times)}
    switched = [r for r in replay if r['handoff_new_contacts_vs_current_path']]
    additional_contacts = sum(len(r['handoff_new_contacts_vs_current_path']) for r in replay)
    incident_cost_hours = [2, 8, 24]
    cognitive_cost_minutes = [5, 15, 30]
    # Defects prevented are unknown: these are cost-effectiveness thresholds,
    # not estimates of prevented bugs or realized savings.
    breakeven = [{ 'reviewer_minutes_per_contact': m, 'avoided_incident_hours': h,
                   'model_new_contact_hours_if_supplemental': additional_contacts*m/60,
                   'minimum_avoided_incidents_needed_in_sample': additional_contacts*m/(h*60),
                   'minimum_avoided_incidents_per_100_prs': 100*additional_contacts*m/(h*60*len(replay))}
                 for m in cognitive_cost_minutes for h in incident_cost_hours]
    save_json('shadow_replay_and_roi_bounds.json', {
        'n_pr_event_pairs':len(replay), 'n_independent_migration_events':len(grouped),
        'interpretation':'OBSERVATIONAL SHADOW REPLAY ONLY. Counterfactual response and causal industrial ROI are unidentifiable.',
        'team_membership_unknown':True,
        'original_git_hub_request_events_are_publicly_visible_subset':True,
        'strategy_summary':totals, 'switch_prs':len(switched),
        'additional_contacts_if_supplementing_current_path':additional_contacts,
        'supplemental_contact_percent_of_prs':round(100*additional_contacts/len(replay),3),
        'supplemental_new_contacts_who_actually_reviewed':sum(len(x['handoff_new_contacts_actually_reviewed']) for x in replay),
        'hypothetical_cost_break_even_sensitivity_NOT_MEASURED_ROI':breakeven,
        'claim_limits':['No randomized or on-platform deployment','No actual saved review hours or bugs observed',
                        'CODEOWNERS anonymized team requests may already reach suggested users',
                        'Public named review requests are not comprehensive invitations',
                        'Reviewer response times are conditional on self-selected natural participation'],
        'per_pr':replay})
    print('REPLAY',len(replay),'NEW_CONTACTS',additional_contacts,'SWITCH_PRS',len(switched),
          'NEW_CONTACTS_ACTUALLY_REVIEWED', sum(len(x['handoff_new_contacts_actually_reviewed']) for x in replay))


if __name__ == '__main__':
    main()
