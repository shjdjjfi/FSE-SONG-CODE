#!/usr/bin/env python3
"""OSV PyPI frame statistics, computed BEFORE sampling or resolver outcomes."""
from __future__ import annotations

from collections import Counter, defaultdict
import datetime as dt
import json
import pathlib
import zipfile

from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version

BASE=pathlib.Path(__file__).resolve().parent
Z=BASE/'raw'/'osv-pypi-20261114.zip'


def year_bucket(value):
    try:year=int(str(value)[:4])
    except (ValueError,TypeError):return 'unknown'
    return 'early' if year<=2023 else 'middle' if year<=2025 else 'recent'


def iter_fixes():
    with zipfile.ZipFile(Z) as archive:
        for name in sorted(n for n in archive.namelist() if n.endswith('.json')):
            try:v=json.loads(archive.read(name))
            except Exception:continue
            if v.get('withdrawn'):continue
            for affected in v.get('affected',[]):
                package=affected.get('package') or {}
                if package.get('ecosystem')!='PyPI' or not package.get('name'):continue
                project=canonicalize_name(package['name'])
                for rng in affected.get('ranges',[]):
                    if rng.get('type')!='ECOSYSTEM':continue
                    for event in rng.get('events',[]):
                        fixed=event.get('fixed')
                        if not fixed:continue
                        try:ver=Version(fixed)
                        except InvalidVersion:continue
                        if ver.is_prerelease or ver.is_devrelease:continue
                        yield {'osv_id':v.get('id'), 'project':project,
                               'fixed_version':fixed, 'published':v.get('published'),
                               'published_stratum':year_bucket(v.get('published')),
                               'aliases':v.get('aliases',[]),
                               'modified':v.get('modified'),
                               'summary':v.get('summary','')[:200]}


def main():
    records=list(iter_fixes())
    unique={}
    for rec in records:
        k=(rec['project'],str(Version(rec['fixed_version'])))
        old=unique.get(k)
        if old is None:
            unique[k]={**rec,'osv_ids':[rec['osv_id']]}
        else:
            old['osv_ids'].append(rec['osv_id'])
            if str(rec['published'])<str(old['published']):
                old['published']=rec['published']
                old['published_stratum']=rec['published_stratum']
    projects=defaultdict(list)
    for x in unique.values():projects[x['project']].append(x)
    stats={'raw_fixed_mentions':len(records),'unique_project_version_pairs':len(unique),
           'unique_projects':len(projects), 'strata':dict(Counter(x['published_stratum'] for x in unique.values())),
           'project_strata':dict(Counter(min((r['published_stratum'] for r in rs),
               key=lambda y:['early','middle','recent','unknown'].index(y)) for rs in projects.values())),
           'first_10_projects':sorted(projects)[:10]}
    print(json.dumps(stats,ensure_ascii=False,indent=2))
    (BASE/'osv_inventory.json').write_text(json.dumps(stats,indent=2))


if __name__=='__main__':main()
