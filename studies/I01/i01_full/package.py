#!/usr/bin/env python3
"""Create a complete, verified, deterministic research ZIP (no GPU caches)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parent
ARCHIVE=ROOT.parent/'I01_FSE2027_Full_CPU_Experiment_20261114.zip'
PREFIX='I01_FSE2027_Full_CPU_Experiment'


def include(p):
    relative=p.relative_to(ROOT)
    return (p.is_file() and p.name!='ARTIFACT_MANIFEST.json' and 'uv_cache' not in relative.parts
            and '__pycache__' not in relative.parts and p.suffix!='.pyc'
            and 'uv_full.partial' not in p.name)


def main():
    audit=json.loads((ROOT/'verification_results.json').read_text())
    if not audit.get('all_pass'):
        raise SystemExit('The complete experiment must pass verify.py before packaging')
    source_files=sorted((p for p in ROOT.rglob('*') if include(p)),key=lambda p:str(p.relative_to(ROOT)))
    manifest={}
    for p in source_files:
        rel=p.relative_to(ROOT).as_posix()
        b=p.read_bytes()
        manifest[rel]={'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
    manifest_path=ROOT/'ARTIFACT_MANIFEST.json'
    manifest_path.write_text(json.dumps({'created_date':'2026-11-14',
                                         'files':manifest},indent=2,ensure_ascii=False))
    source_files.append(manifest_path)
    with zipfile.ZipFile(ARCHIVE,'w',allowZip64=True) as z:
        for p in sorted(source_files,key=lambda p:str(p.relative_to(ROOT))):
            archive_name=f'{PREFIX}/{p.relative_to(ROOT).as_posix()}'
            stat=p.stat()
            info=zipfile.ZipInfo(archive_name,date_time=(2026,11,14,0,0,0))
            info.external_attr=(0o644<<16)
            info.compress_type=(zipfile.ZIP_STORED if p.suffix=='.zip' else zipfile.ZIP_DEFLATED)
            with p.open('rb') as r,z.open(info,'w') as w:
                while True:
                    chunk=r.read(1024*1024)
                    if not chunk:break
                    w.write(chunk)
    with zipfile.ZipFile(ARCHIVE) as z:
        assert z.testzip() is None
        assert len(z.namelist())==len(source_files)
    print('ARTIFACT',ARCHIVE,'BYTES',ARCHIVE.stat().st_size,
          'SHA256',hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(),
          'FILES',len(source_files))


if __name__=='__main__':main()
