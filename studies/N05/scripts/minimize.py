#!/usr/bin/env python3
"""Post-discovery independent Cargo checks for subset-minimal fixes.

These checks are *outside* the eight-check comparison budget; report their
cost separately. "Minimal" means no feature can be dropped from the found
set, never a claim of global cardinality minimality without enumeration.
"""
import argparse
import itertools
import json
from pathlib import Path

from replay import read_jsonl, run_check

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RESULTS = ROOT / "results"


def feature_closure(meta, requested):
    mapping = meta["feature_map"]
    known = set(mapping)
    visited = set()
    queue = list(requested) + list(meta["default_features"])
    while queue:
        feat = queue.pop()
        if feat in visited:
            continue
        visited.add(feat)
        for tok in mapping.get(feat, []):
            if tok in known:
                queue.append(tok)
    return sorted(visited)


def minimal(meta, row, found):
    current = list(found)
    checks = []
    # Fixed lexicographic removal order to avoid researcher discretion.
    for item in sorted(found):
        if item not in current:
            continue
        smaller = sorted(x for x in current if x != item)
        result = run_check(meta, row, "candidate", smaller)
        checks.append({"removed": item, "test_set": smaller,
                       "status": result["status"], "check": result["key"]})
        if result["status"] == "pass":
            current = smaller
    # Certify against any single deletion in the final set, in case the
    # previous reductions changed which original deletions should be tried.
    for item in current:
        smaller = sorted(x for x in current if x != item)
        if any(c["test_set"] == smaller and c["status"] == "fail" for c in checks):
            continue
        result = run_check(meta, row, "candidate", smaller)
        checks.append({"removed": item, "test_set": smaller,
                       "status": result["status"], "check": result["key"]})
    verified = all(any(c["test_set"] == sorted(x for x in current if x != item)
                       and c["status"] == "fail" for c in checks) for item in current)
    return current, checks, verified


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    metas = {x["crate"]: x for x in json.loads((DATA / "crates_manifest.json").read_text())}
    corpus = {x["id"]: x for x in read_jsonl(DATA / "corpus.jsonl")}
    searched = [x for x in read_jsonl(RESULTS / "search.jsonl") if x["guided"]["pass"]]
    existing = {x["id"]: x for x in read_jsonl(RESULTS / "minimized.jsonl")}
    if args.limit:
        searched = searched[:args.limit]
    for i, s in enumerate(searched, 1):
        if s["id"] in existing:
            continue
        m, row = metas[s["crate"]], corpus[s["id"]]
        direct, checks, confirmed = minimal(m, row, s["guided"]["features"])
        existing[s["id"]] = {
            "id": s["id"], "crate": s["crate"],
            "initial_feature_set": s["guided"]["features"],
            "subset_minimal_feature_set": direct,
            "subset_minimal_certified": confirmed,
            # For a one-flag fix, default (zero extra flags) already failed.
            # Thus exactly one requested flag is trivially cardinality-minimal.
            # This says nothing about the size of its transitive feature closure.
            "globally_minimal_certified": bool(confirmed and len(direct) == 1),
            "local_feature_closure": feature_closure(m, direct),
            "post_discovery_checks": checks,
        }
        (RESULTS / "minimized.jsonl").write_text("".join(json.dumps(r) + "\n" for r in existing.values()))
        print(f"[{i}/{len(searched)}] {s['crate']} {s['id']}: {direct}, "
              f"subset-minimal={confirmed}, checks={len(checks)}", flush=True)
    for rec in existing.values():
        rec["globally_minimal_certified"] = bool(rec["subset_minimal_certified"] and len(rec["subset_minimal_feature_set"]) == 1)
    (RESULTS / "minimized.jsonl").write_text("".join(json.dumps(r) + "\n" for r in existing.values()))


if __name__ == "__main__":
    main()
