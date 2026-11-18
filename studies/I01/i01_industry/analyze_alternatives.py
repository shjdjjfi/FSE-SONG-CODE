#!/usr/bin/env python3
"""Enumerate every OSV-listed alternative fixed branch for six sampled projects.

Uses only public version-specific PyPI metadata and actual CPU-only uv solvers;
reports existential available alternatives, not a certified repair path.
"""
from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor,as_completed
import hashlib
import json
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request

HERE=Path(__file__).resolve().parent
PREV=HERE.parent/'i01_full'
sys.path.insert(0,str(PREV))
from run import VERSIONS, PLATFORMS, preflight_for, uv_case  # noqa: E402

SAMPLE=json.loads((PREV/'osv_sample120.json').read_text())
MULTI=sorted([x for x in SAMPLE if len(x['all_final_fixes'])>1],key=lambda x:x['project'])
ALTS=HERE/'alternative_raw_pypi'
RAW_LOG=HERE/'alternative_uv.jsonl'
MANIFEST=HERE/'alternative_catalog_manifest.json'


def digest(b):return hashlib.sha256(b).hexdigest()


def metadata_for(project,version):
    file=ALTS/project/(version+'.json')
    if file.is_file():raw=file.read_bytes()
    else:
        url=f'https://pypi.org/pypi/{project}/{version}/json'
        request=urllib.request.Request(url,headers={'User-Agent':'i01-cpu-research/2026-11-14'})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request,timeout=25) as res:raw=res.read()
                file.parent.mkdir(parents=True,exist_ok=True)
                file.write_bytes(raw)
                break
            except urllib.error.HTTPError as exc:
                if exc.code==404:
                    return {'status':'http_404','project':project,'version':version,'files':[],
                            'requires_python':None,'source_url':url}
                if attempt==2:return {'status':'http_error','project':project,'version':version,
                                      'files':[],'requires_python':None,'error':str(exc)}
            except Exception as exc:
                if attempt==2:return {'status':'network_error','project':project,'version':version,
                                      'files':[],'requires_python':None,'error':str(exc)}
            time.sleep(.3*(attempt+1))
    try:
        doc=json.loads(raw)
        assert doc['info']['version']==version
        return {'status':'ok','project':project,'version':version,
                'files':[{'filename':f['filename'],'packagetype':f['packagetype'],
                          'requires_python':f.get('requires_python'),
                          'yanked':f.get('yanked',False)} for f in doc.get('urls',[])],
                'requires_python':doc['info'].get('requires_python'),
                'raw_path':str(file.relative_to(HERE)),
                'raw_sha256':digest(raw),'source_url':f'https://pypi.org/pypi/{project}/{version}/json'}
    except (AssertionError,KeyError,ValueError) as exc:
        return {'status':'malformed','project':project,'version':version,'files':[],
                'requires_python':None,'error':str(exc)}


def read_log(path):
    out={}
    if path.exists():
        for line in path.read_text().splitlines():
            try:r=json.loads(line);out[r['case_id']]=r
            except (KeyError,json.JSONDecodeError):continue
    return out


def planned():
    assert len(MULTI)==6
    return [{'project':x['project'],'osv_id':x['osv_id'],
             'versions':x['all_final_fixes'],'first':x['fixed_version']}
            for x in MULTI]


def main():
    ALTS.mkdir(exist_ok=True)
    chosen=planned()
    expected_alts=sum(len(x['versions'])-1 for x in chosen)
    assert expected_alts==17,(expected_alts,chosen)
    if MANIFEST.exists():assert json.loads(MANIFEST.read_text())==chosen
    else:MANIFEST.write_text(json.dumps(chosen,indent=2))
    versions=[(x['project'],ver) for x in chosen for ver in x['versions']]
    metadata={}
    with ThreadPoolExecutor(max_workers=3) as ex:
        results=list(ex.map(lambda pair:metadata_for(*pair),versions))
    for meta in results:metadata[(meta['project'],meta['version'])]=meta
    md_out=[{k:v for k,v in x.items()} for x in results]
    (HERE/'alternative_metadata.json').write_text(json.dumps(md_out,indent=2,ensure_ascii=False))
    targets=[]
    preflights={}
    for item in chosen:
        for version in item['versions']:
            for py in VERSIONS:
                for plat in PLATFORMS:
                    cid=f'{item["project"]}=={version}|py{py}|{plat}'
                    check=preflight_for(metadata[(item['project'],version)],py,plat)
                    preflights[cid]={**check,'metadata_status':metadata[(item['project'],version)]['status']}
                    if version!=item['first']:
                        targets.append({'case_id':cid,'project':item['project'],
                                        'version':version,'python':py,'platform':plat})
    assert len(targets)==204,len(targets)
    (HERE/'alternative_preflight_276.json').write_text(json.dumps(preflights,indent=2))
    done=read_log(RAW_LOG)
    pending=[x for x in targets if x['case_id'] not in done]
    print('ALTERNATIVE UV: all fixed versions',len(versions),'alternative targets',len(targets),
          'already',len(done),'pending',len(pending),flush=True)
    with RAW_LOG.open('a') as f,ThreadPoolExecutor(max_workers=3) as ex:
        futs={ex.submit(uv_case,c):c for c in pending}
        for task in as_completed(futs):
            case=futs[task]
            try:rec=task.result()
            except Exception as exc:rec={'case_id':case['case_id'],
                                        'status':'unhandled_error','error':repr(exc)}
            f.write(json.dumps(rec,ensure_ascii=False)+'\n');f.flush()
            done[rec['case_id']]=rec
            if len(done)%18==0:print('ALT',len(done),'/',len(targets),
                                    dict(Counter(x['status'] for x in done.values())),flush=True)
    assert len(done)==len(targets)
    original=read_log(PREV/'uv_full.jsonl')
    original.update(read_log(PREV/'uv_macos11.jsonl'))
    pre_orig={x['case_id']:x for x in json.loads((PREV/'all_1440_cases.json').read_text())}
    cases=[]
    for item in chosen:
        for py in VERSIONS:
            for plat in PLATFORMS:
                first_id=f'{item["project"]}=={item["first"]}|py{py}|{plat}'
                orig=original[first_id]['status']
                root_first=pre_orig[first_id]['b2_root_gate']
                alts=[]
                for version in item['versions'][1:]:
                    cid=f'{item["project"]}=={version}|py{py}|{plat}'
                    alts.append({'version':version,'root_compatible':preflights[cid]['b2_root_gate'],
                                 'uv_status':done[cid]['status']})
                recovery=next((x['version'] for x in alts if x['uv_status']=='success'),None)
                root_recovery=next((x['version'] for x in alts if x['root_compatible'] is True),None)
                cases.append({'project':item['project'],'python':py,'platform':plat,
                              'first_version':item['first'],'first_uv_status':orig,
                              'first_root_compatible':root_first,'alternatives':alts,
                              'any_uv_success':orig=='success' or recovery is not None,
                              'any_root_compatible':root_first is True or root_recovery is not None,
                              'uv_recovered_by':recovery if orig!='success' else None,
                              'root_recovered_by':root_recovery if root_first is False else None})
    nfirst=sum(x['first_uv_status']=='success' for x in cases)
    nany=sum(x['any_uv_success'] for x in cases)
    rootfirst=sum(x['first_root_compatible'] is True for x in cases)
    rootany=sum(x['any_root_compatible'] for x in cases)
    outcome={'date':'2026-11-14','sample_projects':len(SAMPLE),
             'multi_fixed_projects':len(chosen),'osv_fixed_events':len(versions),
             'additional_fixed_events':expected_alts,'target_cases':len(cases),
             'extra_actual_uv_calls':len(done),'metadata_statuses':dict(Counter(x['status'] for x in results)),
             'first_fixed_uv_success':nfirst,'any_listed_fixed_uv_success':nany,
             'additional_uv_resolvable_cells':nany-nfirst,
             'first_fixed_root_compatible':rootfirst,'any_listed_fixed_root_compatible':rootany,
             'additional_root_compatible_cells':rootany-rootfirst,
             'alternative_uv_statuses':dict(Counter(r['status'] for r in done.values())),
             'cases':cases,'catalog':chosen,
             'limitations':['Only 6 purposively inspected multi-fixed projects among the original 120.',
                            'OSV-listed fixed releases are not necessarily interchangeable maintenance branches.',
                            'uv ignores Requires-Python upper bounds; no source builds or application constraints.',
                            'Existence of an installable fixed branch does not prove app-code compatibility or safety from other CVEs.']}
    (HERE/'alternative_results.json').write_text(json.dumps(outcome,indent=2,ensure_ascii=False))
    print('FINAL ALTERNATIVES',json.dumps({k:outcome[k] for k in
             ('first_fixed_uv_success','any_listed_fixed_uv_success','additional_uv_resolvable_cells',
              'first_fixed_root_compatible','any_listed_fixed_root_compatible',
              'additional_root_compatible_cells','alternative_uv_statuses')},indent=2),flush=True)


if __name__=='__main__':main()
