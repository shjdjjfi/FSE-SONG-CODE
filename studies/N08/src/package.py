#!/usr/bin/env python3
"""Build an independently verifiable ZIP of the finished N08 research bundle."""

import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT.parent / "FSE2027_N08_Experimental_Evidence.zip"
MANIFEST = ROOT / "results" / "FILE_MANIFEST.json"


def include(path):
    return not any(x == '__pycache__' for x in path.parts) and path.suffix not in ('.pyc', '.tmp')


def main():
    source_paths = sorted(p for p in ROOT.rglob('*') if p.is_file() and p != MANIFEST and include(p))
    entries = []
    for f in source_paths:
        buf = f.read_bytes()
        entries.append({'path': str(f.relative_to(ROOT)), 'bytes': len(buf),
                        'sha256': hashlib.sha256(buf).hexdigest()})
    MANIFEST.write_text(json.dumps({'schema': 1, 'paths': entries}, indent=2) + '\n', encoding='utf-8')
    paths = [*source_paths, MANIFEST]
    with zipfile.ZipFile(DEST, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=8) as z:
        for f in paths:
            z.write(f, arcname=str(Path(ROOT.name) / f.relative_to(ROOT)))
    digest = hashlib.sha256(DEST.read_bytes()).hexdigest()
    with zipfile.ZipFile(DEST) as z:
        fail = z.testzip()
        assert not fail, fail
        count = len(z.namelist())
    print(f"ZIP: {DEST}\nFiles: {count}\nBytes: {DEST.stat().st_size}\nSHA256: {digest}")


if __name__ == '__main__':
    main()
