#!/usr/bin/env python3
"""CPU-only isolated pip installs and bounded actual public-project tests."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor,as_completed
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
SOURCES=HERE/'sources'
ENV_ROOT=HERE/'venvs'
LOGDIR=HERE/'install_logs'
LOG=HERE/'install_test_results.jsonl'
MAN=json.loads((HERE/'source_manifest.json').read_text())
PACKAGE_VERSIONS={n:r['latest_final_available'] for n,r in MAN['pypi'].items()}
PYPI='https://pypi.org/simple'


def sha(data):return hashlib.sha256(data).hexdigest()


AI_SMOKE='''
import os
assert os.environ.get('DEMO_MODE','').lower()=='true'
from fastapi.testclient import TestClient
from app.main import app
with TestClient(app) as client:
    response = client.get('/')
    assert response.status_code == 200, (response.status_code, response.text)
    payload = response.json()
    assert payload.get('status') == 'online', payload
    schema=client.get('/openapi.json')
    assert schema.status_code == 200
    assert '/npc' in schema.json().get('paths', {}), schema.text[:400]
print('AI-NPC: root endpoint, OpenAPI route and in-process HTTP smoke passed')
'''

JOSE_SMOKE='''
from jose import jwt
body={'sub':'public-cpu-smoke','iat':1234567}
token=jwt.encode(body,'nonproduction-local-test-key',algorithm='HS256')
decoded=jwt.decode(token,'nonproduction-local-test-key',algorithms=['HS256'])
assert decoded['sub']==body['sub']
print('python-jose: benign JWT roundtrip passed')
'''


def cases():
    out=[]
    ai_versions=[('vulnerable','0.109.0'),('first_fixed','0.109.1'),
                 ('latest',PACKAGE_VERSIONS['fastapi'])]
    for arm,version in ai_versions:
        file='generated_requirements/ai_npc/'+({'vulnerable':'declared',
             'first_fixed':'replaced_fixed','latest':'replaced_latest'}[arm])+'.txt'
        out.append({'id':'ai_npc_'+arm,'project':'rainpaw/AI-NPC','package':'fastapi',
                    'target_version':version,'arm':arm,'install_type':'exact_project_requirements',
                    'install_requirements_file':file,'packages':[],
                    'test_type':'researcher_smoke_on_real_repo_code','test_python':AI_SMOKE,
                    'source_workdir':'AI-NPC','env_overrides':{'DEMO_MODE':'true'}})
    for arm,version in [('vulnerable','1.8.10'),('first_fixed','1.8.11')]:
        out.append({'id':'pyramid_multiauth_'+arm,'project':'mozilla-services/pyramid_multiauth',
                    'package':'webob','target_version':version,'arm':arm,
                    'install_type':'upstream_runtime_requirements_plus_exact_webob_and_test_tools',
                    'packages':['pyramid>=2,<3',f'webob=={version}','pytest>=8,<10',
                                'pytest-cov>=4','setuptools>=64','setuptools-scm>=8'],
                    'test_type':'existing_repository_pytest',
                    'pytest_paths':['tests/test_base.py','tests/test_securitypolicy.py'],
                    'source_workdir':'pyramid_multiauth'})
    for arm,version in [('vulnerable','1.8.10'),('first_fixed','1.8.11')]:
        out.append({'id':'pypiserver_'+arm,'project':'pypiserver/pypiserver',
                    'package':'webob','target_version':version,'arm':arm,
                    'install_type':'upstream_runtime_requirements_plus_selected_test_dependencies',
                    'packages':['defusedxml>=0.7.1','packaging>=26','pip>=26.0.1',
                                'pytest>=8,<10','pytest-cov>=6','webtest>=3.0.7',
                                'httpx>=0.28.1','passlib==1.7.4','setuptools>=64,<85',
                                'wheel>=0.25',f'webob=={version}'],
                    'test_type':'existing_repository_pytest',
                    'pytest_paths':['tests/test_config.py','tests/test_core.py','tests/test_app.py'],
                    'source_workdir':'pypiserver'})
    for arm,version in [('vulnerable','3.3.0'),('first_fixed','3.4.0'),
                        ('latest',PACKAGE_VERSIONS['python-jose'])]:
        out.append({'id':'python_jose_'+arm,'project':'mpdavis/python-jose',
                    'package':'python-jose','target_version':version,'arm':arm,
                    'install_type':'published_pypi_wheel_root_and_transitives',
                    'packages':[f'python-jose=={version}'],
                    'test_type':'researcher_package_smoke','test_python':JOSE_SMOKE,
                    'source_workdir':None})
    assert len(out)==10 and len({x['id'] for x in out})==10
    return out


def run_logged(case_id,stage,cmd,cwd=None,env=None,timeout=120):
    filename=LOGDIR/f'{case_id}__{stage}.log'
    started=time.monotonic()
    record={'argv':cmd,'cwd':str(cwd) if cwd else None,
            'env_overrides':{k:v for k,v in (env or {}).items()
                             if k in ('DEMO_MODE','PYTHONPATH','PYTHONDONTWRITEBYTECODE')},
            'timeout_seconds':timeout}
    try:
        p=subprocess.run(cmd,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                         text=True,encoding='utf-8',errors='replace',timeout=timeout)
        record.update({'exit_code':p.returncode,'status':'success' if p.returncode==0 else 'failed',
                       'seconds':round(time.monotonic()-started,3),
                       'stdout_sha256':sha(p.stdout.encode()),'stderr_sha256':sha(p.stderr.encode()),
                       'stdout_tail':p.stdout[-1400:],'stderr_tail':p.stderr[-1800:]})
        content=f'argv: {json.dumps(cmd)}\n\n[STDOUT]\n{p.stdout}\n\n[STDERR]\n{p.stderr}'
    except subprocess.TimeoutExpired as exc:
        record.update({'exit_code':None,'status':'timeout_unknown',
                       'seconds':round(time.monotonic()-started,3)})
        content=f'argv: {json.dumps(cmd)}\nTIMEOUT after {timeout}s\n'+str(exc)
    except OSError as exc:
        record.update({'exit_code':None,'status':'execution_error','error':str(exc)[:250],
                       'seconds':round(time.monotonic()-started,3)})
        content=f'argv: {json.dumps(cmd)}\nExecution error: {exc}\n'
    filename.write_text(content)
    record['log_path']=str(filename.relative_to(HERE))
    record['log_sha256']=sha(filename.read_bytes())
    return record


def one(case):
    cid=case['id']
    envdir=ENV_ROOT/cid
    envdir.parent.mkdir(parents=True,exist_ok=True)
    src=SOURCES/case['source_workdir'] if case.get('source_workdir') else HERE
    vpy=envdir/'bin/python'
    steps={}
    steps['venv']=run_logged(cid,'venv',[sys.executable,'-m','venv',str(envdir)],timeout=35)
    if steps['venv']['status']!='success':return {**case,'status':'venv_error','steps':steps}
    install_base=[str(vpy),'-m','pip','install','--no-input','--disable-pip-version-check',
                  '--only-binary=:all:','--progress-bar','off','--timeout','12',
                  '--retries','1','--index-url',PYPI]
    steps['pip_pin']=run_logged(cid,'pip_pin',install_base+['pip==26.2.2'],timeout=60)
    if steps['pip_pin']['status']!='success':return {**case,'status':'pip_bootstrap_error','steps':steps}
    args=(['-r',str(HERE/case['install_requirements_file'])] if case.get('install_requirements_file')
          else case['packages'])
    steps['install']=run_logged(cid,'install',install_base+args,timeout=120)
    if steps['install']['status']!='success':
        return {**case,'status':'dependency_install_failed_or_timeout','steps':steps}
    version_cmd=[str(vpy),'-c',f'import importlib.metadata as m; print(m.version({case["package"]!r}))']
    steps['installed_version']=run_logged(cid,'installed_version',version_cmd,timeout=15)
    if steps['installed_version']['status']!='success' or case['target_version'] not in steps['installed_version']['stdout_tail']:
        return {**case,'status':'wrong_target_version','steps':steps}
    test_env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1',
              'PIP_NO_INPUT':'1',
              'PYTHONPATH':str(src)+os.pathsep+str(src/'src')}
    test_env.update(case.get('env_overrides',{}))
    if case['test_type']=='existing_repository_pytest':
        test_cmd=[str(vpy),'-m','pytest','-q',*case['pytest_paths']]
    else:
        test_cmd=[str(vpy),'-c',case['test_python']]
    steps['test']=run_logged(cid,'test',test_cmd,cwd=src,env=test_env,timeout=120)
    output=steps['test'].get('stdout_tail','')+'\n'+steps['test'].get('stderr_tail','')
    steps['test']['pytest_summary_matches']=re.findall(r'\d+ (?:passed|failed|skipped|error|xfailed)',output)
    return {**case,'status':('installed_and_tests_passed' if steps['test']['status']=='success'
                              else 'installed_but_tests_not_passed'),
            'steps':steps}


def main():
    ENV_ROOT.mkdir(exist_ok=True);LOGDIR.mkdir(exist_ok=True)
    items=cases()
    (HERE/'install_test_manifest.json').write_text(json.dumps(items,indent=2,ensure_ascii=False))
    done={}
    if LOG.exists():
        for line in LOG.read_text().splitlines():
            try:r=json.loads(line);done[r['id']]=r
            except json.JSONDecodeError:continue
    pending=[x for x in items if x['id'] not in done]
    print('INSTALL TESTS',len(items),'completed',len(done),'new',len(pending),flush=True)
    with LOG.open('a') as f,ThreadPoolExecutor(max_workers=2) as exe:
        futs={exe.submit(one,c):c for c in pending}
        for task in as_completed(futs):
            c=futs[task]
            try:rec=task.result()
            except Exception as exc:rec={**c,'status':'runner_exception','error':repr(exc)}
            done[c['id']]=rec
            f.write(json.dumps(rec,ensure_ascii=False)+'\n');f.flush()
            print(len(done),'/',len(items),c['id'],rec['status'],flush=True)
    print('FINAL',dict(Counter(x['status'] for x in done.values())),flush=True)


if __name__=='__main__':main()
