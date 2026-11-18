#!/usr/bin/env python3
"""Recover historical review-request events from public PR timelines.

GitHub may anonymize team reviewers as 'a team'; do not infer identities.
"""

import concurrent.futures
import collections
import datetime as dt
import hashlib
import json
import re

from lxml import html
from harvest import OUT, ROOT, fetch, write_json
from analyze import parse_time


def parse_author(page):
    dom = html.fromstring(page)
    links = dom.xpath('//a[contains(concat(" ",normalize-space(@class)," ")," author ")]/@href')
    if not links:
        return None
    if re.fullmatch(r'/[A-Za-z0-9-]{1,39}', links[0]):
        return links[0].lstrip('/').lower()
    if re.fullmatch(r'/apps/[A-Za-z0-9-]{1,39}', links[0]):
        return links[0].split('/')[-1].lower() + '[bot]'
    return None


def parse_requests(page):
    dom = html.fromstring(page)
    requests = []
    for d in dom.xpath('//div[contains(concat(" ",normalize-space(@class)," ")," TimelineItem ")]'):
        txt = ' '.join(d.text_content().split())
        if not re.search(r'requested (?:a )?review from', txt, re.I):
            continue
        if 'removed' in txt.lower() or 'dismissed' in txt.lower():
            continue
        dates = d.xpath('.//relative-time/@datetime')
        if not dates:
            continue
        actor_hrefs = d.xpath('.//a[contains(@class,"TimelineItem-avatar")]/@href')
        actor = actor_hrefs[0].lstrip('/').lower() if actor_hrefs else ''
        people = []
        for a in d.xpath('.//a[@href]'):
            href = a.get('href', '')
            text = a.text_content().strip().lstrip('@')
            if re.fullmatch(r'/[A-Za-z0-9-]{1,39}', href) and text and href.lstrip('/').lower() != actor:
                people.append(href.lstrip('/').lower())
        requests.append({'datetime': dates[0], 'actor': actor,
                         'requested_people': sorted(set(people)),
                         'team_request_anonymized': bool(re.search(r'requested (?:a )?review from a team', txt, re.I))})
    return requests


def collect(repo, pr, overwrite=False):
    p = OUT / 'request_timelines' / f"{repo.replace('/', '__')}__{pr}.json"
    if p.exists() and not overwrite:
        return json.loads(p.read_text())
    url = f'https://github.com/{repo}/pull/{pr}'
    buf, _ = fetch(url)
    page = buf.decode('utf-8', 'replace')
    events = parse_requests(page)
    result = {'repo': repo, 'pr': pr, 'url': url, 'sha256': hashlib.sha256(buf).hexdigest(),
              'pr_author': parse_author(page), 'request_events': events}
    write_json(p, result)
    return result


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--overwrite', action='store_true')
    args = ap.parse_args()
    rows = json.loads((ROOT / 'results' / 'predictions.json').read_text())
    ids = {(r['repo'], r['pr']) for r in rows}
    errors = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(collect, repo, n, args.overwrite): (repo, n) for repo, n in ids}
        for fut in concurrent.futures.as_completed(futures):
            try:
                fut.result()
            except Exception as exc:
                errors[str(futures[fut])] = str(exc)
    observed_requests = 0
    team_auto, individual, legacy_request, legacy_review, no_both, legacy_request_72h = 0, 0, 0, 0, 0, 0
    records = []
    for row in rows:
        p = OUT / 'request_timelines' / f"{row['repo'].replace('/', '__')}__{row['pr']}.json"
        if not p.exists():
            continue
        data = json.loads(p.read_text())
        requested = set().union(*(e['requested_people'] for e in data['request_events'])) if data['request_events'] else set()
        auto = any(e['team_request_anonymized'] for e in data['request_events'])
        legacy = set(row['pre_source_reviewer_pool'])
        actual = set(row['actual_reviewers'])
        old_requested = bool(requested & legacy)
        cutoff_72h = parse_time(row['opened_at']) + dt.timedelta(hours=72)
        old_requested_early = any(set(ev['requested_people']) & legacy and parse_time(ev['datetime']) <= cutoff_72h
                                  for ev in data['request_events'])
        old_reviewed = bool(actual & legacy)
        team_auto += int(auto)
        individual += int(bool(requested))
        legacy_request += int(old_requested)
        legacy_request_72h += int(old_requested_early)
        legacy_review += int(old_reviewed)
        no_both += int(not old_requested and not old_reviewed)
        observed_requests += len(data['request_events'])
        records.append({'event': row['event'], 'repo': row['repo'], 'pr': row['pr'],
                        'pr_author': data.get('pr_author'),
                        'named_review_requests': sorted(requested), 'anonymized_team_auto_request': auto,
                        'old_path_reviewers_invited_by_name': old_requested,
                        'old_path_reviewers_invited_within_72_hours': old_requested_early,
                        'old_path_reviewers_actually_reviewed': old_reviewed,
                        'visible_review_request_events': len(data['request_events'])})
    result = {'pr_event_pairs': len(rows), 'audited': len(records),
              'visible_request_events': observed_requests,
              'with_anonymized_team_review_request': team_auto,
              'with_named_review_request': individual,
              'with_observed_old_history_reviewer_named_request': legacy_request,
              'with_observed_old_history_reviewer_named_request_within_72_hours': legacy_request_72h,
              'with_observed_old_history_reviewer_review': legacy_review,
              'with_neither_old_history_reviewer_named_request_nor_review': no_both,
              'errors': errors,
              'missing_pr_authors': sum(not x.get('pr_author') for x in records),
              'critical_limit': 'Anonymized team requests and observed old-path reviewers cannot establish independent missing-expertise truth.',
              'records': records}
    write_json(ROOT / 'results' / 'request_audit.json', result)
    print('Requests:', len(records), 'PR-event pairs,', observed_requests, 'events,',
          team_auto, 'with team requests,', individual, 'with named requests; errors', len(errors))


if __name__ == '__main__':
    main()
