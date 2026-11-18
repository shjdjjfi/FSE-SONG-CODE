#!/usr/bin/env python3
"""Visible-copy ablation on independently admissible consumer snippets."""
import collections
import json
from pathlib import Path

from replay import run_check

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RESULTS = ROOT / "results"


def main():
    meta = {x["crate"]: x for x in json.loads((DATA / "crates_manifest.json").read_text())}
    corpus = {x["id"]: x for x in map(json.loads, (DATA / "corpus.jsonl").read_text().splitlines())}
    screen = [json.loads(x) for x in (RESULTS / "screen.jsonl").read_text().splitlines()]
    # Fixed one each per label per project to avoid letting large projects set
    # the result. No ablation examples chosen based on their visible-only result.
    chosen = {}
    for s in sorted(screen, key=lambda r: r["id"]):
        if s["label"] not in ("eligible_mismatch", "default_compiles"):
            continue
        key = (s["crate"], s["label"])
        if key not in chosen:
            chosen[key] = s
    output = []
    for (crate, label), s in sorted(chosen.items()):
        profile = "docs" if label == "eligible_mismatch" else "default"
        res = run_check(meta[crate], corpus[s["id"]], profile, visible=True)
        output.append({"id": s["id"], "crate": crate, "label": label,
                       "hidden_included_status": "pass", "visible_only_status": res["status"],
                       "profile": profile, "check": res["key"]})
        print(f"{crate}: {label} visible={res['status']}", flush=True)
    (RESULTS / "visible_ablation.json").write_text(json.dumps(output, indent=2) + "\n")
    print(f"{len(output)} independent project/stratum ablations")


if __name__ == "__main__":
    main()
