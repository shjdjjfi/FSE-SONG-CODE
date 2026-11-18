#!/usr/bin/env python3
"""Retrospective pre/post release coverage of maintainer-confirmed feature-doc fixes.

We do not infer detection from the existence of a bug report. The current N05
prototype only extracts literal Rustdoc code fences from published source.
"""
import json
from pathlib import Path
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import collect

HISTORY = Path(__file__).resolve().parent / "historical"
RELEASES = (("iced", "0.10.0"), ("iced", "0.12.0"))
TARGETS = (
    {"maintainer_pr": "https://github.com/iced-rs/iced/pull/2188",
     "description": "Missing feature guidance for iced::time::every",
     "literal_patterns": ("time::every", "iced::time::every")},
    {"maintainer_pr": "https://github.com/iced-rs/iced/pull/2184",
     "description": "Missing feature badges for lazy widget helpers",
     "literal_patterns": ("widget::lazy", "lazy::")},
)


def main():
    HISTORY.mkdir(parents=True, exist_ok=True)
    collect.RAW = HISTORY / "data/crates"
    out = {"evidence_level": "independently_maintainer_reported_not_N05_deployment",
           "releases": [], "historical_targets": []}
    published = {}
    try:
        url = "https://crates.io/api/v1/crates/iced"
        req = urllib.request.Request(url, headers={"User-Agent": "N05-historical-audit"})
        with urllib.request.urlopen(req, timeout=20) as stream:
            obj = json.load(stream)
        published = {r["num"]: r.get("created_at") for r in obj.get("versions", [])}
    except Exception as exc:
        out["release_metadata_fetch_error"] = str(exc)
    cached = {}
    for crate, version in RELEASES:
        meta, rows = collect.collect_one(crate, version)
        cached[version] = rows
        out["releases"].append({"crate": crate, "version": version,
                                "published_utc": published.get(version),
                                "original_archive_sha256": meta["archive_sha256"],
                                "archive_url": meta["archive_url"],
                                "extracted_snippets": len(rows),
                                "docs_metadata": meta["docs_metadata"]})
        print(f"iced {version}: {len(rows)} literal code fences", flush=True)
    for target in TARGETS:
        case = {"maintainer_pr": target["maintainer_pr"],
                "description": target["description"], "releases": {}}
        for version, rows in cached.items():
            matches = [{"id": row["id"], "source": row["source"], "line": row["line"]}
                       for row in rows if any(p in row["compiled_code"] for p in target["literal_patterns"])]
            case["releases"][version] = {
                "literal_snippets_mentioning_affected_api": len(matches),
                "snippets": matches,
                "detection_status": "not screened: out of original method's fixed 32-crate cohort" if matches else
                                     "not detectable by current literal-snippet extractor",
            }
        out["historical_targets"].append(case)
    path = HISTORY / "historical_case_coverage.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(out["historical_targets"], indent=2))


if __name__ == "__main__":
    main()
