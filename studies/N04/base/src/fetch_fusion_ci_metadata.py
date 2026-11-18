"""Pin public Actions run/job metadata for a source-linked quarantine migration.

This is actual observed CI timing, but not a causal CI-cost counterfactual.
Job logs are not available anonymously (GitHub returns HTTP 403).
"""

from __future__ import annotations
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import subprocess
from urllib.request import Request,urlopen


BASE="https://api.github.com/repos/Runfusion/Fusion/actions/runs"
RUNS=(28697507894,28720367126)
MIGRATION="b5450832494d24e4171acea606b4c022a5a8475b"


def api(url):
    request=Request(url,headers={"User-Agent":"n04-reproducible-public-ci-study",
                                 "Accept":"application/vnd.github+json",
                                 "X-GitHub-Api-Version":"2022-11-28"})
    with urlopen(request,timeout=25) as r:
        return json.load(r)


def delta_seconds(start,end):
    a=datetime.fromisoformat(start.replace("Z","+00:00"))
    b=datetime.fromisoformat(end.replace("Z","+00:00"))
    return round((b-a).total_seconds(),3)


def snapshot(run_id):
    run=api(f"{BASE}/{run_id}")
    jobs=api(f"{BASE}/{run_id}/jobs?per_page=100")
    assert jobs["total_count"]<=100,"API pagination must be implemented before reporting"
    selected={key:run.get(key) for key in
              ("id","name","status","conclusion","created_at","run_started_at",
               "updated_at","head_sha","run_attempt","event","head_branch","html_url")}
    chosen_jobs=[]
    for job in jobs["jobs"]:
        chosen_jobs.append({"id":job["id"],"name":job["name"],
                            "conclusion":job.get("conclusion"),
                            "started_at":job.get("started_at"),
                            "completed_at":job.get("completed_at"),
                            "duration_seconds":delta_seconds(job["started_at"],job["completed_at"]),
                            "steps":[{k:step.get(k) for k in ("name","status","conclusion","started_at","completed_at")}
                                     for step in job.get("steps",[])]})
    selected["job_count"]=len(chosen_jobs)
    selected["job_walltimes_sum_seconds"]=round(sum(x["duration_seconds"] for x in chosen_jobs),3)
    selected["overall_update_elapsed_seconds"]=delta_seconds(run["run_started_at"],run["updated_at"])
    selected["jobs"]=chosen_jobs
    return selected


def main(repo,output):
    runs=[snapshot(run_id) for run_id in RUNS]
    post=runs[1]["head_sha"]
    ancestor=subprocess.run(["git","-C",str(repo),"merge-base","--is-ancestor",MIGRATION,post])
    if ancestor.returncode!=0:raise AssertionError("Follow-up CI run does not descend from migration commit")
    result={"retrieved_at_utc":datetime.now(timezone.utc).isoformat(),
            "public_api":"https://api.github.com/repos/Runfusion/Fusion/actions/runs/{id}/jobs",
            "study_commit":MIGRATION,
            "pre_run_is_original_maintainer_linked_failure":True,
            "post_run_head_descends_from_study_commit":True,
            "post_run_is_not_at_exact_study_commit":post!=MIGRATION,
            "observational_warning":"Before/after runs differ in source revisions and may have other failures; duration changes cannot be attributed to N04 or quarantine migration",
            "actual_retry_count_unobserved":"Two independent run IDs, each run_attempt=1; not a before-after rerun inventory for one failed PR",
            "job_log_access":"Public runs/jobs metadata available; anonymous /actions/jobs/{id}/logs returned HTTP 403",
            "runs":runs}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps({"runs":[{k:r[k] for k in ("id","name","conclusion","job_count",
                        "job_walltimes_sum_seconds","overall_update_elapsed_seconds")}
                        for r in runs]},indent=2))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--repo",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    main(a.repo,a.output)
