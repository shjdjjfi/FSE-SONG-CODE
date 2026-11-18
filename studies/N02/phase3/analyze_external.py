#!/usr/bin/env python3
"""Statistical and evidentiary audit; explicitly not an operator study."""
from __future__ import annotations

from collections import defaultdict
import json
import math
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parent.parent
HERE = ROOT / "phase3"
RESULTS = HERE / "results"


def wilson(success: int, total: int, z: float = 1.959963984540054):
    if not total:
        return None
    p = success / total
    d = 1 + z*z/total
    center = (p + z*z/(2*total)) / d
    margin = z*math.sqrt(p*(1-p)/total + z*z/(4*total*total)) / d
    return [round(max(0., center-margin), 5),
            round(min(1., center+margin), 5)]


def main():
    rows = [json.loads(x) for x in (RESULTS / "challenge_cases.jsonl").read_text().splitlines()]
    diff = {x["case"]: x for x in
            json.loads((RESULTS / "native_diff_external.json").read_text())["cases"]}
    positives = [x for x in rows if x["status"] == "confirmed_manifest_positive"]
    controls = [x for x in rows if x["status"] == "confirmed_preserved_control"]
    valid = positives + controls
    assert len(valid) == 9 and len(positives) == 6 and len(controls) == 3
    assert all(diff[r["id"]]["exit_code"] == 0 for r in valid)
    previous = json.loads((ROOT / "phase2/results/holdout_summary.json").read_text())
    prevcontrols = previous["aggregate"]["controls"]
    prevfalse = previous["aggregate"]["cid_fp"]
    assert prevcontrols == 72 and prevfalse == 0
    tp = sum(r["method"]["cid_alert"] for r in positives)
    fp = sum(r["method"]["cid_alert"] for r in controls)
    missing_tp = sum(r["method"]["missing_default_keys"] > 0 for r in positives)
    missing_fp = sum(r["method"]["missing_default_keys"] > 0 for r in controls)
    byfam = defaultdict(list)
    for row in valid:
        byfam[row["family"]].append(row)
    baseline = {
        "manual_docs_source_explicit_for_each_positive":
            sum(r["source_documented"] for r in positives),
        "native_helm_diff_plugin_success_on_valid_cases":
            sum(diff[r["id"]]["exit_code"] == 0 for r in valid),
        "native_helm_diff_relevant_difference_evidence_available":len(positives),
        "real_operator_detection_measured": False,
        "docs_plus_diff_review_time_measured": False,
        "important": "Documentary availability is NOT observed human sensitivity.",
    }
    rng = random.Random(20261115)
    fams = sorted(byfam)
    boot = []
    for _ in range(10000):
        chosen = [byfam[fams[rng.randrange(len(fams))]] for __ in fams]
        group = [r for block in chosen for r in block]
        ps = [r for r in group if r["status"] == "confirmed_manifest_positive"]
        if ps:
            doc_coverage = sum(r["source_documented"] for r in ps)/len(ps)
            cid_recall = sum(r["method"]["cid_alert"] for r in ps)/len(ps)
            boot.append(100*(cid_recall-doc_coverage))
    boot.sort()
    result = {
        "population": "docs-informed positive-enriched historical chart challenge",
        "valid_n":len(valid), "positive_n":len(positives),"negative_n":len(controls),
        "unconfirmed_or_nonrenderable_n":len(rows)-len(valid),
        "positive_families": sorted({r["family"] for r in positives}),
        "cid": {"tp":tp,"fn":len(positives)-tp,"fp":fp,
                "sensitivity":tp/len(positives),
                "sensitivity_wilson95":wilson(tp,len(positives)),
                "fpr":fp/len(controls),
                "negative_specificity_wilson95":wilson(len(controls)-fp,len(controls))},
        "simple_missing_new_defaults":{
            "tp":missing_tp,"fp":missing_fp,
            "sensitivity":missing_tp/len(positives),
            "delta_cid_minus_simple_pp":100*(tp-missing_tp)/len(positives)},
        "documents_and_diff": baseline,
        "docs_visible_coverage":sum(r["source_documented"] for r in positives)/len(positives),
        "cid_minus_docs_visible_pp":
            100*(tp-sum(r["source_documented"] for r in positives))/len(positives),
        "cid_minus_docs_coverage_cluster_bootstrap_95pp":
            [round(boot[int(.025*len(boot))],3),
             round(boot[int(.975*len(boot))-1],3)],
        "by_family":{
            fam:{"n":len(rs),
                 "positive_n":sum(r["status"]=="confirmed_manifest_positive" for r in rs),
                 "cid_tp":sum(r["method"].get("cid_alert",False) for r in rs
                              if r["status"]=="confirmed_manifest_positive"),
                 "cid_fp":sum(r["method"].get("cid_alert",False) for r in rs
                              if r["status"]=="confirmed_preserved_control")}
            for fam,rs in sorted(byfam.items())},
        "all_negative_controls_across_phase2_and_phase3":{
            "n":prevcontrols+len(controls),"fp":prevfalse+fp,
            "specificity_wilson95":wilson(prevcontrols+len(controls)-prevfalse-fp,
                                         prevcontrols+len(controls))},
        "human_reviewer_count":0,
        "human_review_minutes":None,
        "plus_15pp_human_improvement_demonstrated":False,
        "limitations":[
            "Docs used for selecting candidate positives, so not random unseen incidents.",
            "Loki positives correlated within same upstream major upgrade.",
            "Vault cases are chart template regressions, not renamed value keys.",
            "Helm diffs use synthetic releases on an API stub, no Kubernetes workloads.",
            "Docs availability and clear diff cues are not measured human judgments.",
            "No real participant can be generated by a model role-playing a human.",
        ],
    }
    (RESULTS / "challenge_statistical_audit.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False))
    print(json.dumps({k:v for k,v in result.items() if k not in (
        "limitations", "by_family")}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
