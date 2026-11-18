"""Version original immutable measurements and SHA256 the extended ZIP payload.

The v1 integrity record is preserved independently. We explicitly verify that
the previously frozen experimental *results*, figures, evidence and scripts
have not been altered; updated README/research narratives are versioned in v2.
"""

from __future__ import annotations
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import platform


ROOT=Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    old_path=ROOT/"results/provenance_v1.json"
    if not old_path.exists():raise FileNotFoundError("Preserve original results/provenance.json as provenance_v1.json first")
    old=json.loads(old_path.read_text())
    immutable_prefixes=("results/","figures/","evidence/","src/","tests/")
    immutable_checked=[]
    for relative,expected in old.get("bundle_sha256",{}).items():
        if relative.startswith(immutable_prefixes):
            current=ROOT/relative
            if not current.is_file() or sha(current)!=expected:
                raise AssertionError(f"Original empirical measurement/script changed: {relative}")
            immutable_checked.append(relative)
    independent=json.loads((ROOT/"results/independent_refactoring_oracle.json").read_text())
    paths=[]
    for folder in ("src","tests","evidence","results","figures"):
        paths.extend(p for p in (ROOT/folder).rglob("*") if p.is_file() and
                     "__pycache__" not in p.parts and p.suffix not in (".pyc",".tmp"))
    paths.extend(p for p in ROOT.iterdir() if p.is_file() and p.suffix in (".md",".txt"))
    paths.append(ROOT/"requirements.txt")
    paths=[p for p in set(paths) if p.relative_to(ROOT).as_posix()!="results/provenance.json"]
    digest={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(paths)}
    metadata={"snapshot_semantics":"Extended N04 results v2; provenance_v1.json is original immutable baseline",
              "generated_utc":datetime.now(timezone.utc).isoformat(),
              "python":platform.python_version(),
              "original_measurements_verified_unchanged":len(immutable_checked),
              "previous_toolchain":old.get("toolchain"),
              "previous_repository_heads":old.get("repository_heads"),
              "previous_ftw_downloaded_archive":old.get("ftw_downloaded_archive"),
              "independent_refactoring_oracle_head":independent["oracle_git_head"],
              "source_commit_pins":{"fusion_quarantine_split":"b5450832494d24e4171acea606b4c022a5a8475b",
                                    "riptide_label_conflict":"cef45a1e325b5b1fdc4c47def3269ad3578b1fe1"},
              "real_github_action_ids":[28697507894,28720367126],
              "not_established":["production N04 benefit","causal CI cost reduction",
                                 "2-percent false inheritance certification"],
              "bundle_sha256":digest}
    out=ROOT/"results/provenance.json"
    out.write_text(json.dumps(metadata,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(f"Recorded {len(digest)} file checksums; verified {len(immutable_checked)} frozen empirical files")


if __name__=="__main__":main()
