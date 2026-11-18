#!/usr/bin/env python3
"""Gather provenance-rich, timestamped public GitHub evidence for N08.

Uses public GitHub REST only for PR metadata and path-limited commit histories;
review events are parsed from publicly rendered PR timelines. Stores compact
derivatives and SHA256 of source responses, not copyrighted HTML pages.
"""

import argparse
import concurrent.futures
import datetime as dt
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from lxml import html

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data"
UA = "FSE-Industry-N08-empirical-study/0.1 (public-research)"
BOT = re.compile(r"(?:\[bot\]|-bot$|^dependabot$|^github-actions$)", re.I)


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def fetch(url, timeout=25, attempts=3):
    for i in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/vnd.github+json" if url.startswith("https://api.github.com") else "text/html, */*"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = r.read()
                return data, dict(r.headers)
        except (urllib.error.URLError, TimeoutError) as exc:
            if isinstance(exc, urllib.error.HTTPError) and exc.code in (401, 403, 404, 422):
                raise RuntimeError(f"Non-retryable HTTP {exc.code}: {url}") from exc
            if i == attempts - 1:
                raise RuntimeError(f"Fetch failed {url}: {exc}") from exc
            time.sleep(i + 1)
    raise AssertionError("unreachable")


def load_or_fetch_json(path, url, overwrite=False):
    if path.exists() and not overwrite:
        cached = json.loads(path.read_text(encoding="utf-8"))
        if cached.get("source_url") == url:
            return cached
    buf, headers = fetch(url)
    obj = json.loads(buf)
    write_json(path, {"source_url": url, "sha256": hashlib.sha256(buf).hexdigest(),
                      "fetched_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                      "rate_remaining": headers.get("X-RateLimit-Remaining"), "body": obj,
                      "link_header": headers.get("Link")})
    return json.loads(path.read_text(encoding="utf-8"))


def owner_for(path, content):
    """Limited prefix CODEOWNERS resolver for explicit paths in the curated cases.

    Does not pretend to implement full gitignore-style wildcard semantics. If a
    wildcard might affect the result, returns ambiguity in validation instead.
    """
    matched = []
    for line in content.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        toks = s.split("#")[0].split()
        if len(toks) < 2:
            continue
        pat = toks[0].lstrip("/").rstrip("/")
        if "*" in pat or "?" in pat or "[" in pat:
            continue
        if path == pat or path.startswith(pat + "/"):
            matched = [x for x in toks[1:] if x.startswith("@")]
    return matched


def parse_patch_renames(patch):
    old = re.findall(r"^rename from (.+)$", patch, flags=re.M)
    new = re.findall(r"^rename to (.+)$", patch, flags=re.M)
    return [{"old": a, "new": b} for a, b in zip(old, new)]


def review_timeline(page):
    doc = html.fromstring(page)
    nodes = doc.xpath('//div[contains(concat(" ",normalize-space(@class)," ")," TimelineItem ")]')
    reviews, merged_at = [], None
    for node in nodes:
        txt = " ".join(node.text_content().split())
        dates = node.xpath('.//relative-time/@datetime')
        if re.search(r"\bmerged commit\b", txt) and dates:
            merged_at = dates[0]
        if not dates:
            continue
        state = next((state for phrase, state in [("approved these changes", "APPROVED"),
                                                  ("requested changes", "CHANGES_REQUESTED"),
                                                  ("left a review comment", "COMMENTED"),
                                                  ("reviewed", "COMMENTED")]
                      if phrase in txt.lower()), None)
        if state is None:
            continue
        href = node.xpath('.//a[contains(@class,"TimelineItem-avatar")]/@href')
        user = href[0].strip("/") if href else None
        if not user or "/" in user or BOT.search(user):
            continue
        reviews.append({"login": user, "state": state, "submitted_at": dates[0]})
    dates_all = doc.xpath('//relative-time/@datetime')
    opened_at = min(dates_all) if dates_all else None
    # Stable deduplication: one user can submit multiple independent reviews.
    reviews = list({(r["login"], r["state"], r["submitted_at"]): r for r in reviews}.values())
    reviews.sort(key=lambda x: x["submitted_at"])
    return opened_at, merged_at, reviews


def fetch_pr_html(repo, n, overwrite=False):
    path = OUT / "pr_timelines" / f"{repo.replace('/', '__')}__{n}.json"
    if path.exists() and not overwrite:
        return json.loads(path.read_text(encoding="utf-8"))
    url = f"https://github.com/{repo}/pull/{n}"
    buf, _ = fetch(url)
    opened, merged, reviews = review_timeline(buf.decode("utf-8", "replace"))
    obj = {"repo": repo, "pr": n, "source_url": url,
           "raw_html_sha256": hashlib.sha256(buf).hexdigest(),
           "fetched_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
           "opened_at": opened, "merged_at": merged, "reviews": reviews,
           "review_count_visible": len(reviews)}
    write_json(path, obj)
    return obj


def collect_event(event, overwrite=False, pre_days=365, post_days=365):
    n, repo = event["migration_pr"], event["repo"]
    slug = repo.replace("/", "__")
    meta = load_or_fetch_json(OUT / "metadata" / f"{slug}__{n}.json",
                              f"https://api.github.com/repos/{repo}/pulls/{n}", overwrite)["body"]
    if not meta.get("merged_at"):
        raise ValueError(f"PR #{n} never merged: cannot be a migration event")
    buf, _ = fetch(f"https://github.com/{repo}/pull/{n}.patch")
    patch = buf.decode("utf-8", "replace")
    rename_pairs = [pair for pair in parse_patch_renames(patch)
                    if pair["old"].startswith(event["old_prefix"]) and pair["new"].startswith(event["new_prefix"])]
    if not rename_pairs:
        raise ValueError(f"No verified actual cross-prefix rename in #{n}")
    old_url = f"https://raw.githubusercontent.com/{repo}/{meta['base']['sha']}/.github/CODEOWNERS"
    new_url = f"https://raw.githubusercontent.com/{repo}/{meta['merge_commit_sha']}/.github/CODEOWNERS"
    before, _ = fetch(old_url)
    after, _ = fetch(new_url)
    source_owner = owner_for(rename_pairs[0]["old"], before.decode("utf-8", "replace"))
    target_owner = owner_for(rename_pairs[0]["new"], after.decode("utf-8", "replace"))
    # Owner declarations are independently validated, not simply copied from config.
    old_ok = event["expected_old_team"] in source_owner
    new_ok = event["expected_new_team"] in target_owner
    if not (old_ok and new_ok and event["expected_old_team"] != event["expected_new_team"]):
        raise ValueError(f"CODEOWNERS handoff unverified #{n}: {source_owner} -> {target_owner}")
    merged = dt.datetime.fromisoformat(meta["merged_at"].replace("Z", "+00:00"))
    histories = {}
    for role, prefix, start, end in [
        ("before", event["old_prefix"], merged - dt.timedelta(days=pre_days), merged - dt.timedelta(seconds=1)),
        ("after", event["new_prefix"], merged + dt.timedelta(seconds=1), merged + dt.timedelta(days=post_days))
    ]:
        qs = urllib.parse.urlencode({"path": prefix, "since": start.isoformat().replace("+00:00", "Z"),
                                     "until": end.isoformat().replace("+00:00", "Z"), "per_page": 100})
        url = f"https://api.github.com/repos/{repo}/commits?{qs}"
        h = load_or_fetch_json(OUT / "commit_queries" / f"{event['id']}_{role}.json", url, overwrite)
        items = []
        for c in h["body"]:
            title = c.get("commit", {}).get("message", "").splitlines()[0]
            prs = re.findall(r"\(#(\d+)\)", title)
            if prs:
                items.append({"sha": c["sha"], "date": c["commit"]["committer"]["date"],
                              "pr": int(prs[-1]), "title": title})
        # API returns newest first. Keep one observation per PR; avoid incomplete
        # first-page samples when >100 results. Such events are flagged unfit.
        unique = {it["pr"]: it for it in reversed(items)}
        histories[role] = {"source_url": url, "commit_count": len(h["body"]),
                           "pr_linked_count": len(unique), "truncated": bool(h.get("link_header")),
                           "records": sorted(unique.values(), key=lambda x: (x["date"], x["pr"]))}
    obj = {**event, "merged_at": meta["merged_at"], "merge_sha": meta["merge_commit_sha"],
           "base_sha": meta["base"]["sha"], "rename_pairs": rename_pairs,
           "all_patch_renames": len(parse_patch_renames(patch)),
           "migration_patch_sha256": hashlib.sha256(buf).hexdigest(),
           "before_codeowners_sha256": hashlib.sha256(before).hexdigest(),
           "after_codeowners_sha256": hashlib.sha256(after).hexdigest(),
           "old_owner": source_owner, "new_owner": target_owner,
           "pre_days": pre_days, "post_days": post_days, "histories": histories,
           "valid": True}
    write_json(OUT / "events" / f"{event['id']}.json", obj)
    return obj


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--only", default="", help="comma-separated event ids")
    ap.add_argument("--timelines", action="store_true", help="collect public PR review timelines")
    ap.add_argument("--max-train", type=int, default=10)
    ap.add_argument("--max-test", type=int, default=15)
    ap.add_argument("--pre-days", type=int, default=365)
    ap.add_argument("--post-days", type=int, default=365)
    args = ap.parse_args()
    events = json.loads((ROOT / "config" / "events.json").read_text())
    if args.only:
        events = [e for e in events if e["id"] in args.only.split(",")]
    completed, errors = [], {}
    for e in events:
        try:
            result = collect_event(e, args.overwrite, args.pre_days, args.post_days)
            completed.append(result)
            print(e["id"], "merged", result["merged_at"][:10],
                  "renames", len(result["rename_pairs"]), "commits", result["histories"]["before"]["commit_count"],
                  result["histories"]["after"]["commit_count"], flush=True)
        except Exception as ex:
            errors[e["id"]] = str(ex)
            print("ERROR", e["id"], str(ex), flush=True)
    if args.timelines:
        candidates = {}
        for e in completed:
            for role, max_n in [("before", args.max_train), ("after", args.max_test)]:
                rows = e["histories"][role]["records"]
                if role == "before":
                    rows = list(reversed(rows))[:max_n]
                else:
                    rows = rows[:max_n]
                for row in rows:
                    if row["pr"] != e["migration_pr"]:
                        candidates[(e["repo"], row["pr"])] = True
            candidates[(e["repo"], e["migration_pr"])] = True
        print("TIMELINES", len(candidates), flush=True)
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            future_map = {pool.submit(fetch_pr_html, *key, args.overwrite): key for key in candidates}
            for fut in concurrent.futures.as_completed(future_map):
                try:
                    fut.result()
                except Exception as ex:
                    errors[str(future_map[fut])] = str(ex)
        print("TIMELINES_FAILED", len([x for x in errors if x.startswith('(')]), flush=True)
    all_verified_events = sorted(p.stem for p in (OUT / "events").glob("*.json"))
    write_json(OUT / "harvest_status.json", {"completed_events": all_verified_events,
                                                  "selected_events_in_this_run": [e["id"] for e in completed],
                                                  "errors": errors, "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                                                  "max_train_pr": args.max_train, "max_test_pr": args.max_test})


if __name__ == "__main__":
    main()
