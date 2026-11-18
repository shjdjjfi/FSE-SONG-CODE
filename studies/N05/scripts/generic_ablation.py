#!/usr/bin/env python3
"""Transfer-control: remove all crate-specific and prose-based feature boosts.

This is an exploratory post-hoc ablation, NOT a third preregistered baseline.
It keeps the same 8-check limit and same independently labeled snippets.
"""
import json
from pathlib import Path

import replay

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RESULTS = ROOT / "results"


def main():
    meta = {m["crate"]: m for m in json.loads((DATA / "crates_manifest.json").read_text())}
    corpus = {r["id"]: r for r in replay.read_jsonl(DATA / "corpus.jsonl")}
    positives = [s for s in replay.read_jsonl(RESULTS / "screen.jsonl") if s["label"] == "eligible_mismatch"]
    old = {s["id"]: s for s in replay.read_jsonl(RESULTS / "generic_ablation.jsonl")}
    original = replay.collections_boosts
    replay.collections_boosts = lambda m, r: {}
    try:
        for s in positives:
            if s["id"] in old:
                continue
            m, row = meta[s["crate"]], corpus[s["id"]]
            order = replay.candidate_features(m, row)
            fixed = replay.evaluate_sequence(m, row, order)
            old[s["id"]] = {"id": s["id"], "crate": s["crate"], "ranking": order,
                            "lexical_only": fixed, "budget": 8,
                            "posthoc_exploratory": True}
            (RESULTS / "generic_ablation.jsonl").write_text("".join(json.dumps(x) + "\n" for x in old.values()))
            print(f"{s['crate']} {s['id']} generic_pass={fixed['pass']}", flush=True)
    finally:
        replay.collections_boosts = original


if __name__ == "__main__":
    main()
