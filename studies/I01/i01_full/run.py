#!/usr/bin/env python3
"""Actual CPU-only PyPI wheel resolution, preflight arms, and pip replication.

Run: python run.py preflight | uv | pip ; reruns resume from JSONL checkpoints.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.utils import InvalidWheelFilename, parse_wheel_filename
from packaging.version import Version

try:
    from pip._internal.models.target_python import TargetPython
except ImportError as exc:
    raise SystemExit(f'pip TargetPython not found: {exc}')

BASE=Path(__file__).resolve().parent
VERSIONS=['3.8','3.10','3.12','3.14']
PLATFORMS={
    'linux_amd64':('manylinux2014_x86_64','x86_64-manylinux2014'),
    'windows_amd64':('win_amd64','x86_64-pc-windows-msvc'),
    'macos_arm64':('macosx_11_0_arm64','aarch64-apple-darwin'),
}
SAMPLE=json.loads((BASE/'osv_sample120.json').read_text())
META={r['project']:r for r in json.loads((BASE/'metadata_index.json').read_text())}
ALL_TARGETS={
    (py,plat):TargetPython(py_version_info=tuple(int(x) for x in py.split('.')),
                           platforms=[spec[0]],implementation='cp',
                           abis=[f"cp{py.replace('.','')}"]).get_sorted_tags()
    for py in VERSIONS for plat,spec in PLATFORMS.items()
}
# pip uses vendored `pip._vendor.packaging.tags.Tag`, whereas top-level
# `packaging.utils.parse_wheel_filename` returns `packaging.tags.Tag`.
# These are deliberately distinct Python classes; normalize to PEP 425 strings.
ALL_TAGS={k:set(map(str,v)) for k,v in ALL_TARGETS.items()}


def accepts(spec,python):
    if not spec:
        return True
    try:
        return Version(f'{python}.0') in SpecifierSet(spec)
    except (InvalidSpecifier,ValueError):
        return None


def preflight_for(metadata,py,plat):
    if metadata['status']!='ok':
        return {'b0_requires_python':None,'b1_tags':None,'b2_root_gate':None,
                'root_reason':'metadata_'+metadata['status'],
                'compatible_wheels':0,'all_wheels':0,'rejected_by_python':0,
                'rejected_by_tags':0,'parse_failures':0}
    info=accepts(metadata['requires_python'],py)
    target_tags=ALL_TAGS[(py,plat)]
    wheels=[f for f in metadata['files'] if f['packagetype']=='bdist_wheel']
    tags_match=0
    simultaneous=0
    python_rej=0
    tag_rej=0
    error=0
    all_yanked=0
    for f in wheels:
        try:
            _,_,_,file_tags=parse_wheel_filename(f['filename'])
            tag_match=bool(set(map(str,file_tags)) & target_tags)
        except (InvalidWheelFilename,ValueError,TypeError):
            tag_match=False
            error+=1
        file_py=accepts(f.get('requires_python') or metadata['requires_python'],py)
        if tag_match:
            tags_match+=1
            if file_py is True and not f.get('yanked',False):
                simultaneous+=1
            if f.get('yanked',False):
                all_yanked+=1
        else:
            tag_rej+=1
        if file_py is False:
            python_rej+=1
    root_reason='ok'
    if not wheels:root_reason='no_wheel_for_release'
    elif not tags_match:root_reason='no_matching_platform_abi_wheel'
    elif not simultaneous:
        root_reason='requires_python_or_yanked'
    return {
        'b0_requires_python':info,
        'b1_tags':bool(tags_match),
        'b2_root_gate':bool(simultaneous),
        'root_reason':root_reason,
        'compatible_wheels':simultaneous,
        'all_wheels':len(wheels),
        'rejected_by_python':python_rej,
        'rejected_by_tags':tag_rej,
        'parse_failures':error,
        'matched_but_yanked':all_yanked,
    }


def cases():
    output=[]
    for item in SAMPLE:
        for py in VERSIONS:
            for plat in PLATFORMS:
                project=item['project']
                case_id=f'{project}=={item["fixed_version"]}|py{py}|{plat}'
                output.append({
                    'case_id':case_id,'project':project,'version':item['fixed_version'],
                    'osv_id':item['osv_id'],'stratum':item['stratum'],
                    'python':py,'platform':plat,
                    'metadata_status':META[project]['status'],
                    **preflight_for(META[project],py,plat),
                })
    assert len(output)==1440
    return output


def run_subprocess(cmd,requirement,timeout=45,attempts=2,env=None):
    total_elapsed=0.0
    for trial in range(attempts):
        start=time.monotonic()
        try:
            r=subprocess.run(cmd,input=requirement+'\n',text=True,encoding='utf-8',
                             stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                             timeout=timeout,check=False,env=env)
            elapsed=time.monotonic()-start
            total_elapsed+=elapsed
            combined=(r.stdout+'\n'+r.stderr)
            low=combined.lower()
            if r.returncode==0:
                status='success'
            elif any(s in low for s in ['proxyerror','connecttimeout','readtimeout','sslerror',
                                        'temporary failure in name resolution','failed to establish a new connection',
                                        'network is unreachable','failed to fetch']):
                status='unknown_error'
            elif ('no solution found' in low or 'no matching distribution found' in low
                  or 'could not find a version that satisfies' in low or 'resolutionimpossible' in low):
                status='unsat'
            else:
                status='unknown_error'
            # Retrying an unsatisfiable result cannot make it satisfiable.
            if status=='unknown_error' and trial+1<attempts:
                time.sleep(0.2)
                continue
            return {
                'status':status,'return_code':r.returncode,'seconds':round(total_elapsed,4),
                'attempts':trial+1,'stdout_sha256':hashlib.sha256(r.stdout.encode()).hexdigest(),
                'stderr_sha256':hashlib.sha256(r.stderr.encode()).hexdigest(),
                'stdout_excerpt':r.stdout[:3500],'stderr_excerpt':r.stderr[-4500:],
                'resolved_packages':sum(bool(re.match(r'^[a-zA-Z0-9_.-]+==',line)) for line in r.stdout.splitlines()),
            }
        except subprocess.TimeoutExpired as exc:
            elapsed=time.monotonic()-start
            total_elapsed+=elapsed
            if trial+1==attempts:
                return {'status':'timeout','return_code':None,'seconds':round(total_elapsed,4),
                        'attempts':trial+1,'stdout_excerpt':str(exc.stdout or '')[:500],
                        'stderr_excerpt':str(exc.stderr or '')[:500]}
        except OSError as exc:
            return {'status':'execution_error','return_code':None,
                    'seconds':round(total_elapsed+time.monotonic()-start,4),
                    'attempts':trial+1,'error':str(exc)[:200]}


def uv_case(case):
    python=case['python']
    platform=PLATFORMS[case['platform']][1]
    cmd=['uv','pip','compile','-','--python-version',python,'--python-platform',platform,
         '--only-binary',':all:','--no-python-downloads','--no-header','--no-annotate','--no-progress']
    env=dict(os.environ,UV_CACHE_DIR=str(BASE/'uv_cache'),UV_NO_PROGRESS='1')
    # uv's default macOS deployment target is 13.0 even when the target
    # triple is aarch64-apple-darwin. Our preregistered target is macOS 11.
    if case['platform']=='macos_arm64':
        env['MACOSX_DEPLOYMENT_TARGET']='11.0'
    r=run_subprocess(cmd,f"{case['project']}=={case['version']}",timeout=45,attempts=2,env=env)
    return {'case_id':case['case_id'],'method':'uv_full',**r}


def pip_case(case):
    py=case['python']
    pipplat=PLATFORMS[case['platform']][0]
    initial=[sys.executable,'-m','pip','install','--dry-run','--ignore-installed',
             '--python-version',py,'--implementation','cp','--platform',pipplat,
             '--only-binary=:all:','--no-input','--disable-pip-version-check',
             '--retries','1','--timeout','10']
    forde=run_subprocess(initial+[f"{case['project']}=={case['version']}"],'',timeout=75,attempts=2)
    direct=run_subprocess(initial+['--no-deps',f"{case['project']}=={case['version']}"],'',timeout=75,attempts=2)
    return {'case_id':case['case_id'],'method':'pip_validation',
            'full':forde,'no_deps':direct}


def pip_all_case(case):
    """Strict pip falsification beyond the preregistered 20% dual-mode holdout.

    Independent direct rejection implies full rejection for the same pinned
    fixed release; otherwise perform an actual full pip dry run.
    """
    py=case['python']
    pipplat=PLATFORMS[case['platform']][0]
    initial=[sys.executable,'-m','pip','install','--dry-run','--ignore-installed',
             '--python-version',py,'--implementation','cp','--platform',pipplat,
             '--only-binary=:all:','--no-input','--disable-pip-version-check',
             '--retries','1','--timeout','10']
    root_req=f"{case['project']}=={case['version']}"
    is_holdout=case['case_id'] in PIP_HOLDOUT_IDS
    direct=None
    if case['b2_root_gate'] is False or is_holdout:
        direct=run_subprocess(initial+['--no-deps',root_req],'',timeout=75,attempts=2)
    infer_unsat=(not is_holdout and direct is not None and direct['status']=='unsat')
    if infer_unsat:
        full={'status':'unsat','seconds':0.0,'return_code':None,
              'method':'inferred_from_independent_pip_no_deps_unsat',
              'proof':'A pinned direct requirement rejected by pip cannot become installable by adding dependencies.'}
    else:
        full=run_subprocess(initial+[root_req],'',timeout=75,attempts=2)
    return {'case_id':case['case_id'],'method':'pip_all','full':full,
            'no_deps':direct,'full_inferred_from_no_deps':infer_unsat,
            'preregistered_20pct_holdout':is_holdout}


def validate_sample(rows):
    by_cell={}
    for case in rows:
        k=(case['stratum'],case['python'],case['platform'])
        by_cell.setdefault(k,[]).append(case)
    sample=[]
    for key,cell in by_cell.items():
        ordered=sorted(cell,key=lambda c:hashlib.sha256(('i01-pip20-'+c['case_id']).encode()).hexdigest())
        assert len(ordered)==40,(key,len(ordered))
        sample.extend(ordered[:8])
    assert len(sample)==288
    return sample


PIP_HOLDOUT_IDS={x['case_id'] for x in validate_sample(cases())}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('mode',choices=['preflight','uv','uv_macos11','pip','pip_all'])
    p.add_argument('--workers',type=int,default=4)
    a=p.parse_args()
    assert 1<=a.workers<=4
    rows=cases()
    (BASE/'all_1440_cases.json').write_text(json.dumps(rows,indent=2))
    summary={
        'planned_cases':len(rows),'root_gates':dict(Counter(str(c['b2_root_gate']) for c in rows)),
        'metadata_cases':dict(Counter(c['metadata_status'] for c in rows)),
        'root_failure_reasons':dict(Counter(c['root_reason'] for c in rows)),
    }
    (BASE/'preflight_summary.json').write_text(json.dumps(summary,indent=2))
    if a.mode=='preflight':
        print(json.dumps(summary,indent=2))
        return
    if a.mode=='uv_macos11':
        rows=[x for x in rows if x['platform']=='macos_arm64']
    if a.mode=='pip':
        rows=validate_sample(rows)
        (BASE/'pip_validation_ids.json').write_text(json.dumps([r['case_id'] for r in rows],indent=2))
    elif a.mode=='pip_all':
        (BASE/'pip_validation_ids.json').write_text(json.dumps([r['case_id'] for r in validate_sample(rows)],indent=2))
    output=BASE/({'uv':'uv_full.jsonl','uv_macos11':'uv_macos11.jsonl',
                  'pip':'pip_validation.jsonl','pip_all':'pip_all.jsonl'}[a.mode])
    done={}
    if output.exists():
        for line in output.read_text().splitlines():
            try:
                rec=json.loads(line)
                done[rec['case_id']]=rec
            except json.JSONDecodeError:
                continue
    pending=[case for case in rows if case['case_id'] not in done]
    fn=uv_case if a.mode in ('uv','uv_macos11') else pip_all_case if a.mode=='pip_all' else pip_case
    print(f'{a.mode}: total {len(rows)}, already {len(done)}, remaining {len(pending)}; concurrency {a.workers}',flush=True)
    with ThreadPoolExecutor(max_workers=a.workers) as executor:
        futures={executor.submit(fn,item):item for item in pending}
        with output.open('a') as f:
            for n,fut in enumerate(as_completed(futures),1):
                item=futures[fut]
                try:rec=fut.result()
                except Exception as exc:
                    rec={'case_id':item['case_id'],'method':a.mode,
                         'status':'unhandled_exception','error':repr(exc)}
                f.write(json.dumps(rec,ensure_ascii=False)+'\n')
                f.flush()
                done[rec['case_id']]=rec
                if n%30==0 or n==len(pending):
                    counts=Counter((rec.get('status') or rec.get('full',{}).get('status','unknown')) for rec in done.values())
                    print(f'{a.mode} {n}/{len(pending)} new; total {len(done)}; statuses {dict(counts)}',flush=True)
    print('FINISHED',a.mode,len(done),flush=True)
    if a.mode=='pip_all' and len(done)==1440:
        ordered=[done[x['case_id']] for x in validate_sample(cases())]
        assert all(x['no_deps'] is not None and not x['full_inferred_from_no_deps'] for x in ordered)
        with (BASE/'pip_validation.jsonl').open('w') as f:
            for x in ordered:
                f.write(json.dumps({'case_id':x['case_id'],'method':'pip_validation_from_full_audit',
                                    'full':x['full'],'no_deps':x['no_deps']})+'\n')
        print('Saved 288 prespecified dual-mode pip cases from full strict audit',flush=True)


if __name__=='__main__':main()
