#!/usr/bin/env python3
"""Pre-register a stratified and seeded consumer-replay sample.

Three seeds change which *published* snippet is selected, not the compiler or
the outcome. All selection precedes compilation and is persisted on disk.
"""
import json
from pathlib import Path
import random
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SEEDS = [17, 29, 43]


def risk(row, crate_meta):
    doc_features = crate_meta.get("docs_metadata", {})
    default = set(crate_meta.get("default_features", []))
    if not doc_features.get("all-features") and not doc_features.get("features"):
        return False
    candidates = (set(crate_meta["feature_names"]) if doc_features.get("all-features")
                  else set(doc_features.get("features", []))) - default - {"default"}
    code = row["compiled_code"].lower()
    for feat in candidates:
        norm = feat.lower().replace("-", "_")
        if len(norm) < 2:
            continue
        if re.search(r"\b" + re.escape(norm) + r"\b", code):
            return True
        if re.search(r"\bnew_" + re.escape(norm) + r"\b", code):
            return True
    return False


def main():
    metas = {m["crate"]: m for m in json.loads((DATA / "crates_manifest.json").read_text())}
    corpus = [json.loads(s) for s in (DATA / "corpus.jsonl").read_text().splitlines()]
    by_crate = {crate: [] for crate in metas}
    for row in corpus:
        code = row["compiled_code"]
        if len(code) > 3000 or any(s in code for s in ("...", "todo!", "unimplemented!")):
            continue
        # Test the actual code from the documentation. We do not synthesize
        # unknown async runtimes or missing third-party dependencies.
        if ".await" in code and "async fn main" not in code and "# async fn main" not in row["raw_code"]:
            continue
        row["risk"] = risk(row, metas[row["crate"]])
        by_crate[row["crate"]].append(row)

    # Each seed: at most two high-risk and one other item from each of 24
    # packages. Repeated snippets across seeds share one compilation record.
    assignments = []
    for seed in SEEDS:
        for crate in sorted(metas):
            rng = random.Random(f"n05:v1:{seed}:{crate}")
            available = by_crate[crate]
            high = sorted((r for r in available if r["risk"]), key=lambda r: r["id"])
            low = sorted((r for r in available if not r["risk"]), key=lambda r: r["id"])
            selected = rng.sample(high, min(2, len(high)))
            selected += rng.sample(low, min(3 - len(selected), len(low)))
            if len(selected) < 3:
                rest = [r for r in available if r not in selected]
                selected += rng.sample(rest, min(3 - len(selected), len(rest)))
            for row in selected:
                assignments.append({"seed": seed, "crate": crate, "id": row["id"],
                                    "stratum": "risk" if row["risk"] else "control"})
    (DATA / "frozen_sample.json").write_text(json.dumps({
        "selection_version": 1,
        "seeds": SEEDS,
        "rule": "Per seed and crate: up to two risk, plus control, three total; all before compiling.",
        "n_corpus": len(corpus),
        "n_filtered": sum(map(len, by_crate.values())),
        "assignments": assignments,
    }, indent=2) + "\n")
    print(f"Frozen: {len(assignments)} seed-assigned rows, "
          f"{len({r['id'] for r in assignments})} distinct snippets, "
          f"{sum(r['stratum'] == 'risk' for r in assignments)} risk assignments")


if __name__ == "__main__":
    main()
