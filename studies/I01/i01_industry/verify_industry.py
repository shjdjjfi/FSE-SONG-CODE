#!/usr/bin/env python3
"""Offline, non-mutating audit of the I01 public-consumer CPU follow-up.

Checks recorded evidence and byte digests, NOT CVE exploit efficacy.
The only write is industry_verification.json with audit outcomes.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT=Path(__file__).resolve().parent
ORIGINAL_ZIP_SHA='62950c93bbd3a830b9c05b6cf03857f48f0f3abb9e6fb6b8e149559abbc0b5e5'


def j(name):
    return json.loads((ROOT/name).read_text())


def rows(name):
    return [json.loads(line) for line in (ROOT/name).read_text().splitlines() if line.strip()]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def nested_snapshots(obj):
    if isinstance(obj,list):
        for value in obj:yield from nested_snapshots(value)
    elif isinstance(obj,dict):
        if {'path','sha256'} <= set(obj) and str(obj['path']).startswith('snapshots/'):
            yield obj
        for value in obj.values():yield from nested_snapshots(value)


def check_install_output(stage):
    path=ROOT/stage['log_path']
    if not path.is_file() or digest(path)!=stage['log_sha256']:
        return False
    if stage['status']=='timeout_unknown' or 'stdout_sha256' not in stage:
        return True
    content=path.read_text()
    part=content.partition('\n\n[STDOUT]\n')
    if not part[1]:return False
    out,sep,err=part[2].rpartition('\n\n[STDERR]\n')
    if not sep:return False
    return (hashlib.sha256(out.encode()).hexdigest()==stage['stdout_sha256'] and
            hashlib.sha256(err.encode()).hexdigest()==stage['stderr_sha256'])


def main():
    checks={}
    def ck(name,condition):checks[name]=bool(condition)

    source=j('source_manifest.json')
    snapshots=list(nested_snapshots(source))
    ck('exactly_seven_public_repo_manifest_entries',len(source['repositories'])==7)
    ck('all_pinned_repository_hashes',all(
        re.fullmatch(r'[0-9a-f]{40}',repo.get('commit',repo.get('current_commit','')))
        for repo in source['repositories'].values()))
    ck('all_OSV_PyPI_GitHub_snapshot_SHA256s',bool(snapshots) and all(
        (ROOT/x['path']).is_file() and digest(ROOT/x['path'])==x['sha256']
        and (x.get('bytes') is None or (ROOT/x['path']).stat().st_size==x['bytes'])
        for x in snapshots))
    ck('historical_pin_true_in_frozen_content',
       'python-jose==3.3.0' in (ROOT/'snapshots/github/pyfa/historical_requirements-requirements.txt').read_text()
       and 'python-jose==3.5.0' in (ROOT/'snapshots/github/pyfa/current_pyproject-pyproject.toml').read_text())

    manifest=j('consumer_probe_manifest.json')
    probes=rows('consumer_pip_audit.jsonl')
    mid={r['id']:r for r in manifest}
    byid={r['id']:r for r in probes}
    ck('23_unique_complete_declared_pip_probes',len(manifest)==len(probes)==len(mid)==len(byid)==23
       and set(mid)==set(byid)
       and Counter(x['scope'].startswith('entire_public') for x in manifest)=={True:15,False:8})
    ck('all_real_requirements_bytes_sha256',all(
        (ROOT/x['req_path']).is_file() and digest(ROOT/x['req_path'])==x['req_sha256']
        for x in probes))
    ck('pip_probe_metadata_matches_declared_plan',all(
        all(observed.get(k)==planned.get(k) for k in
            ('scope','repo_case','package','arm','req_path','req_sha256'))
        for key,observed in byid.items() for planned in [mid[key]]))
    ck('pip_14_success_9_failure',Counter(x['status'] for x in probes)==
       {'success':14,'unsat_or_no_wheel':9})
    pip_reports=[x for x in probes if x['status']=='success']
    def valid_pip_report(x):
        file=x.get('report_file')
        if not file or not (ROOT/file).is_file():return False
        record=json.loads((ROOT/file).read_text())
        if not isinstance(record.get('install'),list):return False
        names=[z.get('metadata',{}).get('name','').lower().replace('_','-')
               for z in record['install']]
        return x['package'].lower().replace('_','-') in names
    ck('all_14_successful_pip_reports_contain_target',len(pip_reports)==14 and
       all(valid_pip_report(x) for x in pip_reports))

    install_plan=j('install_test_manifest.json')
    install=rows('install_test_results.jsonl')
    testids={x['id'] for x in install}
    ck('10_unique_actual_isolated_install_tasks',len(install_plan)==len(install)==len(testids)==10
       and testids=={x['id'] for x in install_plan})
    ck('9_installed_and_tested_1_known_install_failure',
       Counter(x['status'] for x in install)==
       {'installed_and_tests_passed':9,'dependency_install_failed_or_timeout':1}
       and next(x['id'] for x in install if x['status']!='installed_and_tests_passed')=='ai_npc_latest')
    stages=[s for x in install for s in x.get('steps',{}).values()]
    ck('all_install_stage_raw_logs_and_stream_SHA256',bool(stages) and all(check_install_output(x) for x in stages))
    ck('real_repo_test_invocation_not_assumed',all(
        ('-m' in x['steps']['test']['argv'] and 'pytest' in x['steps']['test']['argv'])
        for x in install if x['test_type']=='existing_repository_pytest'))
    pytest_cases={x['id']:x for x in install if x['test_type']=='existing_repository_pytest'}
    ck('existing_Mozilla_pytest_43_each',all(
        name in pytest_cases and pytest_cases[name]['steps']['test']['exit_code']==0
        and '43 passed' in pytest_cases[name]['steps']['test']['pytest_summary_matches']
        for name in ('pyramid_multiauth_vulnerable','pyramid_multiauth_first_fixed')))
    ck('existing_pypiserver_pytest_316_each',all(
        name in pytest_cases and pytest_cases[name]['steps']['test']['exit_code']==0
        and '316 passed' in pytest_cases[name]['steps']['test']['pytest_summary_matches']
        for name in ('pypiserver_vulnerable','pypiserver_first_fixed')))
    ck('AI_NPC_real_project_test_client_smoke_passed',all(
        x['steps']['test']['exit_code']==0 and '/openapi.json' in x['test_python']
        and '/npc' in x['test_python'] and 'DEMO_MODE' in x['test_python']
        for x in install if x['id'] in ('ai_npc_vulnerable','ai_npc_first_fixed')))

    catalog=j('alternative_catalog_manifest.json')
    metadata=j('alternative_metadata.json')
    preflight=j('alternative_preflight_276.json')
    alt_runs=rows('alternative_uv.jsonl')
    alternative=j('alternative_results.json')
    fixed_versions={(item['project'],v) for item in catalog for v in item['versions']}
    additional={(item['project'],v) for item in catalog for v in item['versions'][1:]}
    ck('6_OSV_multi_fixed_projects_23_fixed_events_17_extra',
       len(catalog)==6 and len(fixed_versions)==23 and len(additional)==17)
    ck('23_frozen_versioned_PyPI_responses',len(metadata)==23 and
       {(x['project'],x['version']) for x in metadata}==fixed_versions and
       all((ROOT/x['raw_path']).is_file() and digest(ROOT/x['raw_path'])==x['raw_sha256']
           for x in metadata))
    ck('276_independently_recorded_preflight_results',len(preflight)==276)
    ck('204_unique_real_alternate_uv_solver_records',
       len(alt_runs)==len({r['case_id'] for r in alt_runs})==204 and
       Counter(r['status'] for r in alt_runs)=={'success':96,'unsat':108})
    ck('all_extra_version_platform_python_combinations',all(
        f'{project}=={version}|py{py}|{plat}' in {r['case_id'] for r in alt_runs}
        for project,version in additional
        for py in ('3.8','3.10','3.12','3.14')
        for plat in ('linux_amd64','windows_amd64','macos_arm64')))
    case_rows=alternative['cases']
    ck('72_unique_first_vs_any_cases',len(case_rows)==len({
        (r['project'],r['python'],r['platform']) for r in case_rows})==72)
    first=sum(r['first_uv_status']=='success' for r in case_rows)
    any_success=sum(r['any_uv_success'] for r in case_rows)
    first_root=sum(r['first_root_compatible'] for r in case_rows)
    any_root=sum(r['any_root_compatible'] for r in case_rows)
    logs={r['case_id']:r for r in alt_runs}
    ck('all_204_uv_outcomes_match_72_scenario_summaries',all(
        x['uv_status']==logs.get(f"{r['project']}=={x['version']}|py{r['python']}|{r['platform']}",{}).get('status')
        for r in case_rows for x in r['alternatives']))
    ck('zero_net_recovered_42_first_42_any',first==any_success==42
       and alternative['first_fixed_uv_success']==first
       and alternative['any_listed_fixed_uv_success']==any_success
       and alternative['additional_uv_resolvable_cells']==0)
    ck('zero_net_recovered_root_wheel_54',first_root==any_root==54
       and alternative['first_fixed_root_compatible']==first_root
       and alternative['any_listed_fixed_root_compatible']==any_root)

    vendor=j('vendor_backport_evidence.json')
    backports=vendor['positive_confirmed_vendor_backports']
    ck('two_official_distro_oldbase_backport_announcements',len(backports)==2
       and all('suse.com/support/update/announcement/' in x['vendor_advisory_url']
               and x['cve']=='CVE-2026-54770'
               and ('1.8.7-' in x['vendor_patched_binary_package'] or
                    '1.2.3-' in x['vendor_patched_binary_package'])
               for x in backports))
    ck('vendor_packages_explicitly_not_claimed_locally_tested',all(
       'no local' in x['claim_scope'].lower() for x in backports))

    ck('Chinese_report_exists',(ROOT/'I01_工业真实项目扩展实验报告.md').is_file())
    ck('two_evidence_figures_exist',all((ROOT/'figures'/f).is_file() for f in
       ('consumer_constraints_matrix.png','alternative_fix_recovery.png')))
    ck('narrative_summary_counts_match_records',j('industry_summary.json')['n_consumer_dryruns_total']==len(probes)
       and j('industry_summary.json')['n_install_test_environments']==len(install)
       and j('industry_summary.json')['alternatives']['extra_actual_uv_calls']==len(alt_runs))

    candidates=[ROOT.parent/'previous_offline_study.zip',
                ROOT.parent/'I01_FSE2027_Full_CPU_Experiment_20261114.zip']
    found=[p for p in candidates if p.is_file()]
    ck('original_120x12_artifact_immutable_SHA256',bool(found) and
       any(digest(p)==ORIGINAL_ZIP_SHA for p in found))
    # The signed-off previous study is independently verifiable once unpacked.
    if found:
        original=next((p for p in found if digest(p)==ORIGINAL_ZIP_SHA),None)
        if original:
            with zipfile.ZipFile(original) as archive:
                status=json.loads(archive.read(
                    'I01_FSE2027_Full_CPU_Experiment/verification_results.json'))
            ck('previous_offline_study_verified_all_pass',status['all_pass'] is True)

    result={'all_pass':all(checks.values()),'checked':len(checks),'checks':checks,
            'frozen_snapshots_checked':len(snapshots),
            'recorded_install_stages_verified':len(stages),
            'pipeline':'I01 actual-consumer CPU validation, 2026-11-14',
            'interpretation':'artifact integrity only; not independently re-run or vulnerability PoC'}
    (ROOT/'industry_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result['all_pass'] else 1


if __name__=='__main__':sys.exit(main())
