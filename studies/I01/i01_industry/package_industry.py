#!/usr/bin/env python3
"""Make an auditable CPU-only industry follow-up artifact, preserving the baseline ZIP."""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path
import zipfile

HERE=Path(__file__).resolve().parent
TASK=HERE.parent
ORIGINAL=TASK/'I01_FSE2027_Full_CPU_Experiment_20261114.zip'
OUT=TASK/'I01_FSE2027_Industry_Extended_CPU_20261114.zip'
EXPECTED_ORIGINAL_SHA='62950c93bbd3a830b9c05b6cf03857f48f0f3abb9e6fb6b8e149559abbc0b5e5'
ROOT='I01_FSE2027_Industry_Extension'
DATE=(2026,11,14,0,0,0)
DENY_DIR={'sources','venvs','__pycache__','.git','uv_cache','.pytest_cache','.mypy_cache'}
DENY_SUFFIX={'.pyc','.pyo'}


def sha(data):return hashlib.sha256(data).hexdigest()


def file_entry(path,logical):
    data=path.read_bytes()
    return {'path':logical,'bytes':len(data),'sha256':sha(data)}


def add_bytes(archive,name,data,stored=False):
    meta=zipfile.ZipInfo(name,DATE)
    meta.create_system=3
    meta.external_attr=0o644<<16
    meta.compress_type=zipfile.ZIP_STORED if stored else zipfile.ZIP_DEFLATED
    archive.writestr(meta,data,compress_type=meta.compress_type,compresslevel=None if stored else 6)


def main():
    assert ORIGINAL.is_file(),ORIGINAL
    assert sha(ORIGINAL.read_bytes())==EXPECTED_ORIGINAL_SHA,'original baseline artifact unexpectedly changed'
    checked=json.loads((HERE/'industry_verification.json').read_text())
    assert checked['all_pass'] and checked['checked']>=30,'run verify_industry.py first'

    new_files=[]
    for path in sorted(HERE.rglob('*')):
        if not path.is_file() or any(part in DENY_DIR for part in path.relative_to(HERE).parts):
            continue
        if path.suffix in DENY_SUFFIX or path.is_symlink():continue
        if path.name.startswith('._'):continue
        new_files.append((path,('i01_industry/'+path.relative_to(HERE).as_posix())))

    entry_list=[file_entry(p,name) for p,name in new_files]
    entry_list.append(file_entry(ORIGINAL,'previous_offline_study.zip'))
    manifest={
        'artifact':'The Patchability Cliff: actual public consumer constraints, CPU installs and vendor backports',
        'date':'2026-11-14',
        'original_study_sha256':EXPECTED_ORIGINAL_SHA,
        'record_count':{'public_git_repositories':7,'pip_dryruns':23,
                        'isolated_install_test_conditions':10,'additional_uv_full_resolution':204,
                        'verified_data_checks':checked['checked']},
        'included_files':entry_list,
        'excluded':'public Git clones, isolated venvs, caches and secrets; fully recreatable with scripts',
    }
    top_readme=(
        '# The Patchability Cliff — FSE 2027 Industry CPU experimental artifact\n\n'
        '本 ZIP 同时包含原样保留的 1,440 场景基线研究包、七个真实开源仓库的依赖约束研究、'
        '真实 CPU 安装和源仓库选定单测、204 次多修复分支 uv 求解、两项 SUSE 官方 backport 证据。\n\n'
        '先读 `i01_industry/README.md` 与 `i01_industry/I01_工业真实项目扩展实验报告.md`。\n\n'
        '在解压目录运行 `python3 i01_industry/verify_industry.py`，不需要 GPU、联网或安装环境。\n'
        '研究 **不声称** 完整生产服务 CI、零漏洞扫描或 SUSE RPM 实装。\n'
    ).encode()
    with zipfile.ZipFile(OUT,'w',allowZip64=True) as archive:
        add_bytes(archive,f'{ROOT}/README.md',top_readme)
        for (path,logical),entry in zip(new_files,entry_list):
            content=path.read_bytes()
            assert sha(content)==entry['sha256']
            add_bytes(archive,f'{ROOT}/{logical}',content)
        add_bytes(archive,f'{ROOT}/previous_offline_study.zip',ORIGINAL.read_bytes(),stored=True)
        add_bytes(archive,f'{ROOT}/ZIP_CONTENT_MANIFEST.json',json.dumps(
            manifest,ensure_ascii=False,indent=2).encode())
    with zipfile.ZipFile(OUT) as archive:
        assert archive.testzip() is None,'zip CRC corruption'
        saved=json.loads(archive.read(f'{ROOT}/ZIP_CONTENT_MANIFEST.json'))
        for entry in saved['included_files']:
            member=archive.read(f"{ROOT}/{entry['path']}")
            assert len(member)==entry['bytes'] and sha(member)==entry['sha256'],entry['path']
    print(json.dumps({'zip':str(OUT),'size_bytes':OUT.stat().st_size,
          'sha256':sha(OUT.read_bytes()),'files':len(entry_list)+2,
          'previous_study_preserved':True,'zip_members_CRC_verified':True},
          ensure_ascii=False,indent=2))


if __name__=='__main__':main()
