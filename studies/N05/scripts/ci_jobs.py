#!/usr/bin/env python3
"""Attach observed GitHub Actions job timings (not attributable to N05)."""
import datetime as dt
import json
from pathlib import Path

from industrial_evidence import ROOT, fetch, save_record


def parse(ts):
    return dt.datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else None


def main():
    path = ROOT / "industrial/public_ci_and_fixes.json"
    records = json.loads(path.read_text())
    for project in records["projects"]:
        repo, run = project["repo"], project["run_id"]
        url = f"https://api.github.com/repos/{repo}/actions/runs/{run}/jobs?per_page=100"
        try:
            payload, headers = fetch(url)
            save_record(repo.replace("/", "_") + "_jobs", url, payload, headers)
            raw = json.loads(payload)
            jobs = []
            for job in raw.get("jobs", []):
                begin, end = parse(job.get("started_at")), parse(job.get("completed_at"))
                mins = round((end - begin).total_seconds() / 60, 2) if begin and end else None
                jobs.append({"id": job["id"], "name": job["name"], "status": job["status"],
                             "conclusion": job.get("conclusion"), "wall_minutes": mins})
            project["observed_jobs"] = jobs
            project["jobs_api_total_count"] = raw.get("total_count")
            project["jobs_observed_count"] = len(jobs)
            project["jobs_paginated_truncated"] = raw.get("total_count", 0) > len(jobs)
            values = [v["wall_minutes"] for v in jobs if v["wall_minutes"] is not None]
            project["sum_of_observed_job_wall_minutes_not_billing"] = round(sum(values), 2)
            print(f"{repo}: {len(jobs)}/{raw.get('total_count')} jobs, sum {sum(values):.1f} job-min", flush=True)
        except Exception as exc:
            project["jobs_fetch_error"] = str(exc)
            print(f"{repo}: job fetch failed: {exc}", flush=True)
    path.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
