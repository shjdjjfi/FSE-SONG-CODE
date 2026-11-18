#!/usr/bin/env python3
"""Evaluate secondary frozen path-aware heuristic at identical compile budget."""
import argparse
import json
from pathlib import Path
import sys

import replay
import pathaware

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cohort", choices=["holdout", "prospective"], required=True)
    args = ap.parse_args()
    cohort = ROOT / args.cohort
    replay.DATA = cohort / "data"
    replay.RESULTS = cohort / "results"
    replay.WORK = ROOT / "work"
    meta = {x["crate"]: x for x in json.loads((replay.DATA / "crates_manifest.json").read_text())}
    corpus = {x["id"]: x for x in replay.read_jsonl(replay.DATA / "corpus.jsonl")}
    positives = [x for x in replay.read_jsonl(replay.RESULTS / "screen.jsonl") if x["label"] == "eligible_mismatch"]
    out = {x["id"]: x for x in replay.read_jsonl(replay.RESULTS / "pathaware.jsonl")}
    for i, result in enumerate(positives, start=1):
        rid = result["id"]
        if rid in out:
            continue
        source = corpus[rid]
        features = pathaware.candidate_features_v2(meta[result["crate"]], source)
        search = replay.evaluate_sequence(meta[result["crate"]], source, features)
        out[rid] = {"id": rid, "crate": result["crate"], "source": source["source"],
                    "pathaware_ranking": features, "pathaware": search}
        (replay.RESULTS / "pathaware.jsonl").write_text("".join(json.dumps(x) + "\n" for x in out.values()))
        print(f"[{i}/{len(positives)}] {result['crate']} {rid} v2={search['pass']} attempts={search['attempts']}", flush=True)


if __name__ == "__main__":
    main()
