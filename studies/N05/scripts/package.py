#!/usr/bin/env python3
"""Build and byte-verify the complete N05 reproducibility ZIP."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / "N05_FSE2027_Experiments_And_Evidence.zip"
IGNORE = {"work", "results_v1_superseded", "__pycache__", ".pytest_cache"}


def main():
    files = []
    for file in sorted(ROOT.rglob("*")):
        if (not file.is_file() or IGNORE.intersection(file.relative_to(ROOT).parts)
                or file.name == "REPRODUCIBILITY_MANIFEST.json"):
            continue
        files.append(file)
    ledger = []
    with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6,
                         allowZip64=True) as z:
        for path in files:
            name = "n05_experiment/" + path.relative_to(ROOT).as_posix()
            data = path.read_bytes()
            ledger.append({"path": name, "sha256": hashlib.sha256(data).hexdigest(),
                           "bytes": len(data)})
            z.writestr(name, data)
        # Keep the original fixed screening question alongside the new results.
        proposal = ROOT.parent / "screening" / "ideas" / "N05" / "proposal.md"
        if proposal.exists() and not (ROOT / "ORIGINAL_N05_PROPOSAL.md").exists():
            content = proposal.read_bytes()
            dest = "n05_experiment/ORIGINAL_N05_PROPOSAL.md"
            z.writestr(dest, content)
            ledger.append({"path": dest, "sha256": hashlib.sha256(content).hexdigest(),
                           "bytes": len(content)})
        z.writestr("n05_experiment/REPRODUCIBILITY_MANIFEST.json",
                   json.dumps({"schema_version": 1, "files": ledger}, indent=2) + "\n")
    with zipfile.ZipFile(OUT, "r") as z:
        fault = z.testzip()
        if fault is not None:
            raise RuntimeError(f"Corrupt ZIP member: {fault}")
        for item in ledger:
            if hashlib.sha256(z.read(item["path"])).hexdigest() != item["sha256"]:
                raise RuntimeError(f"SHA-256 mismatch: {item['path']}")
    print(json.dumps({"zip": str(OUT), "files": len(ledger) + 1,
                      "bytes": OUT.stat().st_size,
                      "sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
                      "verification": "ZIP CRC + every member SHA-256 passed"}, indent=2))


if __name__ == "__main__":
    main()
