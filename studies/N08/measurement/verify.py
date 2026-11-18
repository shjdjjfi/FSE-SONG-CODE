#!/usr/bin/env python3
"""Offline integrity and inferential-honesty checks for the N08 measurement pivot.

No network fetch is performed. The assertions are properties of the stored
public trace cohort and intentionally do NOT assert a known human expert oracle.
"""

import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

from run_measurement import sharp_delta_bounds

ROOT = Path(__file__).resolve().parents[1]
MR = ROOT / 'measurement' / 'results'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def close(a, b):
    assert math.isclose(a, b, rel_tol=0, abs_tol=1e-12), (a, b)


def main():
    records = read(MR / 'per_pr_observability_and_witnesses.json')
    metrics = read(MR / 'measurement_metrics.json')
    robust = read(MR / 'robustness.json')['settings']
    synthetic = read(MR / 'synthetic_bounds_validation.json')
    selection = read(ROOT / 'results' / 'issue_event_sampling_audit.json')
    original = read(ROOT / 'results' / 'FINAL_SUBMISSION_GATE_AUDIT.json')

    assert len(records) == metrics['n_pr_event_pairs'] == 114
    assert len({(x['repo'], x['pr']) for x in records}) == metrics['n_unique_prs'] == 103
    assert len({x['event'] for x in records}) == metrics['n_events'] == 9
    assert len({x['repo'] for x in records}) == metrics['n_independent_repositories'] == 2
    assert all(x['url'].startswith('https://github.com/') for x in records)
    assert all(x['old_team_handles'] and x['new_team_handles'] for x in records)
    assert all(x['decision_reviewers'] for x in records)

    assert sum(x['switched'] for x in records) == metrics['world_witness_counts']['switched'] == 48
    assert sum(x['opposite_worlds_both_candidates_prior_module_reviewers'] for x in records) == 41
    assert sum(x['opposite_worlds_both_candidates_actual_decision_reviewers'] for x in records) == 5

    by_key = defaultdict(lambda: defaultdict(list))
    for row in records:
        A, B = set(row['A']), set(row['B'])
        O = set(row['decision_reviewers'])
        H = set(row['prior_old_module_reviewers']) | set(row['prior_new_module_reviewers'])
        P = set(row['named_requested_ever'])
        U = O | H | P | A | B
        assert len(A) <= 2 and len(B) <= 2
        for key, candidates, m in (
            ('all_candidate_pool', U, 1),
            ('observed_decision_reviewer_only', O, 1),
            ('all_component_review_history_or_decision', O | H, 1),
            ('observed_decision_reviewers_two_experts', O, 2),
            ('component_history_or_decision_two_experts', O | H, 2),
        ):
            expected = sharp_delta_bounds(candidates, A, B, m)
            found = row['bounds'][key]
            if expected is None:
                assert found is None
            else:
                close(found[0], expected[0]); close(found[1], expected[1])
                assert -1 <= found[0] <= found[1] <= 1
                by_key[key][row['event']].append(found)

        s = row['proxies']['decision_reviewers']
        close(s['delta'], (len(B & O) - len(A & O)) / len(O))
        # The full reviewer proxy score is the arithmetic mean of singleton
        # expert allocations and hence must be *inside* the sharp singleton set.
        lo, hi = row['bounds']['observed_decision_reviewer_only']
        assert lo - 1e-12 <= s['delta'] <= hi + 1e-12

        if row['api_issues_events_available']:
            fname = ROOT / 'data' / 'issue_events' / f"{row['repo'].replace('/', '__')}__{row['pr']}.json"
            evidence = read(fname)
            assert evidence['http_status'] == 200
            assert len(evidence['body_sha256']) == 64
            assert evidence['source_url'].startswith('https://api.github.com/repos/')
            assert evidence['request_events']
            assert row['api_team_slugs']
            assert row['api_requested_old_team'] and row['api_requested_new_team']
        assert not row['historical_team_membership_verified']
        assert not row['independent_named_expertise_verified']

    for key, summary in metrics['sharp_expert_recall_delta_identification_intervals'].items():
        evs = by_key[key]
        pairs = sum(map(len, evs.values()))
        assert pairs == summary['pr_event_pairs']
        assert len(evs) == summary['events']
        for component, suffix in ((0, 'lower'), (1, 'upper')):
            group_means = [sum(b[component] for b in vals) / len(vals) for vals in evs.values()]
            close(sum(group_means) / len(group_means), summary[suffix])

    a = metrics['sharp_expert_recall_delta_identification_intervals']['observed_decision_reviewer_only']
    b = robust['budget_2']['bounds_observed_only_one_expert']
    close(a['lower'], b[0]); close(a['upper'], b[1])
    assert synthetic['n_bruteforce_cases'] == 4500
    assert synthetic['formula_vs_enumeration_disagreements'] == 0
    assert selection['selected_pr_event_pairs'] == 36
    assert sum(x['data_available'] for x in selection['pairs']) == 2
    assert selection['incomplete_due_to_rate_or_other_error']
    assert any('HTTP 403' in str(x) for x in selection['errors'].values())
    assert metrics['observable_stage_counts']['verified_historic_person_to_team_roster'] == 0
    assert metrics['observable_stage_counts']['independently_adjudicated_person_to_pr_expertise'] == 0
    assert original['strict_independent_truth_n'] == 0
    assert original['real_realized_industrial_roi_measured'] is False

    for prefix in ('fig_m1_observability_stages', 'fig_m2_sharp_identification_intervals',
                   'fig_m3_proxy_choice_sensitivity', 'fig_m4_budget_identification_bounds'):
        for ext in ('.png', '.svg'):
            p = MR / 'figures' / (prefix + ext)
            assert p.is_file() and p.stat().st_size > 2000, str(p)
    for doc in ('EXPERIMENT_REPORT_CN.md', 'PAPER_EXPERIMENTS_EN.md',
                'TABLES_FOR_PAPER.md'):
        assert (MR / doc).stat().st_size > 2000
    paper = (MR / 'PAPER_EXPERIMENTS_EN.md').read_text(encoding='utf-8')
    assert 'Eᵢ={u}' in paper and 'Eᵢ={{u}}' not in paper
    assert '**not** representative prevalence' in paper

    source_digests = {}
    for path in sorted((ROOT / 'data' / 'issue_events').glob('*.json')):
        source_digests[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = {'design': 'frozen public repository measurement; no expertise oracle',
                'n_pr_event_pairs': len(records),
                'n_unique_prs': len({(x['repo'], x['pr']) for x in records}),
                'n_event_clusters': len({x['event'] for x in records}),
                'historical_team_memberships_independently_observed': 0,
                'human_expertise_independently_adjudicated': 0,
                'api_team_identity_samples': len(source_digests),
                'issue_events_normalized_sha256': source_digests,
                'synthetic_bound_tests': synthetic['n_bruteforce_cases'],
                'synthetic_bound_test_errors': synthetic['formula_vs_enumeration_disagreements'],
                'industrial_causal_savings_measured': False,
                'verified': True}
    (MR / 'VERIFICATION_AUDIT.json').write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print('MEASUREMENT_VERIFY_OK', json.dumps(manifest, sort_keys=True))


if __name__ == '__main__':
    main()
