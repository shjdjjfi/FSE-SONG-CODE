#!/usr/bin/env python3
"""Advisory external consumer example check for a released Rust crate.

This is a runnable CI *prototype*, not evidence that an upstream project has
adopted it. A feature mismatch is a suggestion, not automatically a bug.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import collect
import replay

selector_spec = importlib.util.spec_from_file_location("n05_gate_selector", ROOT / "scripts/select.py")
selector = importlib.util.module_from_spec(selector_spec)
selector_spec.loader.exec_module(selector)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--crate", required=True, help="published crates.io name")
    ap.add_argument("--version", required=True, help="exact published version")
    ap.add_argument("--limit", type=int, default=12)
    ap.add_argument("--output-dir", type=Path, default=ROOT / "industrial/local_ci_runs")
    args = ap.parse_args()
    if args.limit <= 0 or args.limit > 1000:
        ap.error("--limit must be between 1 and 1000")
    name = args.crate
    if not all(c.isalnum() or c in "-_" for c in name) or not all(c.isalnum() or c in ".-_" for c in args.version):
        ap.error("invalid crate name/version")

    out = args.output_dir / f"{name}-{args.version}"
    out.mkdir(parents=True, exist_ok=True)
    collect.RAW = out / "data/crates"
    meta, corpus = collect.collect_one(name, args.version)
    replay.DATA = out / "data"
    replay.RESULTS = out / "results"
    replay.WORK = ROOT / "work"
    # Never train on this sample; deterministic choice and no statistical claim.
    filtered = [r for r in corpus if len(r["compiled_code"]) <= 3000 and
                not any(s in r["compiled_code"] for s in ("...", "todo!", "unimplemented!")) and
                not (".await" in r["compiled_code"] and "async fn main" not in r["compiled_code"])]
    high = sorted((r for r in filtered if selector.risk(r, meta)), key=lambda r: r["id"])
    low = sorted((r for r in filtered if not selector.risk(r, meta)), key=lambda r: r["id"])
    rng = random.Random(f"N05-release-gate-v1:{name}:{args.version}")
    rng.shuffle(high)
    rng.shuffle(low)
    high_n = min(len(high), (2 * args.limit + 2) // 3)
    chosen = high[:high_n] + low[:args.limit - high_n]
    if len(chosen) < args.limit:
        chosen.extend(high[high_n:high_n + (args.limit - len(chosen))])
    report = []
    for i, row in enumerate(chosen, 1):
        default = replay.run_check(meta, row, "default")
        docs = replay.run_check(meta, row, "docs")
        candidate = None
        if default["status"] == "fail" and docs["status"] == "pass":
            candidate = replay.explore(meta, row)
        report.append({"id": row["id"], "source": row["source"], "line": row["line"],
                       "default_status": default["status"], "docs_status": docs["status"],
                       "candidate": candidate, "label": "feature_profile_mismatch" if candidate else "not_a_confirmed_mismatch"})
        print(f"[{i}/{len(chosen)}] {name} {row['source']}:{row['line']} default={default['status']} docs={docs['status']}", flush=True)
    record = {"source": meta, "sample_method": "seeded fixed unordered sample; no learning",
              "sampled": len(chosen), "candidate_mismatches": sum(x["candidate"] is not None for x in report),
              "industrial_adoption": False, "semantic_defects_confirmed": 0,
              "note": "Advisory only. A page may already display the feature prerequisite. Do not report candidate count as defects.",
              "findings": report}
    dest = out / "gate_findings.json"
    dest.write_text(json.dumps(record, indent=2) + "\n")
    md = [f"# N05 release consumer check — {name} {args.version}", "",
          f"Examined {len(chosen)} externally compiled documentation snippets.",
          f"Observed {record['candidate_mismatches']} feature-profile differences. These are not verified documentation defects.",
          "", "| Source | Line | Default profile | docs.rs feature profile |", "|---|---:|---|---|"]
    md.extend(f"| {x['source']} | {x['line']} | {x['default_status']} | {x['docs_status']} |" for x in report)
    (out / "SUMMARY.md").write_text("\n".join(md) + "\n")
    print("CI ADVISORY: report written to", dest)


if __name__ == "__main__":
    main()
