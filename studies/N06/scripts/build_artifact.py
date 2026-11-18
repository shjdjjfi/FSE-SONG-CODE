"""Build the complete, self-contained N06 experiment ZIP with SHA audit."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys
import zipfile

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT.parent / "N06_FSE2027_Experiments.zip"
PREFIX = "N06_FSE2027_Experiments"
INCLUDE = ("README.md", "requirements.txt", "sources", "src", "scripts", "tests",
           "promtool", "paper", "results_v2", "exploratory_holdout",
           "field_capture", "results_field", ".github")


def files_to_pack() -> list[Path]:
    paths = []
    for item in INCLUDE:
        path = ROOT / item
        if not path.exists():
            raise FileNotFoundError(path)
        if path.is_file():
            paths.append(path)
        else:
            paths.extend(x for x in path.rglob("*") if x.is_file())
    return sorted((p for p in paths if p.suffix != ".pyc" and
                   "__pycache__" not in p.parts), key=lambda p: str(p.relative_to(ROOT)))


def build() -> Path:
    inputs = files_to_pack()
    hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in inputs}
    audit = {
        "purpose": "N06 synthetic mechanism benchmark, field capture toolkit, and fail-closed non-submission-readiness audit",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version.split()[0],
        "system": platform.platform(),
        "count_files_without_self_manifest": len(inputs),
        "files_sha256": hashes,
    }
    manifest = ROOT / "MANIFEST_SHA256.json"
    manifest.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    inputs.append(manifest)
    with zipfile.ZipFile(DEST, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9, strict_timestamps=False) as handle:
        for path in inputs:
            arcname = PREFIX + "/" + str(path.relative_to(ROOT)).replace("\\", "/")
            handle.write(path, arcname=arcname)
    with zipfile.ZipFile(DEST) as handle:
        assert handle.testzip() is None
        assert len(handle.namelist()) == len(inputs)
    print(f"PASS: {DEST.name}, {len(inputs)} files, {DEST.stat().st_size} bytes")
    return DEST


if __name__ == "__main__":
    build()
