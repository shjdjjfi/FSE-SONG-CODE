#!/usr/bin/env python3
"""Freeze verified public GitHub config and PyPI/OSV metadata before probes."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time
import urllib.request
import zipfile

from packaging.version import InvalidVersion, Version

HERE=Path(__file__).resolve().parent
PREV=HERE.parent/'i01_full'
OUT=HERE/'snapshots'
SOURCES=HERE/'sources'

REPOS={
    'skyline-apiserver':{
        'url':'https://github.com/openstack/skyline-apiserver',
        'commit':'8d130ece9600179150a393e3971a4d304a0848e2',
        'paths':['requirements.txt','pyproject.toml']},
    'overhave':{
        'url':'https://github.com/Tinkoff/overhave',
        'commit':'793bbd6cb98c2cd0b1cb432d1cd56bbf77e11518',
        'paths':['pyproject.toml']},
    'AI-NPC':{
        'url':'https://github.com/rainpaw/AI-NPC',
        'commit':'6d3dfb80758c2163af72254281d74a5144ba3174',
        'paths':['requirements.txt','app/main.py','app/config.py']},
    'allura':{
        'url':'https://github.com/apache/allura',
        'commit':'22b7bfb96a268d4e1c04dee0c71ddcbb4a03f450',
        'paths':['requirements.txt','CHANGES']},
    'pypiserver':{
        'url':'https://github.com/pypiserver/pypiserver',
        'commit':'70648dbe7193a3687fb48650b0c67287cc69d6b6',
        'paths':['pyproject.toml','uv.lock','CHANGES.rst']},
    'pyramid_multiauth':{
        'url':'https://github.com/mozilla-services/pyramid_multiauth',
        'commit':'86865c11248a3ac168f5c448be51dfb7cce773b6',
        'paths':['pyproject.toml','requirements.in','requirements.txt']},
}
PYFA={
    'url':'https://github.com/pyfa-org/Pyfa',
    'current_commit':'b79cd902b0bfa56a43cc5c08b6266fa842f25e85',
    'historical_commit':'430e7af225b4b3ef061ea777fb849fdc05f7e7d0',
    'historical_removed_by':'9d57e3b8072676d854132e2d2835b0c37c9125ca',
}
FIXES={
    'python-jose':{'vulnerable':'3.3.0','fixed':'3.4.0','osv':'GHSA-cjwg-qfpm-7377'},
    'fastapi':{'vulnerable':'0.109.0','fixed':'0.109.1','osv':'PYSEC-2024-38'},
    'webob':{'vulnerable':'1.8.10','fixed':'1.8.11','osv':'PYSEC-2026-3943'},
}


def sha(b:bytes)->str:return hashlib.sha256(b).hexdigest()


def fetch(url:str,attempts:int=3)->bytes:
    for i in range(attempts):
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'i01-cpu-research/2026-11-14',
                                                     'Accept':'application/json'})
            with urllib.request.urlopen(req,timeout=25) as res:
                data=res.read()
                if not data:raise RuntimeError('empty response')
                return data
        except Exception:
            if i+1==attempts:raise
            time.sleep(.8*(i+1))
    raise AssertionError('unreachable')


def save_snapshot(relative:str,data:bytes):
    path=OUT/relative
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        assert path.read_bytes()==data,f'existing snapshot conflicts: {path}'
    else:
        path.write_bytes(data)
    return {'path':str(path.relative_to(HERE)),'sha256':sha(data),'bytes':len(data)}


def main():
    OUT.mkdir(exist_ok=True)
    manifest={'date':'2026-11-14','repositories':{},'osv':{},'pypi':{},
              'fixed_selection':FIXES,'notes':['Git SHAs are checked before resolution/install.',
              'Pyfa historical requirements.txt is from the parent of its 2026-07-31 removal commit.']}
    for name,repo in REPOS.items():
        source=SOURCES/name
        head=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
        assert head==repo['commit'],(name,head)
        files={}
        for relative in repo['paths']:
            src=source/relative
            if not src.exists():
                files[relative]={'status':'not_at_frozen_commit'}
            else:
                files[relative]=save_snapshot(f'github/{name}/{relative}',src.read_bytes())
        manifest['repositories'][name]={**repo,'files':files}
    pyfa_files={}
    for title,commit,path in [
        ('current_pyproject',PYFA['current_commit'],'pyproject.toml'),
        ('historical_requirements',PYFA['historical_commit'],'requirements.txt')]:
        url=f'https://raw.githubusercontent.com/pyfa-org/Pyfa/{commit}/{path}'
        pyfa_files[title]={**save_snapshot(f'github/pyfa/{title}-{path}',fetch(url)),
                           'source_url':url,'commit':commit}
    assert b'python-jose==3.3.0' in (OUT/pyfa_files['historical_requirements']['path'].replace('snapshots/','')).read_bytes()
    assert b'python-jose==3.5.0' in (OUT/pyfa_files['current_pyproject']['path'].replace('snapshots/','')).read_bytes()
    manifest['repositories']['pyfa']={**PYFA,'files':pyfa_files,
                                    'history_status':'historical pin verified; current pin verified'}

    with zipfile.ZipFile(PREV/'raw/osv-pypi-20261114.zip') as z:
        for package,record in FIXES.items():
            filename=record['osv']+'.json'
            raw=z.read(filename)
            doc=json.loads(raw)
            assert doc['id']==record['osv']
            manifest['osv'][package]={**save_snapshot(f'osv/{filename}',raw),
                                      'osv_id':record['osv'],
                                      'published':doc.get('published'),
                                      'references':doc.get('references',[])}

    for package,record in FIXES.items():
        raw=fetch(f'https://pypi.org/pypi/{package}/json')
        index=json.loads(raw)
        versioned=[]
        for version,files in index['releases'].items():
            try:v=Version(version)
            except InvalidVersion:continue
            if v.is_prerelease or v.is_devrelease or not files:continue
            if all(f.get('yanked',False) for f in files):continue
            versioned.append((v,version))
        assert versioned,package
        latest=max(versioned)[1]
        item={'index':save_snapshot(f'pypi/{package}/index.json',raw),
              'latest_final_available':latest,'arms':{}}
        for role,version in [('vulnerable',record['vulnerable']),('fixed',record['fixed']),('latest',latest)]:
            payload=fetch(f'https://pypi.org/pypi/{package}/{version}/json')
            info=json.loads(payload)
            assert info['info']['version']==version,(package,role)
            item['arms'][role]={**save_snapshot(f'pypi/{package}/{role}-{version}.json',payload),
                                 'version':version,
                                 'requires_python':info['info'].get('requires_python'),
                                 'wheel_count':sum(x['packagetype']=='bdist_wheel' for x in info['urls'])}
        manifest['pypi'][package]=item
    path=HERE/'source_manifest.json'
    path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    print(json.dumps({'repositories':[(n,r.get('commit',r.get('current_commit'))) for n,r in manifest['repositories'].items()],
                      'pypi':{n:{'fixed':r['arms']['fixed']['version'],
                                 'latest':r['latest_final_available']} for n,r in manifest['pypi'].items()}},
                     ensure_ascii=False,indent=2))


if __name__=='__main__':main()
