#!/usr/bin/env python3
"""Fail-closed audit of saved experiment claims and recommendation eligibility."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads((ROOT / path).read_text())


def main():
    events = [json.loads(p.read_text()) for p in (ROOT / 'data' / 'events').glob('*.json')]
    assert events and len(set(e['id'] for e in events)) == len(events)
    for e in events:
        assert e['valid'] and e['rename_pairs'] and e['merged_at'] and e['merge_sha']
        assert set(e['old_owner']) - set(e['new_owner']), e['id']
        for name in ('migration_patch_sha256', 'before_codeowners_sha256', 'after_codeowners_sha256'):
            assert re.fullmatch(r'[0-9a-f]{64}', e[name]), (e['id'], name)
    rows = read('results/predictions.json')
    metrics = read('results/metrics.json')
    assert len(rows) == metrics['evaluated_prs'] > 0
    assert len(set(r['event'] for r in rows)) == metrics['nonempty_events']
    assert metrics['seeds'] == [17, 29, 43]
    methods = set(metrics['strategies'])
    for r in rows:
        assert r['pr_author'] and not r['pr_author'].endswith('[bot]')
        assert r['days_after_handoff'] >= 0 and r['actual_reviewers']
        assert set(r['suggestions']) == methods
        for m, suggestion in r['suggestions'].items():
            assert len(suggestion) == metrics['k'] and len(set(suggestion)) == metrics['k'], (r['pr'], m)
            assert r['pr_author'] not in suggestion, (r['pr'], m, r['pr_author'])
            assert r['method_outcomes'][m]['suggestions'] == metrics['k']
    controls = read('results/negative_controls.json')
    rest = read('results/rest_review_validation.json')
    diff = read('results/diff_audit_summary.json')
    req = read('results/request_audit.json')
    assert controls['false_positives'] == 0 and controls['real_merged_controls'] == len(controls['observations'])
    assert rest['matched'] == rest['sample_size'] and rest['sample_size'] >= 1
    assert diff['audited'] == len(rows) == req['audited']
    assert not req['errors'] and not diff['errors'] and req['missing_pr_authors'] == 0
    assert diff['with_focused_code_changes'] <= diff['with_code_changes'] <= len(rows)
    for figure in ('fig1_reviewer_coverage', 'fig2_budget_sensitivity', 'fig3_event_heterogeneity'):
        assert (ROOT / 'results' / 'figures' / f'{figure}.png').exists()
        assert (ROOT / 'results' / 'figures' / f'{figure}.svg').exists()
    print('VERIFY PASS:', len(events), 'verified migrations,', len(rows), 'author-safe equal-budget predictions,',
          controls['real_merged_controls'], 'negative controls,', rest['sample_size'], 'REST checks')


if __name__ == '__main__':
    main()
