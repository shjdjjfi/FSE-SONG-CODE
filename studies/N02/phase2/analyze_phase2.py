#!/usr/bin/env python3
"""Integrate executed experiment evidence without changing the stopping criteria."""
from __future__ import annotations
from collections import defaultdict
import json
from pathlib import Path
import statistics

ROOT=Path(__file__).resolve().parent.parent
PHASE=ROOT/"phase2"
RESULTS=PHASE/"results"


def j(name:str)->dict:
    return json.loads((RESULTS/name).read_text())


def main():
    old=[json.loads(s) for s in
         (ROOT/"results/case_results.jsonl").read_text().splitlines() if s.strip()]
    train_pos=[x for x in old if x["label"]=="positive"]
    train_neg=[x for x in old if x["label"]!="positive"]
    holdout=j("holdout_summary.json")
    extended=j("reuse_policy_controls.json")
    diff=j("helm_diff_replay.json")["rows"]
    concise=j("helm_diff_concise_replay.json")["rows"]
    human=j("human_review_summary.json")
    environment=j("execution_prerequisites.json")
    fam={}
    for group in (diff,concise):
        for row in group:
            fam.setdefault(row["family"],{"default_lines":[],"concise_lines":[]})
            name="concise_lines" if group is concise else "default_lines"
            fam[row["family"]][name].append(row["stdout_lines"])
    summary={
        "study":"N02 Phase 2, rigorously distinguished synthetic vs live evidence",
        "discovery":{
            "chart_families":5,"cases":len(old),
            "constructed_manifest_positive_cases":len(train_pos),
            "controls":len(train_neg),
            "CID_true_positives":sum(x["score_counterfactual"]>=5 for x in train_pos),
            "CID_false_positives":sum(x["score_counterfactual"]>=5 for x in train_neg),
            "explicitly_actionable_official_docs_hits":
                sum(x.get("documented_actionable_migration",False) for x in train_pos),
            "claim":"development/curated corpus, NOT independent performance",
        },
        "holdout":holdout["aggregate"],
        "holdout_design":holdout["design"],
        "reuse_sensitivity":extended["summary"],
        "native_helm_diff_against_helm_encoded_synthetic_release":{
            "original_plugin_calls":len(diff),
            "successful_original_plugin_calls":sum(r["exit_code"]==0 for r in diff),
            "normalized_context3_calls":len(concise),
            "successful_normalized_context3_calls":sum(r["exit_code"]==0 for r in concise),
            "release_secret_read_verified_for_all":all(
                any("/secrets" in p for p in r["api_requests"]) for r in diff+concise),
            "default_diff_median_lines":statistics.median(r["stdout_lines"] for r in diff),
            "concise_diff_median_lines":statistics.median(r["stdout_lines"] for r in concise),
            "normalized_median_plugin_wall_seconds":round(
                statistics.median(r["plugin_wall_seconds"] for r in concise),3),
            "normalized_total_diff_lines":sum(r["stdout_lines"] for r in concise),
            "by_family":{
                k:{"old_default_median_diff_lines":statistics.median(v["default_lines"]),
                   "normalized_median_diff_lines":statistics.median(v["concise_lines"])}
                for k,v in sorted(fam.items())},
            "important":"Actual binary/plugin and Helm storage format, fake read-only Kubernetes API; not an installed Release in a real cluster",
        },
        "native_kubernetes_runtime":{
            "pods_started":0,"actual_upgrades_executed":0,
            "cluster_available_in_this_environment":
                environment["actual_k8s_cluster_available"],
            "external_cluster_replay_harness_exists":True,
            "status":"BLOCKED - requires user-provided disposable CPU Kubernetes cluster",
        },
        "real_human_review":{
            "reviewers":human["actual_human_participants"],
            "observations":human["observations"],
            "stopwatch_exists":True,
            "status":"BLOCKED - human participants not recruited",
        },
        "prespecified_gate":{
            "two_families_native_silent_runtime_contract_failures":"UNTESTED",
            "CID_over_helm_diff_plus_docs_at_equal_human_minutes_at_least_15_pp":"UNTESTED",
            "out_of_family_sensitivity":"UNDEFINED; 0 positive labels",
            "out_of_family_observed_FPR":holdout["aggregate"]["cid_fpr"],
            "conclusion":"FSE Industry claims not established; do not submit as complete experiment",
        },
    }
    (RESULTS/"phase2_summary.json").write_text(json.dumps(summary,indent=2))
    print(json.dumps({
        "discovery":summary["discovery"],"holdout":summary["holdout"],
        "baseline":summary["native_helm_diff_against_helm_encoded_synthetic_release"],
        "gate":summary["prespecified_gate"]},indent=2))

if __name__=="__main__":
    main()
