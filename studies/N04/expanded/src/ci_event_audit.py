"""Audit real public quarantine/dequarantine transitions without a login.

Only public GitLab and GitHub APIs are queried. Each response is hashed and
reduced to stable, relevant metadata. The code never pretends that a PR status
or a post-merge workflow conclusion is a per-test quarantine effect.
No credentials are used or requested.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

GITLAB_MRS = (162803, 164022, 195179, 228726, 149942, 155883)
GITHUB_PRS = (13874, 14040, 9023)
GITHUB_ISSUES = (9712, 9670, 9789, 8728)
BASE_GITLAB = "https://gitlab.com/api/v4/projects/gitlab-org%2Fgitlab"
BASE_GITHUB = "https://api.github.com/repos/microsoft/aspire"


def request_json(url: str, *, retries=2):
    last = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "research-public-ci-history/1.0",
                "Accept": "application/vnd.github+json" if "api.github.com" in url else "application/json",
            })
            with urllib.request.urlopen(req, timeout=30) as response:
                data = response.read()
            value = json.loads(data)
            return value, {"source_url": url, "sha256": hashlib.sha256(data).hexdigest(),
                           "response_bytes": len(data), "access": "public"}
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last = exc
            if isinstance(exc, urllib.error.HTTPError) and exc.code in (401, 403, 404):
                break  # authentication, privacy, or access blocker: STOP
            time.sleep(min(2, attempt + 1))
    status = getattr(last, "code", None)
    return None, {"source_url": url, "error_type": type(last).__name__,
                  "http_status": status, "access": "not_observed"}


def gitlab_change_summary(change: dict):
    diff = change.get("diff", "")
    added = [x[1:] for x in diff.splitlines() if x.startswith("+") and not x.startswith("+++")]
    removed = [x[1:] for x in diff.splitlines() if x.startswith("-") and not x.startswith("---")]
    add_q = [x for x in added if re.search(r"\bquarantine\s*:", x)]
    rm_q = [x for x in removed if re.search(r"\bquarantine\s*:", x)]
    def tests(lines):
        return sorted(set(m.group(1) for line in lines
               if (m := re.search(r"\b(?:it|scenario|specify)\s*[( ]\s*['\"]([^'\"]+)", line))))
    return {"path_before": change.get("old_path"), "path_after": change.get("new_path"),
            "old_file_deleted": change.get("deleted_file"), "file_renamed": change.get("renamed_file"),
            "quarantine_lines_added": len(add_q), "quarantine_lines_removed": len(rm_q),
            "added_test_descriptions": tests(add_q), "removed_test_descriptions": tests(rm_q),
            "issue_refs_in_quarantine_additions": sorted(set(re.findall(
                r"https://gitlab.com/gitlab-org/(?:gitlab|quality/test-failure-issues)/-/issues/\d+",
                "\n".join(add_q)))),
            "issue_refs_in_quarantine_removals": sorted(set(re.findall(
                r"https://gitlab.com/gitlab-org/(?:gitlab|quality/test-failure-issues)/-/issues/\d+",
                "\n".join(rm_q)))),
            "diff_sha256": hashlib.sha256(diff.encode()).hexdigest(),
            "diff_was_truncated": change.get("too_large") or change.get("collapsed")}


def collect_gitlab():
    events = []
    for iid in GITLAB_MRS:
        raw_url = f"{BASE_GITLAB}/merge_requests/{iid}"
        mr, proof = request_json(raw_url)
        if not mr:
            events.append({"iid": iid, "error": proof})
            continue
        changes, change_proof = request_json(raw_url + "/changes")
        ev = {"iid": iid, "title": mr.get("title"), "state": mr.get("state"),
              "merged_at": mr.get("merged_at"), "merge_sha": mr.get("merge_commit_sha"),
              "web_url": mr.get("web_url"), "description_has_run_link": bool(re.search(
                r"gitlab\.com/.+/-/jobs/\d+", mr.get("description") or "")),
              "metadata_provenance": proof, "changes_provenance": change_proof,
              "files": [gitlab_change_summary(x) for x in changes.get("changes", [])]
              if isinstance(changes, dict) else []}
        ev["quarantine_additions"] = sum(x["quarantine_lines_added"] for x in ev["files"])
        ev["quarantine_removals"] = sum(x["quarantine_lines_removed"] for x in ev["files"])
        events.append(ev)
        print("GitLab", iid, ev["state"], "+", ev["quarantine_additions"],
              "-", ev["quarantine_removals"], flush=True)

    issue, evidence = request_json(f"{BASE_GITLAB}/issues/457549")
    issue_result = {"provenance": evidence}
    if issue:
        body = issue.get("description") or ""
        fingerprint = re.search(r"\| Hash \| `([a-f\d]{40})`", body)
        issue_result.update({"iid": issue.get("iid"), "title": issue.get("title"),
                             "created_at": issue.get("created_at"), "closed_at": issue.get("closed_at"),
                             "state": issue.get("state"), "web_url": issue.get("web_url"),
                             "documented_test_hash": fingerprint.group(1) if fingerprint else None})
    return {"project": "gitlab-org/gitlab", "merge_requests": events,
            "independent_issue": issue_result}


def github_changes(files: list[dict]):
    results = []
    for f in files:
        patch = f.get("patch", "")
        added = [x[1:] for x in patch.splitlines() if x.startswith("+") and not x.startswith("+++")]
        removed = [x[1:] for x in patch.splitlines() if x.startswith("-") and not x.startswith("---")]
        add_q = [x for x in added if "[QuarantinedTest" in x]
        rm_q = [x for x in removed if "[QuarantinedTest" in x]
        if add_q or rm_q:
            results.append({"path": f["filename"], "status": f.get("status"),
                            "quarantine_lines_added": len(add_q), "quarantine_lines_removed": len(rm_q),
                            "issue_ids_added": sorted(set(re.findall(r"github\.com/microsoft/aspire/issues/(\d+)","\n".join(add_q)))),
                            "issue_ids_removed": sorted(set(re.findall(r"github\.com/microsoft/aspire/issues/(\d+)","\n".join(rm_q)))),
                            "patch_sha256": hashlib.sha256(patch.encode()).hexdigest()})
    return results


def collect_github():
    prs=[]
    for number in GITHUB_PRS:
        url=f"{BASE_GITHUB}/pulls/{number}"
        pr,proof=request_json(url)
        if not pr:
            prs.append({"number":number,"error":proof})
            continue
        files,files_proof=request_json(url+"/files?per_page=100")
        f=github_changes(files) if isinstance(files,list) else []
        body=pr.get("body") or ""
        numbers=[int(x) for x in re.findall(r"(?i)(\d+)\s+(?:consecutive\s+)?runs",body)]
        p={"number":number,"title":pr.get("title"),"merged_at":pr.get("merged_at"),
           "merge_commit_sha":pr.get("merge_commit_sha"),"url":pr.get("html_url"),
           "claimed_runs_in_description":numbers,
           "quarantine_additions":sum(x["quarantine_lines_added"] for x in f),
           "quarantine_removals":sum(x["quarantine_lines_removed"] for x in f),
           "changed_quarantine_files":f,
           "provenance":proof,"files_provenance":files_proof}
        prs.append(p)
        print("Aspire",number,"merged",bool(p["merged_at"]),"+",p["quarantine_additions"],
              "-",p["quarantine_removals"],flush=True)
    issues=[]
    for number in GITHUB_ISSUES:
        url=f"{BASE_GITHUB}/issues/{number}"
        issue,proof=request_json(url)
        if not issue:
            issues.append({"number":number,"error":proof})
            continue
        body=issue.get("body") or ""
        # Extract reported observation counts (not estimates from this study).
        run_rows = re.findall(r"(?m)^\s*([A-Za-z0-9_./ ()-]+)\s*\((\d+)/(\d+)\)",body)
        issues.append({"number":number,"title":issue.get("title"),
                       "state":issue.get("state"),"closed_at":issue.get("closed_at"),
                       "created_at":issue.get("created_at"),"updated_at":issue.get("updated_at"),
                       "web_url":issue.get("html_url"),"run_report_rows":run_rows,
                       "body_has_recent_runs": "Recent runs" in body,
                       "provenance":proof})
    return {"project":"microsoft/aspire", "pull_requests":prs,"issues":issues}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path,default=Path("results/real_ci_events"))
    a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    report={"fetched_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
            "definition":"Developer-authored source quarantine transitions and published CI-run statistics; not a rename-specific deployment outcome",
            "gitlab":collect_gitlab(),"github":collect_github(),
            "cautions":["A merged source metadata change is real but is not, by itself, a measured CI outcome.",
                        "A maintainer's claimed repeated-run count is recorded as a claim unless raw job-level artifacts are independently obtained.",
                        "Issues and source changes are public; private/test-level CI dashboards may be inaccessible."]}
    (a.out/"public_event_ledger.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    print("Saved",a.out/"public_event_ledger.json")


if __name__=="__main__":
    main()
