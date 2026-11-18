#!/usr/bin/env python3
"""Classify the actual changed files in each observed post-migration PR.

This is a mechanical *code-touching* audit, not a maintainer's independent
semantic-substance annotation. Keeps source URL/hash, not full PR patch text.
"""

import concurrent.futures
import hashlib
import json
import re
from pathlib import Path

from harvest import OUT, ROOT, fetch, write_json

CODE_ENDINGS = (".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java", ".cs", ".cpp", ".c", ".h")


def classify_patch(patch, prefix):
    matched, test_files, code_files, all_files = set(), set(), set(), set()
    affected_lines = 0
    path, hunk = None, False
    for line in patch.splitlines():
        if line.startswith("diff --git a/"):
            _, _, lhs, rhs = line.split(" ", 3)
            path = rhs.removeprefix("b/")
            all_files.add(path)
            hunk = False
            if path.startswith(prefix):
                matched.add(path)
                if path.endswith(CODE_ENDINGS):
                    if any(z in path.lower() for z in (".test.", ".spec.", "/test/", "/tests/")):
                        test_files.add(path)
                    else:
                        code_files.add(path)
            continue
        if line.startswith("@@"):
            hunk = True
            continue
        if hunk and path in code_files and (line.startswith("+") or line.startswith("-")) and not line.startswith(("+++", "---")):
            affected_lines += 1
    target_fraction = len(matched) / len(all_files) if all_files else 0.0
    return {"changed_files_in_whole_pr": len(all_files),
            "changed_files_under_target": len(matched),
            "target_file_fraction": round(target_fraction, 5),
            "code_files_under_target": len(code_files),
            "test_files_under_target": len(test_files),
            "changed_code_lines_under_target": affected_lines,
            "code_touched": bool(code_files and affected_lines > 0),
            # Sensitivity-only observational focus heuristic, developed after
            # initial results; NOT independent semantic annotation.
            "focused_code_touched": bool(code_files and affected_lines > 0 and target_fraction >= .10 and len(all_files) <= 100),
            "target_paths": sorted(matched)}


def process(row, event, overwrite=False):
    repo, pr = row["repo"], row["pr"]
    path = OUT / "diff_audit" / f"{event['id']}__{pr}.json"
    if path.exists() and not overwrite:
        return json.loads(path.read_text())
    url = f"https://github.com/{repo}/pull/{pr}.patch"
    buf, _ = fetch(url, timeout=35, attempts=2)
    obj = {"event": event["id"], "repo": repo, "pr": pr, "url": url,
           "sha256": hashlib.sha256(buf).hexdigest(), "raw_size_bytes": len(buf),
           **classify_patch(buf.decode("utf-8", "replace"), event["new_prefix"])}
    write_json(path, obj)
    return obj


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()
    rows = json.loads((ROOT / "results" / "predictions.json").read_text())
    events = {p.stem: json.loads(p.read_text()) for p in (OUT / "events").glob("*.json")}
    errors = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(process, r, events[r["event"]], args.overwrite): (r["event"], r["pr"]) for r in rows}
        for f in concurrent.futures.as_completed(futures):
            try:
                f.result()
            except Exception as exc:
                errors[str(futures[f])] = str(exc)
    expected = {(r['event'], r['pr']) for r in rows}
    data = [v for f in sorted((OUT / "diff_audit").glob("*.json"))
            if (v := json.loads(f.read_text())) and (v['event'], v['pr']) in expected]
    write_json(ROOT / "results" / "diff_audit_summary.json", {
        "total_pr_event_pairs": len(rows), "audited": len(data),
        "with_any_target_files": sum(d["changed_files_under_target"] > 0 for d in data),
        "with_code_changes": sum(d["code_touched"] for d in data),
        "with_focused_code_changes": sum(d["focused_code_touched"] for d in data),
        "errors": errors,
        "interpretation": "Mechanical code edits within destination subtree; NOT manual semantic adjudication",
        "rows": data})
    print("Diff audit:", len(data), "of", len(rows), "PR-event pairs; code-touched", sum(d["code_touched"] for d in data), "failures", len(errors))


if __name__ == "__main__":
    main()
