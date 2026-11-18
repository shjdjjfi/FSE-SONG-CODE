#!/usr/bin/env python3
"""Build tamper-evident archive file inventory, excluding downloaded binaries."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/"phase2/results/reproducibility_manifest.json"


def included(p:Path)->bool:
    rel=p.relative_to(ROOT)
    parts=rel.parts
    return ("toolchain" not in parts and "__pycache__" not in parts
            and ".venv" not in parts and p.suffix not in (".pyc",)
            and p!=OUT and p.is_file())


def main():
    files=[]
    for p in sorted(ROOT.rglob("*")):
        if included(p):
            files.append({"path":p.relative_to(ROOT).as_posix(),
                          "size_bytes":p.stat().st_size,
                          "sha256":hashlib.sha256(p.read_bytes()).hexdigest()})
    OUT.write_text(json.dumps({"name":"N02 CPU reproducibility manifest",
                               "excluded":"toolchain downloaded binaries/caches; this manifest file",
                               "file_count":len(files),"files":files},indent=2))
    print(f"Manifested {len(files)} files ({sum(x['size_bytes'] for x in files)} bytes)")

if __name__=="__main__":
    main()
