#!/usr/bin/env python3
"""Compute transitive *published Cargo feature* footprint of suggested fixes.

The number of user-written feature flags is distinct from the number of
activated internal feature flags. A one-flag repair may be semantically bloated.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from minimize import feature_closure


def read_jsonl(path):
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()] if path.exists() else []


def main():
    cases = []
    for name in (".", "holdout", "prospective"):
        d = ROOT / name
        if not (d / "data/crates_manifest.json").exists():
            continue
        meta = {r["crate"]: r for r in json.loads((d / "data/crates_manifest.json").read_text())}
        results = read_jsonl(d / "results/minimized.jsonl")
        for x in results:
            requested = x["subset_minimal_feature_set"]
            m = meta[x["crate"]]
            activated = set(feature_closure(m, requested))
            default = set(feature_closure(m, []))
            increment = activated - default
            candidates = []
            if len(requested) == 1:
                for feature in sorted(increment - set(requested)):
                    if feature.startswith("_"):
                        continue
                    replacement = set(feature_closure(m, [feature])) - default
                    if replacement < increment:
                        candidates.append({"alternative_feature_flag": feature,
                                           "alternative_activated_feature_count": len(replacement),
                                           "saved_activated_feature_count": len(increment) - len(replacement),
                                           "same_consumer_compilation_status": "NOT_TESTED"})
            cases.append({"dataset": name, "crate": x["crate"], "id": x["id"],
                          "requested_flags": requested,
                          "activated_extra_internal_feature_flags": sorted(increment),
                          "activated_extra_internal_feature_count": len(increment),
                          "narrower_structural_subfeature_candidates": candidates,
                          "claim": "structural footprint only, not yet an alternative compiling fix"})
    output = ROOT / "industrial/feature_footprint.json"
    output.write_text(json.dumps({
        "scope": "Minimized successfully compiled fixes on frozen source releases",
        "method": "Cargo.toml feature graph closure; external dependencies not counted; alternative recompilation required before accepting a replacement.",
        "cases": cases}, indent=2) + "\n")
    suspect = [x for x in cases if x["narrower_structural_subfeature_candidates"]]
    print(f"Feature-footprint audit: {len(cases)} fixes, {len(suspect)} structurally dominated candidates")
    for x in suspect[:14]:
        print(x["dataset"], x["crate"], x["requested_flags"], "closure", x["activated_extra_internal_feature_count"],
              "possible", x["narrower_structural_subfeature_candidates"][:4])


if __name__ == "__main__":
    main()
