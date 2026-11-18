#!/usr/bin/env python3
"""Audit observability of historic CODEOWNERS team membership.

Do not equate old-path reviewers/contributors with a past GitHub team roster.
"""

import collections
import datetime as dt
import json
import urllib.error
import urllib.request
from pathlib import Path

from analyze import DATA, RESULTS, make_history, parse_time, read_json, reviewed_users, save_json


def public_team_probe(organization, slug):
    url = f'https://api.github.com/orgs/{organization}/teams/{slug}'
    req = urllib.request.Request(url, headers={'User-Agent': 'FSE-N08-research/0.2', 'Accept':'application/vnd.github+json'})
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            body = json.loads(resp.read())
            return {'url': url, 'http_status': resp.status, 'visibility': body.get('privacy'),
                    'note':'Public current team metadata only; does not establish membership at historical PR dates'}
    except urllib.error.HTTPError as exc:
        return {'url': url, 'http_status': exc.code,
                'note':'Not available anonymously; cannot infer historical team members from this response'}
    except Exception as exc:
        return {'url': url, 'http_status': None, 'error': str(exc)[:150],
                'note':'No verifiable membership fetched'}


def main():
    events = [read_json(p) for p in sorted((DATA / 'events').glob('*.json'))]
    candidate_groups, _, _ = make_history(events, 12, 20)
    seen_teams, evidence = {}, []
    for event, before, after in candidate_groups:
        t = parse_time(event['merged_at'])
        counts, refs = collections.Counter(), collections.defaultdict(list)
        for pr in before:
            if parse_time(pr['merged_at']) >= t:
                continue
            for user in reviewed_users(pr, before=t):
                counts[user] += 1
                refs[user].append(pr['source_url'])
        repo = event['repo']
        requests = []
        for pr in after:
            p = DATA / 'request_timelines' / f"{repo.replace('/', '__')}__{pr['pr']}.json"
            if not p.exists():
                continue
            info = read_json(p)
            for row in info['request_events']:
                if row.get('team_request_anonymized'):
                    requests.append(pr['source_url'])
        teams = sorted(set(event['old_owner'] + event['new_owner']))
        for team in teams:
            if team not in seen_teams:
                org, slug = team.removeprefix('@').split('/', 1)
                seen_teams[team] = public_team_probe(org, slug)
        evidence.append({'event': event['id'], 'repository': repo,
                         'at_handoff': event['merged_at'], 'old_codeowner_team_handles': event['old_owner'],
                         'new_codeowner_team_handles': event['new_owner'],
                         'team_membership_at_handoff': 'NOT_IDENTIFIABLE_FROM_PUBLIC_DATA',
                         'anonymized_team_request_prs': sorted(set(requests)),
                         'historical_old_path_reviewers_NOT_VERIFIED_TEAM_MEMBERS': [
                             {'login': user, 'pre_migration_reviews': n, 'reviewed_pr_urls': refs[user]}
                             for user,n in sorted(counts.items(), key=lambda pair: (-pair[1],pair[0]))]})
    save_json('historical_team_membership_audit.json', {
        'observed_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'interpretation': 'Timestamped CODEOWNERS team handles are verified. Human membership lists remain unknown; pre-handoff module reviewers are NOT equivalent to team members.',
        'public_team_endpoint_probes': seen_teams, 'events': evidence})
    print('EVENTS', len(evidence), 'TEAMS', len(seen_teams), 'PUBLIC_TEAM_META',
          sum(v['http_status'] == 200 for v in seen_teams.values()),
          'UNKNOWN_ROSTERS', sum(x['team_membership_at_handoff'].startswith('NOT') for x in evidence))


if __name__ == '__main__':
    main()
