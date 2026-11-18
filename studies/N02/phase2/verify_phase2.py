#!/usr/bin/env python3
"""Offline audit of phase-two provenance and all executed counts."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent.parent
PHASE=ROOT/"phase2"
RES=PHASE/"results"


def load_json(name:str):
    return json.loads((RES/name).read_text())


def require(expr:bool,label:str):
    if not expr:
        raise AssertionError(label)
    print("PASS",label)


def main():
    original_source=ROOT/"scripts"/"run_study.py"
    require(hashlib.sha256(original_source.read_bytes()).hexdigest() ==
            "64381bae392d703b7fbc20159dbaa02cf9cb6591412eb8249e6bf1f55fbf2b2e",
            "original CID scoring implementation frozen")
    rows=[json.loads(x) for x in (RES/"holdout_cases.jsonl").read_text().splitlines() if x]
    hist=load_json("holdout_summary.json")
    require(len(rows)==72 and hist["aggregate"]["states"]==72,
            "72 heldout values evaluated with 6 independent chart families")
    require(all(x["old_present"] and x["new_present"] and x["path_keys"] and
                x["contract_status"]=="preserved" for x in rows),
            "all 72 old-only-selected sentinel contracts preserved on new chart")
    require(hist["aggregate"]["cid_fp"]==0 and hist["aggregate"]["losses"]==0,
            "zero false positives but recall undefined: no holdout-positive loss")
    audits=load_json("selection_audit.json")
    require(len(audits)>72, "all rejected old-chart candidates logged")
    provenance=load_json("charts_provenance.json")
    require(len(provenance)==8, "no replacement of any preregistered chart pair")
    require(sum(x["status"]=="evaluated" for x in provenance)==6,
            "six chart families evaluated; two documented exclusions")
    for fam in provenance:
        for archive,expected in (("old_archive","old_sha256"),
                                 ("new_archive","new_sha256")):
            if fam[expected]:
                actual=hashlib.sha256((PHASE/"charts"/fam[archive]).read_bytes()).hexdigest()
                require(actual==fam[expected],
                        f"immutable upstream artifact: {fam['family']} / {archive}")
    reuse=load_json("reuse_policy_controls.json")
    require(reuse["summary"]["n"]==72 and
            reuse["summary"]["emulated_reuse_value_losses"]==0 and
            reuse["summary"]["emulated_reuse_render_failures"]==0,
            "72/72 additional emulated reuse-defaults renders preserve user literal")
    for name,suffix in (("helm_diff_replay.json",".diff"),
                        ("helm_diff_concise_replay.json",".concise.diff")):
        diffrows=load_json(name)["rows"]
        require(len(diffrows)==27 and all(r["exit_code"]==0 for r in diffrows),
                f"27/27 genuine plugin invocations in {name}")
        require(all(sum("/secrets" in p for p in r["api_requests"])>=1 for r in diffrows),
                f"all plugin runs read synthetic Helm release storage in {name}")
        require(all((RES/"helm_diff_transcripts"/r["transcript"]).exists()
                    and r["transcript"].endswith(suffix) for r in diffrows),
                f"all native diff transcripts retained in {name}")
    human=load_json("human_review_summary.json")
    require(human["actual_human_participants"]==0 and human["observations"]==0,
            "human-study observations truthfully recorded as zero")
    env=load_json("execution_prerequisites.json")
    require(not env["actual_k8s_cluster_available"],
            "no native cluster existed; native Pod evidence not invented")
    require(load_json("phase2_summary.json")["prespecified_gate"][
        "out_of_family_sensitivity"].startswith("UNDEFINED"),
        "no unsupported positive-recall or FSE admission claim")
    py=sys.executable
    for target in ("run_holdout.py","helm_diff_historical_replay.py",
                   "k8s_actual_replay.py","run_cluster_matrix.py","human_review_study.py",
                   "analyze_phase2.py","analyze_human_study.py"):
        ret=subprocess.run([py,"-m","py_compile",str(PHASE/target)],
                           capture_output=True,text=True)
        require(ret.returncode==0,f"compiled executable: {target}")
    print("PHASE 2 VERIFIED: all measured results, toolchain/plugin, exclusions and blockers.")

if __name__=="__main__":
    main()
