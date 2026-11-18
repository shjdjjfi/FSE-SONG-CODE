"""Inclusion/label-availability audit of independent mined GitHub Actions runs.

The dataset contains *failing candidates only*. Absence from an event must not
be inferred as a passing test, and reproduction passes aren't CI pass history.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path


def audit(files: list[Path]):
    results=[]
    by_repo={}
    for path in files:
        data=json.loads(path.read_text())
        repo="/".join(path.parts[-3:-1])
        repo_agg=by_repo.setdefault(repo,{"run_keys":set(),"test_ids":set(),"mixed_ids":set(),
                                      "quarantine_absent_run_keys":set(),"all_records":0})
        seen={}
        n_candidates=0
        n_mixed_records=0
        missing_quarantine=0
        dates=[]
        for run in data:
            dates.append(run.get("created_at"))
            run_key=(run.get("run_id"),run.get("run_attempt"))
            repo_agg["run_keys"].add(run_key)
            repo_agg["all_records"]+=1
            if "quarantine" not in run and "quarantined_tests" not in run:
                missing_quarantine+=1
                repo_agg["quarantine_absent_run_keys"].add(run_key)
            for name, outcome in run.get("failed_tests",{}).items():
                n_candidates+=1
                repo_agg["test_ids"].add(name)
                if outcome.get("passes",0)>0 and outcome.get("failures",0)>0:
                    n_mixed_records+=1
                    repo_agg["mixed_ids"].add(name)
                seen.setdefault(name,[]).append(outcome)
        results.append({"repository":repo,"source_path":str(path.as_posix()),
                        "runs_with_failing_candidate":len(data),
                        "unique_failed_node_ids":len(seen),
                        "test_fail_records":n_candidates,
                        "test_fail_records_with_mixed_replication":n_mixed_records,
                        "unique_ids_with_mixed_replication":sum(any(x.get("passes",0)>0 and x.get("failures",0)>0 for x in v) for v in seen.values()),
                        "run_records_without_quarantine_field":missing_quarantine,
                        "min_created_at":min(dates) if dates else None,
                        "max_created_at":max(dates) if dates else None})
    unions=[{"repository":repo,"unique_run_attempts":len(agg["run_keys"]),
             "unique_failed_node_ids":len(agg["test_ids"]),
             "unique_ids_with_mixed_replication":len(agg["mixed_ids"]),
             "unique_runs_without_quarantine_field":len(agg["quarantine_absent_run_keys"]),
             "duplicate_run_attempts_across_snapshots":agg["all_records"]-len(agg["run_keys"])}
            for repo,agg in sorted(by_repo.items())]
    return {"scope":"Mined real GitHub Actions failure candidates, NOT full test logs or verified quarantine decisions",
            "uses_official_data_snapshot_files_only":True,
            "cannot_label_post_rename_pass_from_missing_failed_node":True,
            "unique_across_repositories_not_assumed":True,
            "reproduction_passes_are_not_historical_CI_runs":True,
            "snapshot_files":results,"repository_unions":unions,"overall":{
                "unique_repository_run_attempts":sum(x["unique_run_attempts"] for x in unions),
                "unique_failed_test_ids_per_repo_summed":sum(x["unique_failed_node_ids"] for x in unions),
                "distinct_test_ids_with_mixed_replications_per_repo_summed":sum(x["unique_ids_with_mixed_replication"] for x in unions),
                "runs_missing_quarantine_field":sum(x["unique_runs_without_quarantine_field"] for x in unions),
                "duplicate_run_attempts_across_snapshots":sum(x["duplicate_run_attempts_across_snapshots"] for x in unions)}}


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,action="append",required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    data=audit(a.source)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(data,indent=2),encoding="utf-8")
    print(json.dumps(data["overall"],indent=2))
