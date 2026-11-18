#!/usr/bin/env python3
"""Archive independent public CI/maintainer records with provenance.

These are observational context and known defects, NOT outcomes of an N05
deployment. No intervention on third-party CI is implied by this script.
"""
import datetime as dt
import hashlib
import json
import pathlib
import re
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEST = ROOT / "industrial" / "public_records"
PROJECTS = (
    "tokio-rs/tokio",
    "tokio-rs/axum",
    "tower-rs/tower",
    "tower-rs/tower-http",
    "iced-rs/iced",
)
KNOWN_ISSUES = (("iced-rs/iced", 2188), ("iced-rs/iced", 2184))


def fetch(url):
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "N05-FSE-open-source-analysis",
    })
    for try_no in range(3):
        try:
            with urllib.request.urlopen(req, timeout=28) as f:
                return f.read(), dict(f.headers)
        except (OSError, urllib.error.HTTPError) as ex:
            if try_no == 2:
                raise
            print(f"Fetch retry {try_no}: {url}: {ex}", flush=True)
            time.sleep(2 + try_no)


def save_record(name, url, content, headers):
    DEST.mkdir(parents=True, exist_ok=True)
    payload = {
        "source_url": url,
        "retrieved_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "sha256": hashlib.sha256(content).hexdigest(),
        "content_type": headers.get("Content-Type"),
        "etag": headers.get("ETag"),
        "content": content.decode("utf-8", errors="replace"),
    }
    p = DEST / (name + ".json")
    p.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    return payload


def main():
    records = {"classification": "observational_real_public_CI_and_maintainer_change_not_N05_intervention",
               "projects": [], "maintainer_fixes": [], "fetch_failures": []}
    for repo in PROJECTS:
        name = repo.replace("/", "_")
        runs_url = f"https://api.github.com/repos/{repo}/actions/runs?status=success&per_page=10"
        try:
            data, headers = fetch(runs_url)
            save_record(name + "_runs", runs_url, data, headers)
            obj = json.loads(data)
            candidates = [x for x in obj.get("workflow_runs", []) if
                          x.get("conclusion") == "success" and x.get("head_sha") and x.get("path")]
            # Latest successful *project CI workflow*, not a release/publish job.
            workflows = [x for x in candidates if re.search(r"\b(?:ci|test|build|check)\b", x.get("name", ""), re.I)]
            pick = next(iter(workflows), None)
            if not pick:
                records["fetch_failures"].append({"repo": repo, "why": "no successful CI-type run in first 10"})
                continue
            path = pick["path"].removeprefix("./")
            raw_url = f"https://raw.githubusercontent.com/{repo}/{pick['head_sha']}/{path}"
            raw, raw_headers = fetch(raw_url)
            save_record(name + "_workflow", raw_url, raw, raw_headers)
            workflow_text = raw.decode("utf-8", errors="replace")
            commands = [l.strip() for l in workflow_text.splitlines() if
                        "cargo " in l.lower() or "cargo-" in l.lower() or "cargo-hack" in l.lower()]
            records["projects"].append({
                "repo": repo,
                "run_id": pick["id"], "run_url": pick["html_url"],
                "run_started_at": pick.get("run_started_at"), "updated_at": pick.get("updated_at"),
                "conclusion": pick.get("conclusion"), "head_sha": pick["head_sha"],
                "workflow_path": path, "workflow_sha256": hashlib.sha256(raw).hexdigest(),
                "workflow_name": pick["name"],
                "has_cargo_hack": bool(re.search(r"cargo(?:[ -])hack|cargo-hack", workflow_text)),
                "has_doc_test_command": bool(re.search(r"cargo\s+(?:\+\S+\s+)?test\b[^\n]*(?:--doc|--all)", workflow_text)),
                "has_consumer_cargo_manifest_replay_literal": bool(re.search(r"consumer.*(?:docs|examples).*(?:cargo|replay)", workflow_text, re.I)),
                "cargo_lines_in_workflow": commands[:50],
            })
            print(f"CI: {repo} run {pick['id']}: {len(commands)} cargo statements", flush=True)
        except Exception as ex:
            records["fetch_failures"].append({"repo": repo, "why": repr(ex)})
            print(f"CI FAIL: {repo}: {ex}", flush=True)

    for repo, number in KNOWN_ISSUES:
        url = f"https://api.github.com/repos/{repo}/issues/{number}"
        key = f"{repo.replace('/', '_')}_issue_{number}"
        try:
            data, headers = fetch(url)
            save_record(key, url, data, headers)
            obj = json.loads(data)
            records["maintainer_fixes"].append({
                "repo": repo, "number": number, "html_url": obj.get("html_url"),
                "title": obj.get("title"), "state": obj.get("state"),
                "closed_at": obj.get("closed_at"), "body": obj.get("body", "")[:2500],
                "independent_upstream_record": True,
                "is_n05_detection_result": False,
            })
            print(f"PR/issue: {repo}#{number}: {obj['title']}", flush=True)
        except Exception as ex:
            records["fetch_failures"].append({"issue": f"{repo}#{number}", "why": repr(ex)})
            print(f"PR FAIL: {repo}#{number}: {ex}", flush=True)
    out = ROOT / "industrial" / "public_ci_and_fixes.json"
    out.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n")
    print(f"Archived {len(records['projects'])} workflow/run pairs, {len(records['maintainer_fixes'])} historic records; {len(records['fetch_failures'])} failures", flush=True)


if __name__ == "__main__":
    main()
