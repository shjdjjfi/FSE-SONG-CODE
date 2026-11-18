#!/usr/bin/env python3
"""Preserve Cargo dependency lockfiles from all public-release replays."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def main():
    for name in ("prospective", "holdout"):
        base = ROOT / name
        if not (base / "data/crates_manifest.json").exists():
            continue
        meta = json.loads((base / "data/crates_manifest.json").read_text())
        out = base / "data/locks"
        out.mkdir(parents=True, exist_ok=True)
        records = []
        for row in meta:
            crate = row["crate"]
            source = ROOT / "work/consumers" / crate / "Cargo.lock"
            dest = out / f"{crate}.lock"
            if not source.exists():
                if dest.exists():
                    records.append({"crate": crate, "status": "already_frozen",
                                    "sha256": hashlib.sha256(dest.read_bytes()).hexdigest()})
                else:
                    records.append({"crate": crate, "status": "missing"})
                continue
            shutil.copyfile(source, dest)
            records.append({"crate": crate, "status": "frozen",
                            "sha256": hashlib.sha256(dest.read_bytes()).hexdigest()})
        (out / "checksums.json").write_text(json.dumps(records, indent=2) + "\n")
        print(f"{name}: available {sum(x['status']!='missing' for x in records)}/{len(records)} Cargo lockfiles")


if __name__ == "__main__":
    main()
