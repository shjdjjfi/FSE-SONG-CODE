#!/usr/bin/env python3
"""Real consumer requirements, unchanged vs minimally edited, native CPU pip.

Only source files at frozen repository commits are used. Generated arms are
counterfactual constraints; no third-party source file is edited.
"""
from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor,as_completed
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import tomllib

HERE=Path(__file__).resolve().parent
MAN=json.loads((HERE/'source_manifest.json').read_text())
FIXES=MAN['fixed_selection']
REQ=HERE/'generated_requirements'
REPORTS=HERE/'dry_run_reports'
LOG=HERE/'consumer_pip_audit.jsonl'


def sha(b):return hashlib.sha256(b).hexdigest()


def safe_id(s):return hashlib.sha256(s.encode()).hexdigest()[:16]


def edit_direct(text,package,version):
    pattern=r'(?im)^(\s*'+re.escape(package)+r'\s*(?:\[[^]]+\])?\s*)(?:[><=!~].*?)(\s*(?:#.*)?)$'
    lines=text.splitlines(keepends=True)
    positions=[]
    for i,line in enumerate(lines):
        match=re.match(pattern,line.rstrip('\n'))
        if match and not line.lstrip().startswith('#'):
            positions.append(i)
    if len(positions)!=1:return None
    index=positions[0]
    old=lines[index]
    # A line with an inline license comment is preserved verbatim after '#'.
    comment=''
    if ' #' in old:comment=old[old.index(' #'):].rstrip('\n')
    lines[index]=f'{package}=={version}{comment}\n'
    return ''.join(lines)


def write_arm(case,arm,content):
    path=REQ/case/f'{arm}.txt'
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():assert path.read_text()==content,('arm changed',case,arm)
    else:path.write_text(content)
    return str(path.relative_to(HERE))


def collect_cases():
    # Exactly these source manifests; no case substitution on failure.
    configs=[
        ('skyline','snapshots/github/skyline-apiserver/requirements.txt','python-jose'),
        ('pyfa_historical','snapshots/github/pyfa/historical_requirements-requirements.txt','python-jose'),
        ('ai_npc','snapshots/github/AI-NPC/requirements.txt','fastapi'),
        ('allura','snapshots/github/allura/requirements.txt','webob'),
    ]
    cases=[]
    for name,path,package in configs:
        raw=(HERE/path).read_text()
        assert re.search(r'(?im)^\s*'+re.escape(package)+r'\s*(?:[<>=!~]|\[)',raw),name
        arms={'declared':raw}
        fix=FIXES[package]
        if name not in ('allura',):
            arms['injected_fixed']=raw.rstrip()+'\n'+package+'=='+fix['fixed']+'\n'
            arms['replaced_fixed']=edit_direct(raw,package,fix['fixed'])
            latest=MAN['pypi'][package]['latest_final_available']
            if latest!=fix['fixed']:
                arms['replaced_latest']=edit_direct(raw,package,latest)
        else:
            arms['replaced_vulnerable']=edit_direct(raw,package,fix['vulnerable'])
            # Already on first fixed; do not simulate a second independent arm.
        for arm,text in arms.items():
            if text is None:continue
            req=write_arm(name,arm,text)
            cases.append({'id':f'consumer/{name}/{arm}','scope':'entire_public_requirements_file',
                          'repo_case':name,'package':package,'arm':arm,'req_path':req,
                          'frozen_source_path':path,'req_sha256':sha(text.encode()),
                          'replaced_direct_constraint':arm.startswith('replaced_'),
                          'injected_additional_requirement':arm=='injected_fixed'})
    # Also run full *unchanged* lockfile for Mozilla's real consumer, which
    # contains a transitive webob pin and generated hashes.
    path='snapshots/github/pyramid_multiauth/requirements.txt'
    content=(HERE/path).read_text()
    cases.append({'id':'consumer/pyramid_multiauth/declared_lock',
                  'scope':'entire_public_hashed_lockfile','repo_case':'pyramid_multiauth',
                  'package':'webob','arm':'declared_lock',
                  'req_path':write_arm('pyramid_multiauth','declared_lock',content),
                  'frozen_source_path':path,'req_sha256':sha(content.encode()),
                  'replaced_direct_constraint':False,'injected_additional_requirement':False})
    for package,v in FIXES.items():
        for arm,version in [('vulnerable',v['vulnerable']),('first_fixed',v['fixed']),
                            ('latest',MAN['pypi'][package]['latest_final_available'])]:
            if arm=='latest' and version==v['fixed']:continue
            req=write_arm('root_controls',f'{package}-{arm}',package+'=='+version+'\n')
            cases.append({'id':f'root/{package}/{arm}','scope':'single_direct_root_control',
                          'repo_case':None,'package':package,'arm':arm,'req_path':req,
                          'frozen_source_path':None,'req_sha256':sha((package+'=='+version+'\n').encode()),
                          'replaced_direct_constraint':False,'injected_additional_requirement':False})
    assert len({c['id'] for c in cases})==len(cases)
    return cases


def status_for(exit_code,combined):
    s=combined.lower()
    if exit_code==0:return 'success'
    if any(t in s for t in ('readtimeouterror','connecttimeouterror','connection refused',
                           'temporary failure in name resolution','proxyerror','sslerror')):
        return 'network_unknown'
    if any(t in s for t in ('resolutionimpossible','cannot install ','conflicting dependencies',
                           'no matching distribution found',
                           'could not find a version that satisfies')):
        return 'unsat_or_no_wheel'
    return 'execution_error'


def run_case(case):
    cid=case['id']
    report=REPORTS/(safe_id(cid)+'.json')
    cmd=[sys.executable,'-m','pip','install','--dry-run','--ignore-installed',
         '--only-binary=:all:','--no-input','--disable-pip-version-check',
         '--retries','1','--timeout','12','--progress-bar','off',
         '--report',str(report),'-r',str(HERE/case['req_path'])]
    env={**os.environ,'PIP_NO_INPUT':'1','PIP_DISABLE_PIP_VERSION_CHECK':'1'}
    start=time.monotonic()
    try:
        p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
                         timeout=90,env=env)
        elapsed=round(time.monotonic()-start,3)
        output=p.stdout+'\n'+p.stderr
        record={'status':status_for(p.returncode,output),'exit_code':p.returncode,
                'elapsed_seconds':elapsed,'stdout_sha256':sha(p.stdout.encode()),
                'stderr_sha256':sha(p.stderr.encode()),
                'stdout_tail':p.stdout[-2200:],'stderr_tail':p.stderr[-2800:]}
    except subprocess.TimeoutExpired as exc:
        record={'status':'timeout_unknown','exit_code':None,
                'elapsed_seconds':round(time.monotonic()-start,3),
                'timeout_seconds':90,'stdout_tail':str(exc.stdout or b'')[-700:],
                'stderr_tail':str(exc.stderr or b'')[-700:]}
    record['cmd']=cmd
    record['report_file']=None
    if report.is_file():
        try:
            res=json.loads(report.read_text())
            record['report_file']=str(report.relative_to(HERE))
            record['report_sha256']=sha(report.read_bytes())
            record['resolved_package_count']=len(res.get('install',[]))
            target=case['package'].replace('_','-')
            recs=[x['metadata'].get('version') for x in res.get('install',[])
                  if x.get('metadata',{}).get('name','').lower().replace('_','-')==target]
            record['resolved_target_versions']=recs
        except (ValueError,KeyError) as exc:
            record['report_parse_error']=str(exc)[:200]
    return {**case,**record}


def main():
    REQ.mkdir(exist_ok=True);REPORTS.mkdir(exist_ok=True)
    cases=collect_cases()
    (HERE/'consumer_probe_manifest.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2))
    done={}
    if LOG.exists():
        for line in LOG.read_text().splitlines():
            try:r=json.loads(line);done[r['id']]=r
            except json.JSONDecodeError:continue
    pending=[x for x in cases if x['id'] not in done]
    print('PRESET CASES',len(cases),'completed',len(done),'new',len(pending),flush=True)
    with LOG.open('a') as f,ThreadPoolExecutor(max_workers=3) as exe:
        future={exe.submit(run_case,c):c for c in pending}
        for task in as_completed(future):
            c=future[task]
            try:r=task.result()
            except Exception as exc:r={**c,'status':'runner_exception','error':repr(exc)}
            done[c['id']]=r
            f.write(json.dumps(r,ensure_ascii=False)+'\n');f.flush()
            print(len(done),'/',len(cases),c['id'],r['status'],flush=True)
    print('FINAL',dict(Counter(r['status'] for r in done.values())),flush=True)


if __name__=='__main__':main()
