#!/usr/bin/env python3
"""Spot-check extracted public HTML reviews against GitHub's REST review API."""

import collections
import hashlib
import json
import re
from harvest import ROOT, fetch, write_json
from analyze import read_json, reviewed_users, parse_time


def main():
    rows = read_json(ROOT / "results" / "predictions.json")
    by_event = collections.defaultdict(list)
    for r in rows:
        by_event[r["event"]].append(r)
    samples = []
    for ev in sorted(by_event):
        # This checks even highly reviewed cases, where partial timelines may fail.
        pick = sorted(by_event[ev], key=lambda x: (-len(x["actual_reviewers"]), x["pr"]))[0]
        samples.append(pick)
    aud = []
    for row in samples:
        repo, pr = row["repo"], row["pr"]
        url = f"https://api.github.com/repos/{repo}/pulls/{pr}/reviews?per_page=100"
        buf, headers = fetch(url)
        api_reviews = json.loads(buf)
        timeline = read_json(ROOT / "data" / "pr_timelines" / f"{repo.replace('/', '__')}__{pr}.json")
        cutoff = parse_time(timeline.get("merged_at"))
        rest = set()
        for review in api_reviews:
            user = review.get("user") or {}
            submitted = parse_time(review.get("submitted_at"))
            if review.get("state") in ("APPROVED", "CHANGES_REQUESTED") and submitted and (not cutoff or submitted <= cutoff):
                name = user.get("login", "")
                if name and user.get("type") != "Bot" and not re.search(r"\[bot\]|-bot$", name, re.I):
                    rest.add(name.lower())
        html_label = reviewed_users(timeline)
        entry = {"event": row["event"], "repo": repo, "pr": pr, "api_url": url,
                 "api_sha256": hashlib.sha256(buf).hexdigest(),
                 "api_returned_review_events": len(api_reviews),
                 "html_label_users": sorted(html_label), "api_label_users": sorted(rest),
                 "matched": html_label == rest,
                 "rate_remaining": headers.get("X-RateLimit-Remaining")}
        print(row["event"], "PR", pr, "html", sorted(html_label), "api", sorted(rest),
              "match", entry["matched"], flush=True)
        aud.append(entry)
    result = {"sample_size": len(aud), "matched": sum(x["matched"] for x in aud),
              "mismatched": [x for x in aud if not x["matched"]], "audits": aud}
    write_json(ROOT / "results" / "rest_review_validation.json", result)
    if result["mismatched"]:
        raise RuntimeError("Some parsed timelines disagree with GitHub REST; investigate before citing results")


if __name__ == "__main__":
    main()
