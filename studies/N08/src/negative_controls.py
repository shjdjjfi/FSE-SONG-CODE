#!/usr/bin/env python3
"""Independent real-PR negative controls for N08's migration eligibility gate."""

import hashlib
import json
from harvest import OUT, ROOT, fetch, load_or_fetch_json, owner_for, parse_patch_renames, write_json
from analyze import is_handoff

CONTROLS = [
    {"id": "GF114006", "repo": "grafana/grafana", "pr": 114006,
     "case": "same-team move: stars API", "old_prefix": "apps/preferences/kinds/",
     "new_prefix": "apps/collections/kinds/", "substantive": True},
    {"id": "GF110257", "repo": "grafana/grafana", "pr": 110257,
     "case": "same-team move: alerting type", "old_prefix": "public/app/types/alerting.ts",
     "new_prefix": "public/app/features/alerting/unified/types/alerting.ts", "substantive": True},
    {"id": "GF105548", "repo": "grafana/grafana", "pr": 105548,
     "case": "same-team move: SDK generator", "old_prefix": "public/app/api/generator/",
     "new_prefix": "scripts/rtk-client-generator/", "substantive": True},
    {"id": "GF100371", "repo": "grafana/grafana", "pr": 100371,
     "case": "test-fixture-only move, ownership changed",
     "old_prefix": "public/app/features/query-library/api/testdata/",
     "new_prefix": "public/app/features/explore/spec/helper/testdata/", "substantive": False},
    {"id": "GF114837", "repo": "grafana/grafana", "pr": 114837,
     "case": "ownership-only change: OpenTSDB", "old_prefix": "none/",
     "new_prefix": "none/", "substantive": True},
    {"id": "BW16500", "repo": "bitwarden/clients", "pr": 16500,
     "case": "ownership-only change: desktop autofill", "old_prefix": "none/",
     "new_prefix": "none/", "substantive": True}
]


def main():
    outputs = []
    for e in CONTROLS:
        repo, n = e["repo"], e["pr"]
        url = f"https://api.github.com/repos/{repo}/pulls/{n}"
        meta = load_or_fetch_json(OUT / "metadata" / f"{repo.replace('/', '__')}__{n}.json", url)["body"]
        patch_url = f"https://github.com/{repo}/pull/{n}.patch"
        buf, _ = fetch(patch_url)
        renames = [r for r in parse_patch_renames(buf.decode("utf-8", "replace"))
                   if r["old"].startswith(e["old_prefix"]) and r["new"].startswith(e["new_prefix"])]
        old_owner, new_owner = [], []
        if renames:
            before, _ = fetch(f"https://raw.githubusercontent.com/{repo}/{meta['base']['sha']}/.github/CODEOWNERS")
            after, _ = fetch(f"https://raw.githubusercontent.com/{repo}/{meta['merge_commit_sha']}/.github/CODEOWNERS")
            old_owner = owner_for(renames[0]["old"], before.decode("utf-8", "replace"))
            new_owner = owner_for(renames[0]["new"], after.decode("utf-8", "replace"))
        decision = is_handoff(old_owner, new_owner, renames, e["substantive"])
        outcome = {**e, "source_url": patch_url, "sha256": hashlib.sha256(buf).hexdigest(),
                   "merged_at": meta.get("merged_at"), "matching_renames": len(renames),
                   "old_owner": old_owner, "new_owner": new_owner,
                   "added_old_reviewers": decision, "expected_added_old_reviewers": False}
        outputs.append(outcome)
        print(e["id"], e["case"], "renames", len(renames), "old", old_owner, "new", new_owner, "decision", decision, flush=True)
    summary = {"real_merged_controls": len(outputs), "true_negatives": sum(not x["added_old_reviewers"] for x in outputs),
               "false_positives": sum(x["added_old_reviewers"] for x in outputs),
               "limits": "Eligibility controls; these are not downstream reviewer-recall trials.",
               "observations": outputs}
    write_json(ROOT / "results" / "negative_controls.json", summary)
    if summary["false_positives"]:
        raise RuntimeError("Eligibility gate failed real-world negative controls")


if __name__ == "__main__":
    main()
