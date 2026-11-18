#!/usr/bin/env python3
"""Fail-closed QA on all material Phase-3 claims and their stored evidence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
HERE=ROOT/"phase3"
OUT=HERE/"results"


def sha256(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    original_hash="64381bae392d703b7fbc20159dbaa02cf9cb6591412eb8249e6bf1f55fbf2b2e"
    assert sha256(ROOT/"scripts/run_study.py")==original_hash
    cases=[json.loads(line) for line in (OUT/"challenge_cases.jsonl").read_text().splitlines()]
    assert len(cases)==10 and len({x["id"] for x in cases})==10
    bystatus={s:sum(x["status"]==s for x in cases) for s in {
        "confirmed_manifest_positive","confirmed_preserved_control",
        "invalid_or_nonrenderable_oracle","unrepaired_or_unverified_change"}}
    assert bystatus=={
        "confirmed_manifest_positive":6,"confirmed_preserved_control":3,
        "invalid_or_nonrenderable_oracle":1,"unrepaired_or_unverified_change":0}
    for record in cases:
        if record["status"]=="confirmed_manifest_positive":
            assert all(record["render"][x]["ok"] for x in ("old","new","repair"))
            assert [record["observations"][x]["pass"]
                    for x in ("old","new","repair")]==[True,False,True]
    s=json.loads((OUT/"challenge_summary.json").read_text())
    for name,hashvalue in s["chart_sha256"].items():
        archive=ROOT/name
        assert archive.is_file() and sha256(archive)==hashvalue,(name,"chart hash differs")
    a=json.loads((OUT/"challenge_statistical_audit.json").read_text())
    assert a["cid"]=={
        "tp":3,"fn":3,"fp":0,"sensitivity":0.5,
        "sensitivity_wilson95":[0.18762,0.81238],
        "fpr":0.,"negative_specificity_wilson95":[0.4385,1.0]}
    assert a["human_reviewer_count"]==0 and a["human_review_minutes"] is None
    assert a["all_negative_controls_across_phase2_and_phase3"]["n"]==75
    assert a["all_negative_controls_across_phase2_and_phase3"]["fp"]==0
    nd=json.loads((OUT/"native_diff_external.json").read_text())
    valid=[x for x in nd["cases"] if x["status"]=="plugin_executed"]
    assert len(valid)==9 and all(x["exit_code"]==0 for x in valid)
    assert sum(x["lines"] for x in valid)==6110
    for d in valid:
        path=OUT/"helm_diff_transcripts"/d["transcript"]
        assert path.is_file()
        assert len(path.read_text().splitlines())==d["lines"]
        assert any("/secrets" in request for request in d["api_reads"])
    scan=json.loads((OUT/"blind_schema_summary.json").read_text())
    assert len(scan["pairs"])==9 and scan["total_candidates"]==6
    assert scan["total_literal_loss_candidates"]==4
    explorer=json.loads((OUT/"exploratory_validated_discoveries.json").read_text())
    assert len(explorer)==2
    assert all(x["valid_manifest_contract_loss"] and x["frozen_method"]["cid_alert"]
               for x in explorer)
    assert (HERE/"EXPERIMENT_REPORT_PHASE3_CN.md").exists()
    assert (HERE/"AI_EXPERT_DESK_AUDIT_CN.md").exists()
    human=ROOT/"phase2/results/human_review_observations.jsonl"
    if human.exists():
        assert not human.read_text().strip(),"NEW HUMAN RECORDS: verify provenance manually"
    summary={"verified":True,"cases":10,"valid_positives":6,
             "phase3_negative_controls":3,"previous_negative_controls":72,
             "native_diff_transcripts":9,"native_diff_lines":6110,
             "exploratory_validated_cases":2,"human_participants":0,
             "toolchain_not_live_kubernetes":True,
             "frozen_sha256":original_hash}
    (OUT/"verification.json").write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))


if __name__=="__main__":main()
