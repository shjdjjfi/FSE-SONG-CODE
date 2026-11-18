#!/usr/bin/env python3
"""Compile-check a narrow alternative to a bloated one-flag recommendation."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import replay
from minimize import feature_closure


def main():
    d = ROOT / "holdout"
    replay.DATA = d / "data"
    replay.RESULTS = d / "results"
    replay.WORK = ROOT / "work"
    meta = {x["crate"]:x for x in json.loads((replay.DATA / "crates_manifest.json").read_text())}["tower"]
    row = {x["id"]:x for x in replay.read_jsonl(replay.DATA / "corpus.jsonl")}["70f8633f0aab478c"]
    record = {"crate":"tower","release":"0.5.2", "snippet_id":row["id"],
              "source":row["source"],"line":row["line"],
              "original_selected_feature":"balance","source_named_feature":"util",
              "intervention":"counterfactual actual Cargo checks in isolated consumer, not an upstream CI deployment"}
    for name, flags in (("original_broad", ["balance"]),("narrow_candidate",["util"])):
        check = replay.run_check(meta,row,"candidate",flags)
        record[name] = {"requested":flags,"status":check["status"],"check":check["key"],
                        "feature_closure":feature_closure(meta,flags),
                        "feature_closure_size":len(feature_closure(meta,flags))}
    record["observed_narrower_repair"] = (
        record["original_broad"]["status"] == "pass" and
        record["narrow_candidate"]["status"] == "pass" and
        set(record["narrow_candidate"]["feature_closure"]) < set(record["original_broad"]["feature_closure"]))
    dest = ROOT / "industrial/verified_dominated_fix.json"
    dest.write_text(json.dumps(record,indent=2)+"\n")
    print(json.dumps(record,indent=2))


if __name__ == "__main__":
    main()
