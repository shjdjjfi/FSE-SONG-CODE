#!/usr/bin/env python3
"""Time-stratified public Issue Events API audit for team identity observability.

Public endpoint may expose team *slug* although a GitHub HTML timeline says
"a team". It does NOT reveal historical team MEMBER identity or competence.
Respect published API rate limits: no credential workarounds, no 403/429 retry.
"""

import concurrent.futures
import datetime as dt
import hashlib
import json
import random
import urllib.error
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data'/'issue_events'
RESULTS=ROOT/'results'
SEED=20271115


def write_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2,ensure_ascii=False,sort_keys=True)+'\n',encoding='utf-8')


def select_pairs(rows,per_event=4):
    by_event={}
    for row in rows:by_event.setdefault(row['event'],[]).append(row)
    selected=[]
    for event,group in sorted(by_event.items()):
        group=sorted(group,key=lambda r:(r['opened_at'],r['pr']))
        # Event-stratified, chosen without looking at observed reviewer outcome.
        seed=SEED+int(hashlib.sha256(event.encode()).hexdigest()[:8],16)
        rng=random.Random(seed)
        selected.extend(sorted(rng.sample(group,k=min(per_event,len(group))),key=lambda r:r['pr']))
    return selected


def one(row):
    repo,n=row['repo'],row['pr']
    path=OUT/f"{repo.replace('/','__')}__{n}.json"
    if path.exists():return json.loads(path.read_text(encoding='utf-8'))
    url=f'https://api.github.com/repos/{repo}/issues/{n}/events?per_page=100'
    req=urllib.request.Request(url,headers={'User-Agent':'N08-public-CODEOWNERS-measurement/1.0',
                                          'Accept':'application/vnd.github+json'})
    with urllib.request.urlopen(req,timeout=20) as resp:
        raw=resp.read()
        data=json.loads(raw)
        if not isinstance(data,list):raise ValueError('Expected a list of Issue Events')
        events=[]
        for ev in data:
            if ev.get('event') not in ('review_requested','review_request_removed','ready_for_review'):
                continue
            events.append({'event':ev.get('event'),'at':ev.get('created_at'),
                           'actor':(ev.get('actor') or {}).get('login'),
                           'reviewer':(ev.get('requested_reviewer') or {}).get('login'),
                           'team_slug':(ev.get('requested_team') or {}).get('slug'),
                           'team_url':(ev.get('requested_team') or {}).get('html_url')})
        record={'repo':repo,'pr':n,'source_url':url,'fetched_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
                'body_sha256':hashlib.sha256(raw).hexdigest(),'total_issue_events_first_page':len(data),
                'pagination_link':resp.headers.get('Link'),
                'http_status':resp.status,'rate_remaining':resp.headers.get('X-RateLimit-Remaining'),
                'request_events':events}
        write_json(path,record)
        return record


def main():
    rows=json.loads((RESULTS/'predictions.json').read_text(encoding='utf-8'))
    chosen=select_pairs(rows)
    # Deduplicate API calls across correlated migration events; retain all PR-event pairings.
    unique={(r['repo'],r['pr']):r for r in chosen}
    results={}; errors={}; aborted=False
    keys=sorted(unique)
    for index in range(0,len(keys),3):
        group=keys[index:index+3]
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            futures={pool.submit(one,unique[key]):key for key in group}
            for f in concurrent.futures.as_completed(futures):
                key=futures[f]
                try:results[key]=f.result()
                except urllib.error.HTTPError as err:
                    errors[str(key)]=f'HTTP {err.code}'
                    if err.code in (401,403,429):aborted=True
                except Exception as err:errors[str(key)]=str(err)[:200]
        if aborted:break
        # Halt before the official public API quota is exhausted.
        remaining=[int(x['rate_remaining']) for x in results.values()
                   if x.get('rate_remaining') not in (None,'')]
        if remaining and min(remaining)<5:
            aborted=True;errors['rate_policy']='Stopped voluntarily at fewer than five requests remaining';break
    paired=[]
    for r in chosen:
        path=OUT/f"{r['repo'].replace('/','__')}__{r['pr']}.json"
        paired.append({'event':r['event'],'repo':r['repo'],'pr':r['pr'],
                       'data_available':path.exists(),
                       'source_url':f'https://api.github.com/repos/{r["repo"]}/issues/{r["pr"]}/events?per_page=100'})
    write_json(RESULTS/'issue_event_sampling_audit.json',{
        'selection':'Four PRs per event; seeded random sample within each event; PR labels not used',
        'seed':SEED,'selected_pr_event_pairs':len(chosen),'selected_unique_prs':len(unique),
        'available_unique_prs':sum((OUT/f"{repo.replace('/','__')}__{n}.json").exists() for repo,n in unique),
        'incomplete_due_to_rate_or_other_error':aborted or bool(errors), 'errors':errors,'pairs':paired})
    print('API_ISSUE_EVENTS',sum(x['data_available'] for x in paired),'/',len(paired),
          'UNIQUE',len(results),'ERRORS',len(errors),'STOPPED',aborted,flush=True)
    if errors:print('EXCEPTIONS',json.dumps(errors,ensure_ascii=False)[:900])


if __name__=='__main__':main()
