#!/usr/bin/env python3
"""Produce source-linked, reviewable feature-mismatch witness cards.

This is *not* human annotation and never asserts that a rendered docs.rs page
omits an annotation. It preserves exactly the surrounding authored source and
feature configuration needed for a later blinded manual audit.
"""
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RESULTS = ROOT / "results"


def main():
    meta = {m["crate"]: m for m in json.loads((DATA / "crates_manifest.json").read_text())}
    corpus = {r["id"]: r for r in map(json.loads, (DATA / "corpus.jsonl").read_text().splitlines())}
    screen = [json.loads(s) for s in (RESULTS / "screen.jsonl").read_text().splitlines()]
    archive_cache = {}
    rows = []
    for s in screen:
        if s["label"] != "eligible_mismatch":
            continue
        r = corpus[s["id"]]
        m = meta[r["crate"]]
        name = f'{r["crate"]}-{r["version"]}'
        if name not in archive_cache:
            tar_path = DATA / "crates" / (name + ".crate")
            assert hashlib.sha256(tar_path.read_bytes()).hexdigest() == m["archive_sha256"]
            with tarfile.open(tar_path, "r:gz") as f:
                src = {}
                for e in f.getmembers():
                    if not e.isfile():
                        continue
                    path = e.name.split("/", 1)[-1]
                    if path.endswith(".rs") or path.lower().endswith("readme.md"):
                        if e.size < 600_000:
                            try:
                                src[path] = f.extractfile(e).read().decode()
                            except UnicodeDecodeError:
                                pass
                archive_cache[name] = src
        source = archive_cache[name].get(r["source"], "")
        lines = source.splitlines()
        lineno = r["line"]
        surrounding = "\n".join(f"{i + 1}: {lines[i]}" for i in range(max(0, lineno - 31), min(len(lines), lineno + 10)))
        # These are separate *possible* explanatory notices, not equivalent
        # to a validated per-example feature disclosure in rendered rustdoc.
        explicit_nearby = bool(re.search(r"feature[s]?(?:\s+flag)?\s*[:=]|(?:--features|features\s*=)",
                                          surrounding, re.I))
        visible_has_cfg = bool(re.search(r"cfg\s*\(\s*feature\s*=", r["compiled_code"]))
        rows.append({
            "id": r["id"], "crate": r["crate"], "version": r["version"],
            "path": r["source"], "line": lineno, "source_url":
                f'https://docs.rs/crate/{r["crate"]}/{r["version"]}/source/{r["source"]}',
            "archive_sha256": m["archive_sha256"], "docs_rs_metadata": m["docs_metadata"],
            "candidate_feature_names": m["feature_names"],
            "nearby_source_mentions_feature_config": explicit_nearby,
            "rustdoc_hidden_cfg_condition": visible_has_cfg,
            "context_source": surrounding,
            "compiled_rustdoc_example": r["compiled_code"],
            "visible_rustdoc_example": r["visible_code"],
            "manual_annotation_status": "NOT_REVIEWED",
        })
    (RESULTS / "witness_audit.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n")
    print(f"Source-linked {len(rows)} feature-gap witnesses; none marked human-validated.")


if __name__ == "__main__":
    main()
