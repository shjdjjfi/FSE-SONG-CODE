#!/usr/bin/env python3
"""Create a compact, hashed replication ZIP, excluding regenerated 180MB trees."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

from run_n21 import HERE


def main() -> None:
    root = HERE.parent
    validation = json.loads((HERE / "results" / "VALIDATION_REPORT.json").read_text())
    if not validation.get("internal_checks_passed") or validation["observed_trials"] != 920:
        raise RuntimeError("Refusing release until full experiment grid validates")
    files: dict[str, Path] = {}
    for pattern in ("*.py", "*.cjs", "*.sh", "*.md"):
        for p in HERE.glob(pattern):
            files[p.name] = p
    for p in (HERE / "figures").glob("*.svg"):
        files[f"figures/{p.name}"] = p
    for p in (HERE / "github_actions").rglob("*"):
        if p.is_file() and "__pycache__" not in p.parts:
            files[p.relative_to(HERE).as_posix()] = p
    for p in (HERE / "results").rglob("*"):
        if p.is_file() and "active_trial" not in p.relative_to(HERE / "results").parts:
            files[p.relative_to(HERE).as_posix()] = p
    for p in (HERE / "runtime" / "metadata").glob("*.json"):
        files[f"metadata/{p.name}"] = p
    files["metadata/environment.json"] = HERE / "runtime" / "environment.json"

    prior = root / "fse_n21_work"
    for arcname, rel in {
        "prior_work/FINAL_4_IDEAS.md": "FINAL_4_IDEAS.md",
        "prior_work/N21_original.md": "ideas/N21.md",
        "prior_work/N21_original_experiment.py": "code/N21/experiment.py",
        "prior_work/N21_preregistered_review.md": "preregistration/N21-review.md",
        "prior_work/N21_novelty.md": "preregistration/N21-novelty.md",
        "prior_work/N21_dedup.md": "preregistration/N21-dedup.md",
        "prior_work/original_experiment_results.json": "EXPERIMENT_RESULTS.json",
        "prior_work/original_wireit_observations.json": "pilot/wireit-observations.json",
    }.items():
        path = prior / rel
        if not path.is_file():
            raise FileNotFoundError(path)
        files[arcname] = path
    files["quarantined/typescript_before_buildinfo_filter.jsonl"] = (
        HERE / "runtime" / "invalidated_results" / "typescript_before_buildinfo_filter" / "trials.jsonl")

    artifact = root / "N21_FSE2027_Industry_Experiments.zip"
    prefix = "N21_FSE2027_Industry_Experiments"
    hashes = []
    with ZipFile(artifact, "w", compression=ZIP_DEFLATED, compresslevel=9) as z:
        for rel, path in sorted(files.items()):
            if not path.is_file():
                raise FileNotFoundError(path)
            data = path.read_bytes()
            hashes.append(f"{hashlib.sha256(data).hexdigest()}  {rel}")
            info = ZipInfo(f"{prefix}/{rel}", date_time=(2026, 11, 18, 12, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = (0o100644 << 16)
            z.writestr(info, data, compress_type=ZIP_DEFLATED, compresslevel=9)
        info = ZipInfo(f"{prefix}/MANIFEST.sha256", date_time=(2026, 11, 18, 12, 0, 0))
        info.compress_type = ZIP_DEFLATED
        z.writestr(info, "\n".join(hashes) + "\n")
    print(json.dumps({"path": str(artifact), "files": len(files) + 1,
                      "bytes": artifact.stat().st_size,
                      "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest()}, indent=2))


if __name__ == "__main__":
    main()
