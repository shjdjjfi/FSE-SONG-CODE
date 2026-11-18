#!/usr/bin/env python3
"""Strict audit of the planned N21 grid, control fidelity and supplements."""
from __future__ import annotations
import json
from collections import Counter
from pathlib import Path
from run_n21 import CASE_SPECS, HERE, SOURCES

MAIN_FAULTS=["delete_nested_js","delete_entry_js","delete_dts","corrupt_js",
             "corrupt_dts","extra_stale","erase_dist","intact","buildinfo_missing"]
TS_FAULTS=["delete_dts","corrupt_dts","extra_stale","intact"]
MAIN_ARMS=["standard","selective_path","selective_hash","invalidate_all",
           "clean_all","force_all","full_cache"]

def supported(fault,outputs):
    ending=(".d.ts" if fault in ("delete_dts","corrupt_dts") else
            ".js" if fault in ("delete_nested_js","delete_entry_js","corrupt_js") else None)
    return ending is None or any(x.endswith(ending) for x in outputs)

def main():
    runtime=HERE/"runtime"
    results=HERE/"results"
    observations={}
    duplicates=[]
    for file in results.rglob("trials.jsonl"):
        for line in file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            item=json.loads(line)
            key=(item["case"],item["project"],item["fault"],item["seed"],item["arm"])
            if key in observations:
                duplicates.append(key)
            observations[key]=item
    expected={}
    all_meta={}
    for case,spec in CASE_SPECS.items():
        meta=json.loads((runtime/"metadata"/f"{case}.json").read_text())
        if not meta["oracle_exact_match"]:
            raise AssertionError(f"Clean oracle differs: {case}")
        all_meta[case]=meta
        for project in spec["projects"]:
            faults=TS_FAULTS if case=="typescript" else MAIN_FAULTS
            for fault in faults:
                if not supported(fault,meta["expected_digests"][project]):
                    continue
                for arm in MAIN_ARMS:
                    key=(case,project,fault,17,arm)
                    expected[key]="primary"
                if case!="typescript":
                    expected[(case,project,fault,17,"guarded_hash")]="guarded"
    # Sparse additional repeated-location checks: seeds 29/43, same projects.
    for case,projects in (("libraries",["ts-pattern","zod"]),
                         ("andrewthauer",["api"]),("quramy",["x-cli"])):
        for p in projects:
            for f in ("delete_nested_js","corrupt_js","extra_stale"):
                for seed in (29,43):
                    for arm in ("standard","selective_path","guarded_hash","clean_all","full_cache"):
                        expected[(case,p,f,seed,arm)]="sensitivity"
    # Separate TS native guarded runs, if already executed.
    for p in CASE_SPECS["typescript"]["projects"]:
        for f in TS_FAULTS:
            expected[("typescript",p,f,17,"guarded_hash")]="guarded_ts"
    missing=[k for k in expected if k not in observations]
    unexpected=[k for k in observations if k not in expected]
    violations=[]
    for key,item in observations.items():
        before=item["before"]
        fault=item["fault"]
        if fault not in ("intact","buildinfo_missing") and sum(before.values())==0:
            violations.append({"key":key,"error":"damage was not injected"})
        if fault=="intact" and sum(before.values())!=0:
            violations.append({"key":key,"error":"negative control is damaged"})
        if item["arm"] in ("selective_hash","guarded_hash","clean_all","full_cache") and not item["correct"]:
            violations.append({"key":key,"error":"strong recovery oracle mismatch"})
    required_supplements=("wireit/observations.json","turborepo/observations.json",
                          "input_drift_probe.json","api_incremental_probe.json",
                          "version_holdout.json","public_issue_audit.json",
                          "github_actions_aggregate.json")
    optional_external=("public_ci_observability.json","public_ci_incident_evidence.json",
                       "gha_harness_local_smoke.json")
    supplements={}
    for f in required_supplements+optional_external:
        p=results/f
        supplements[f]=p.is_file()
    if supplements["wireit/observations.json"]:
        rows=json.loads((results/"wireit/observations.json").read_text())["observations"]
        for r in rows:
            want=r["profile"]!="none"
            if r["correct"]!=want:
                violations.append({"key":"wireit", "error":f"Unexpected {r['project']}/{r['profile']}/{r['fault']}"})
    if supplements["turborepo/observations.json"]:
        rows=json.loads((results/"turborepo/observations.json").read_text())["observations"]
        for r in rows:
            want=r["cache"]=="available"
            if r["correct"]!=want:
                violations.append({"key":"turbo", "error":f"Unexpected {r['project']}/{r['cache']}/{r['fault']}"})
    if supplements["input_drift_probe.json"]:
        rows=json.loads((results/"input_drift_probe.json").read_text())["observations"]
        for r in rows:
            want=r["arm"] in ("invalidate_all","guarded_hash","clean_all")
            if r["correct_against_new_clean_oracle"]!=want:
                violations.append({"key":"drift", "error":f"Unexpected {r['case']}/{r['arm']}"})
    if supplements["api_incremental_probe.json"]:
        rows=json.loads((results/"api_incremental_probe.json").read_text())["observations"]
        for r in rows:
            vals=[x["jsExists"] for x in r.get("states",[])]
            if r["returncode"]!=0 or vals!=[True,False,True]:
                violations.append({"key":"api", "error":f"Unexpected TypeScript {r['version']} API output: {vals}"})
    if supplements["version_holdout.json"]:
        hold=json.loads((results/"version_holdout.json").read_text())
        if not hold.get("independent_oracle",{}).get("exact"):
            violations.append({"key":"ts6", "error":"Clean TS6 oracle mismatch"})
        for r in hold.get("trials",[]):
            if r["arm"] in ("selective_hash","clean_all","full_cache") and not r["correct"]:
                violations.append({"key":"ts6", "error":str((r["project"],r["fault"],r["arm"]))})
    if supplements["public_ci_observability.json"]:
        ci=json.loads((results/"public_ci_observability.json").read_text())
        rows=ci.get("runs",[])
        if (ci.get("run_count_api")!=17 or len(rows)!=17 or
                len({r.get("run_id") for r in rows})!=17 or
                ci.get("success_runs")!=17 or
                ci.get("real_cache_regression_test_passed_runs")!=17 or
                any(r.get("runner_image")!="ubuntu-22.04" or
                    r.get("output_manifest_or_n21_fault_verified") is not False or
                    not r.get("real_cache_test_success") for r in rows)):
            violations.append({"key":"public_ci", "error":"Historical GitHub-hosted cohort audit inconsistent"})
    if supplements["public_ci_incident_evidence.json"]:
        incident=json.loads((results/"public_ci_incident_evidence.json").read_text())
        if (incident.get("strict_natural_ci_cases_with_complete_raw_logs")!=0 or
                incident.get("strict_n21_incidence_denominator") is not None or
                incident.get("natural_ci_first_person_reports_without_logs")!=1):
            violations.append({"key":"incident", "error":"Cannot claim a complete natural incident or denominator"})
    if supplements["gha_harness_local_smoke.json"]:
        smoke=json.loads((results/"gha_harness_local_smoke.json").read_text())
        rows=smoke.get("observations",[])
        if (len(rows)!=16 or smoke.get("expected_rows")!=16 or
                any(r.get("observed_in_github_actions") or
                    (r["strategy"] in ("guarded_sha","clean_all") and
                     not r["correct_against_trusted_oracle"]) for r in rows)):
            violations.append({"key":"gha_smoke", "error":"Local harness smoke incomplete or mislabeled"})
    if supplements["github_actions_aggregate.json"]:
        gha=json.loads((results/"github_actions_aggregate.json").read_text())
        rows=gha.get("rows",[])
        run_ids=gha.get("included_runs",[])
        per_run=Counter(r.get("run_id") for r in rows)
        if (len(run_ids)!=3 or len(set(run_ids))!=3 or
                gha.get("run_count")!=3 or gha.get("actual_runner_jobs")!=45 or
                gha.get("verified_strategy_records")!=42 or len(rows)!=42 or
                per_run!=Counter({r:14 for r in run_ids}) or
                sum(bool(r.get("correct")) for r in rows)!=30 or
                gha.get("excluded_pilot_run")!="44237397496" or
                gha.get("natural_ci_incidents_with_full_logs")!=0 or
                gha.get("valid_n21_incidence_denominator") is not None or
                gha.get("industrial_roi_measured") is not False):
            violations.append({"key":"github_actions", "error":"Real runner 3x14 matrix evidence inconsistent or overstated"})
    report={"expected_grid_size":len(expected),"observed_trials":len(observations),
        "missing_grid_cells":len(missing),"unexpected_grid_cells":len(unexpected),
        "duplicate_keys":duplicates,"missing":missing[:60],"unexpected":unexpected[:60],
        "violations":violations,"supplements":supplements,
        "independent_source_repos":7,"project_units":sum(len(x["projects"]) for x in CASE_SPECS.values()),
        "source_units_total":sum(sum(x["source_units"].values()) for x in all_meta.values()),
        "emitted_file_total":sum(sum(x["outputs"].values()) for x in all_meta.values()),
        "eligible_for_FSE_industry_complete":False,
        "unresolved": [
            "One first-person natural CI impact report, but no complete natural incident run/job/cache/output logs",
            "No valid N21 partial-output incidence denominator (17 real GitHub-hosted Wireit cache tests lack output SHA manifests)",
            "Three real GitHub-hosted Attest benchmark runs cover only a controlled two-project/four-output fixture, not production-scale industrial timing",
            "No verified organization-specific engineering hours, operational burden, or business-impact measurement for an actual N21 rollout"]}
    report["internal_checks_passed"]=(not missing and not unexpected and not duplicates and not violations and
                                      all(supplements[f] for f in required_supplements))
    (results/"VALIDATION_REPORT.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    print(f"{len(observations)} unique trials / {len(expected)} expected; missing={len(missing)}, "
          f"unexpected={len(unexpected)}, violations={len(violations)}; internal_pass={report['internal_checks_passed']}")
    if not report["internal_checks_passed"]:
        raise SystemExit(1)

if __name__=="__main__":
    main()
