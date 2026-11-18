#!/usr/bin/env python3
"""Independent local audit of original corpus, sample, JSONL and API hashes."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent
EXPECTED_OSV='305dbca79abb7dc1bf52c8466c1be9e7c134b25ec67975c2d395f5259041d22e'


def load_json(filename):
    return json.loads((ROOT/filename).read_text())


def load_log(filename):
    p=ROOT/filename
    if not p.exists():return []
    return [json.loads(line) for line in p.read_text().splitlines()]


def main():
    sample=load_json('osv_sample120.json')
    metadata=load_json('metadata_index.json')
    cases=load_json('all_1440_cases.json')
    oracle=load_log('uv_full.jsonl')
    macos=load_log('uv_macos11.jsonl')
    holdout=load_json('pip_validation_ids.json')
    secondary=load_log('pip_validation.jsonl')
    allpip=load_log('pip_all.jsonl')
    results={}
    def check(name,value):results[name]=bool(value)

    osv_digest=hashlib.sha256((ROOT/'raw/osv-pypi-20261114.zip').read_bytes()).hexdigest()
    check('osv_snapshot_sha256_valid',osv_digest==EXPECTED_OSV)
    check('sample_has_120_unique_projects',len(sample)==120 and len({s['project'] for s in sample})==120)
    check('balanced_year_strata',Counter(s['stratum'] for s in sample)=={'early':40,'middle':40,'recent':40})
    check('one_pypi_metadata_per_project',len(metadata)==120 and
          {s['project'] for s in sample}=={s['project'] for s in metadata})
    hashes_good=True
    raw_good=0
    for item in metadata:
        if item['status']=='ok':
            p=ROOT/item['raw_response_path']
            if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=item['response_sha256']:
                hashes_good=False
            else:raw_good+=1
    check('all_available_pypi_response_hashes_match',hashes_good and raw_good>0)
    check('all_1440_conditions_unique',len(cases)==1440 and
          len({x['case_id'] for x in cases})==1440)
    check('complete_primary_uv_results',len(oracle)==1440 and
          {x['case_id'] for x in cases}=={x['case_id'] for x in oracle})
    check('complete_macos11_correction',len(macos)==480 and
          len({x['case_id'] for x in macos})==480 and
          all('|macos_arm64' in x['case_id'] for x in macos))
    check('complete_288_pip_validation',len(holdout)==len(secondary)==288 and
          set(holdout)=={x['case_id'] for x in secondary})
    bycase={x['case_id']:x for x in cases}
    holdout_cells=Counter((bycase[k]['stratum'],bycase[k]['python'],bycase[k]['platform'])
                          for k in holdout if k in bycase)
    check('pip_holdout_eight_per_each_of_36_cells',len(holdout_cells)==36 and
          all(v==8 for v in holdout_cells.values()))
    check('complete_1440_strict_pip_audit',len(allpip)==1440 and
          {x['case_id'] for x in cases}=={x['case_id'] for x in allpip})
    check('all_120_fixed_advisories_have_source_ids',all(s.get('osv_id') and s.get('fixed_version') for s in sample))
    check('analysis_results_exists',(ROOT/'analysis_results.json').is_file())
    check('figures_exist',all((ROOT/'figures'/f).is_file() for f in
                              ['full_resolution_heatmap.png','preflight_diagnostics.png',
                               'uv_relaxed_resolution_heatmap.png','resolver_disagreement_heatmap.png',
                               'study_flow.png']))
    check('full_report_exists',(ROOT/'I01_完整实验报告.md').is_file())
    summary={'all_pass':all(results.values()),'checks':results,
             'osv_sha256':osv_digest,'pypi_verified_response_files':raw_good,
             'uv_first_pass_records':len(oracle),'macos_corrective_records':len(macos),
             'pip_validation_records':len(secondary),'pip_full_audit_records':len(allpip)}
    (ROOT/'verification_results.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False))
    print(json.dumps(summary,indent=2,ensure_ascii=False))
    sys.exit(0 if summary['all_pass'] else 1)


if __name__=='__main__':main()
