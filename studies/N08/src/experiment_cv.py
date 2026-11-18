#!/usr/bin/env python3
"""Exploratory hybrid expertise ranker with *chronologically safe* feature rows.

Never reuse a PR's reviews or commit authors until the corresponding PR is
merged. Prequential tuning sees only previously finished evaluation PRs.
Evaluation target is still observed participation, NOT expert gold truth.
"""

import collections
import datetime as dt
import itertools
import json
import math
import re
import statistics

from analyze import (DATA, RESULTS, is_bot_author, make_history, parse_time, pr_data,
                     read_json, reviewer_counts, save_json, exact_sign_flip)

ALPHAS = (0., .25, .5, 1., 2.)
BETAS = (0., .25, .5, 1.)
GAMMAS = (0., .25, .5, 1.)
GRID = list(itertools.product(ALPHAS, BETAS, GAMMAS))
DEFAULT = (1., 0., 0.)


def request_counts(prs, opened):
    out = collections.Counter()
    for pr in prs:
        if not pr or not pr.get('merged_at') or parse_time(pr['merged_at']) >= opened:
            continue
        path = DATA / 'request_timelines' / f"{pr['repo'].replace('/', '__')}__{pr['pr']}.json"
        if not path.exists():
            continue
        for ev in read_json(path).get('request_events', []):
            if parse_time(ev.get('datetime')) and parse_time(ev['datetime']) < opened:
                out.update(x.lower() for x in ev['requested_people'] if not is_bot_author(x))
    return out


def commit_author_counts(event, role, opened):
    query = DATA / 'commit_queries' / f"{event['id']}_{role}.json"
    if not query.exists():
        return collections.Counter()
    counts = collections.Counter()
    migration = parse_time(event['merged_at'])
    for c in read_json(query).get('body', []):
        author = ((c.get('author') or {}).get('login') or '').lower()
        if not author or is_bot_author(author):
            continue
        at = parse_time(c.get('commit', {}).get('committer', {}).get('date'))
        if not at or at >= opened:
            continue
        if role == 'before':
            # Only commits known to be part of repository state before transfer.
            if at >= migration:
                continue
        else:
            # GitHub commit author dates alone do not establish merge visibility.
            # Only borrow commits from a PR with independently verified earlier merge.
            title = c.get('commit', {}).get('message', '').splitlines()[0]
            ids = re.findall(r'\(#(\d+)\)', title)
            if not ids:
                continue
            pr = pr_data(event['repo'], int(ids[-1]))
            if not pr or not pr.get('merged_at') or parse_time(pr['merged_at']) >= opened:
                continue
        counts[author] += 1
    return counts


def scores_for(feature, params):
    alpha, beta, gamma = params
    decay = feature['decay']
    score = collections.defaultdict(float)
    for u, count in feature['target_review'].items(): score[u] += count
    for u, count in feature['source_review'].items(): score[u] += alpha * decay * count
    for u, count in feature['target_requests'].items(): score[u] += beta * count
    for u, count in feature['source_requests'].items(): score[u] += beta * decay * count
    for u, count in feature['target_commits'].items(): score[u] += gamma * count
    for u, count in feature['source_commits'].items(): score[u] += gamma * decay * count
    # Candidate availability cannot be a circular label; include only earlier history.
    for u in feature['global_pop']: score.setdefault(u, 0.)
    score.pop(feature['pr_author'].lower(), None)
    return [user for user, _ in sorted(score.items(), key=lambda x: (
        -x[1], -feature['global_pop'].get(x[0], 0), x[0]))[:2]]


def outcome(feature, params):
    predicted = set(scores_for(feature, params))
    return len(predicted & feature['observed']) / len(feature['observed'])


def aggregate(features, params):
    d = collections.defaultdict(list)
    for f in features:
        d[f['event']].append(outcome(f, params))
    return statistics.mean(statistics.mean(xs) for xs in d.values()) if d else 0.


def best_param(train):
    if not train:
        return DEFAULT
    scores = [(aggregate(train, params), params) for params in GRID]
    return sorted(scores, key=lambda x: (-x[0], x[1] != DEFAULT, x[1]))[0][1]


def main():
    events = [read_json(x) for x in sorted((DATA / 'events').glob('*.json'))]
    groups, pooled, _ = make_history(events, 12, 20)
    by_event = {e['id']: (e, before, after) for e, before, after in groups}
    rows = read_json(RESULTS / 'predictions.json')
    features = []
    for row in rows:
        event, before, after = by_event[row['event']]
        opened = parse_time(row['opened_at'])
        source, target = reviewer_counts(before, opened), reviewer_counts(after, opened)
        assert dict(source) == row['pre_source_reviewer_pool'], (row['event'],row['pr'],'source mismatch')
        assert dict(target) == row['previous_target_reviewer_pool'], (row['event'],row['pr'],'target mismatch')
        features.append({'event':row['event'], 'repo':row['repo'], 'pr':row['pr'],
                         'opened':opened, 'merged':parse_time(pr_data(row['repo'],row['pr'])['merged_at']),
                         'pr_author':row['pr_author'], 'observed':set(row['actual_reviewers']),
                         'baseline_current_path':row['method_outcomes']['current_path']['recall'],
                         'baseline_handoff':row['method_outcomes']['windowed_handoff']['recall'],
                         'baseline_recency':row['method_outcomes']['recency_follow']['recall'],
                         'decay':max(0.,1.-row['days_after_handoff']/180.),
                         'source_review':source, 'target_review':target,
                         'source_requests':request_counts(before,opened),
                         'target_requests':request_counts(after,opened),
                         'source_commits':commit_author_counts(event,'before',opened),
                         'target_commits':commit_author_counts(event,'after',opened),
                         'global_pop':reviewer_counts(pooled,opened)})
    # Replicate the original current-path baseline to catch score/feature drift.
    for f, row in zip(features, rows):
        pred = scores_for(f,(0,0,0))
        if pred != row['suggestions']['current_path']:
            raise AssertionError(f"Failed to reproduce path-only ranking: {f['event']} #{f['pr']}: {pred} vs {row['suggestions']['current_path']}")
    # Each held-out event is excluded from hyperparameter tuning (9 folds).
    leave_event_out = []
    for e in sorted({f['event'] for f in features}):
        test = [f for f in features if f['event']==e]
        train_keys = {(f['repo'],f['pr']) for f in test}
        train = [f for f in features if f['event']!=e and (f['repo'],f['pr']) not in train_keys]
        chosen = best_param(train)
        leave_event_out.append({'event':e,'train_pr_events':len(train),'tested_prs':len(test),
                                'params_alpha_beta_gamma':list(chosen),
                                'test_recall':average(outcome(f,chosen) for f in test),
                                'current_path':average(f['baseline_current_path'] for f in test),
                                'handoff_180d':average(f['baseline_handoff'] for f in test),
                                'recency_follow':average(f['baseline_recency'] for f in test)})
    # Stronger prospective replay: only outcomes of PRs MERGED before current PR OPENED
    # are allowed for tuning. Ordered training may include earlier PRs from same event.
    prequential = []
    for f in sorted(features,key=lambda f:(f['opened'],f['event'],f['pr'])):
        train = [x for x in features if x['merged'] < f['opened'] and (x['repo'],x['pr'])!=(f['repo'],f['pr'])]
        distinct_events = len({x['event'] for x in train})
        chosen = best_param(train) if len(train)>=10 and distinct_events>=2 else DEFAULT
        predicted = scores_for(f,chosen)
        prequential.append({'event':f['event'],'repo':f['repo'],'pr':f['pr'],
                            'training_pr_events_before_open':len(train),'training_events':distinct_events,
                            'params_alpha_beta_gamma':list(chosen),
                            'predicted':predicted,'recall':outcome(f,chosen),
                            'observed_reviewers':sorted(f['observed']),
                            'baseline_current_path':f['baseline_current_path'],
                            'baseline_handoff':f['baseline_handoff'],
                            'baseline_recency':f['baseline_recency']})
    grouped = collections.defaultdict(list)
    for row in prequential: grouped[row['event']].append(row)
    comparisons = {}
    for name in ('baseline_current_path','baseline_handoff','baseline_recency'):
        diffs = [average(r['recall']-r[name] for r in prs) for prs in grouped.values()]
        comparisons[name] = {'event_macro_delta':average(diffs),'two_sided_exact_event_sign_flip_p':exact_sign_flip(diffs),
                             'events_better':sum(x>1e-12 for x in diffs), 'events_worse':sum(x<-1e-12 for x in diffs)}
    # Leave-one-project-out diagnostics are structurally insufficient: only 2 projects.
    repo_out = []
    for repo in sorted({f['repo'] for f in features}):
        train=[f for f in features if f['repo']!=repo]
        test=[f for f in features if f['repo']==repo]
        params=best_param(train)
        repo_out.append({'heldout_repository':repo,'train_event_count':len({f['event'] for f in train}),
                         'tested_prs':len(test),'chosen_params':list(params),
                         'test_event_macro_recall':aggregate(test,params)})
    result = {'n_pr_event_pairs':len(features),'n_events':len(grouped),'tuning_grid_size':len(GRID),
              'target':'observed participants, NOT independent experts',
              'selection_risk':'Retrospective grid and cross-validation on previously explored migration events; not a new confirmatory cohort',
              'prequential_strict_time_replay':{'event_macro_recall':average(average(r['recall'] for r in prs)
                                               for prs in grouped.values()),'comparisons':comparisons,'rows':prequential},
              'leave_one_event_out_retrospective':{'event_macro_recall':average(r['test_recall'] for r in leave_event_out),
                                                   'folds':leave_event_out},
              'leave_one_repo_out_underspecified':repo_out,
              'gate_met_for_confirmatory_expert_gain':False}
    save_json('hybrid_strong_baselines_cv.json',result)
    print('FEATURES',len(features),'GRID',len(GRID), 'PREQUENTIAL_RECALL',
          round(result['prequential_strict_time_replay']['event_macro_recall'],4),
          'LOEO',round(result['leave_one_event_out_retrospective']['event_macro_recall'],4))
    for key, val in comparisons.items():
        print('VS',key,'delta_pp',round(val['event_macro_delta']*100,2),'p',val['two_sided_exact_event_sign_flip_p'])


def average(xs):
    xs=list(xs)
    return statistics.mean(xs) if xs else 0.


if __name__ == '__main__':
    main()
