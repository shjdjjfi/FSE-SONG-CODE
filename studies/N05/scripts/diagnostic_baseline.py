#!/usr/bin/env python3
"""Strong baseline: actionable Cargo feature flags suggested by rustc errors.

Only consumes the default-profile compiler diagnostic that both methods have
already paid for; no human rules, future outcomes or target-label leakage.
"""
import argparse
import json
from pathlib import Path
import re

import replay

ROOT = Path(__file__).resolve().parents[1]
FEATURE_HINTS = (
    re.compile(r'\bgated behind the [`\x27]([a-zA-Z0-9_-]+)[`\x27] feature', re.I),
    re.compile(r'#\s*\[\s*cfg\s*\(\s*feature\s*=\s*"([a-zA-Z0-9_-]+)"\s*\)\s*\]', re.I),
    re.compile(r'\brequires? the [`\x27]([a-zA-Z0-9_-]+)[`\x27] feature', re.I),
)


def compiler_feature_hints(check, meta):
    allowed = set(meta["feature_names"]) - {"default"}
    # Keep the exact diagnostic source/target association. No docs-profile
    # compiler output or successful result is inspected here.
    rendered = "\n".join(x.get("rendered", "") for x in check.get("errors", []))
    matches = []
    for pattern in FEATURE_HINTS:
        for match in pattern.finditer(rendered):
            f = match.group(1)
            if f in allowed and f not in matches:
                matches.append(f)
    return matches


def evaluate(cohort):
    data = cohort / "data"
    results = cohort / "results"
    replay.DATA = data
    replay.RESULTS = results
    replay.WORK = ROOT / "work"
    metas = {m["crate"]: m for m in json.loads((data / "crates_manifest.json").read_text())}
    corpus = {r["id"]: r for r in replay.read_jsonl(data / "corpus.jsonl")}
    positives = [x for x in replay.read_jsonl(results / "screen.jsonl") if x["label"] == "eligible_mismatch"]
    prev = {x["id"]: x for x in replay.read_jsonl(results / "diagnostic.jsonl")}
    for i, screen in enumerate(positives, 1):
        if screen["id"] in prev:
            continue
        meta = metas[screen["crate"]]
        row = corpus[screen["id"]]
        check = json.loads((results / "checks" / (screen["default"] + ".json")).read_text())
        hints = compiler_feature_hints(check, meta)
        # Intentionally *no use* of the proposed lexical heuristic. The
        # obvious comparator is native diagnostics with alphabetic fallback.
        alphabetic = sorted(f for f in meta["feature_names"] if f != "default" and not f.startswith("_"))
        combined = hints + [x for x in alphabetic if x not in hints]
        outcome = replay.evaluate_sequence(meta, row, combined)
        rec = {"id": screen["id"], "crate": screen["crate"],
               "default_diagnostic_check": screen["default"],
               "compiler_only_hints": hints,
               "compiler_hints_found": bool(hints),
               "strong_baseline": outcome}
        prev[screen["id"]] = rec
        (results / "diagnostic.jsonl").write_text("".join(json.dumps(r) + "\n" for r in prev.values()))
        print(f"[{i}/{len(positives)}] {screen['crate']} hint={hints} success={outcome['pass']} attempts={outcome['attempts']}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cohort", choices=["main", "holdout", "prospective"], required=True)
    ap.add_argument("--inspect-only", action="store_true", help="read-only diagnostic feature-hint availability without new compiles")
    args = ap.parse_args()
    cohort = ROOT if args.cohort == "main" else ROOT / args.cohort
    if args.inspect_only:
        p = cohort / "data/crates_manifest.json"
        metas = {x["crate"]: x for x in json.loads(p.read_text())}
        positives = [x for x in replay.read_jsonl(cohort / "results/screen.jsonl") if x["label"] == "eligible_mismatch"]
        for row in positives:
            rec = json.loads((cohort / "results/checks" / (row["default"] + ".json")).read_text())
            print(row["crate"], row["id"], compiler_feature_hints(rec, metas[row["crate"]]))
        return
    evaluate(cohort)


if __name__ == "__main__":
    main()
