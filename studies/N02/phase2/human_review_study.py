#!/usr/bin/env python3
"""Genuine human-review stopwatch, no artificial reviewers or timing estimates.

Every participant sees the actual 27-case historical-Release helm-diff baseline.
Randomly allocated trials include the docs URL; the intervention arm ALSO gets
CID alerts and their evidence. Human time and decisions are measured directly.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import random
import statistics
import time

import yaml

ROOT=Path(__file__).resolve().parent.parent
PHASE=ROOT/"phase2"
OUT=PHASE/"results"/"human_review_observations.jsonl"


def tasks():
    bundle=yaml.safe_load((ROOT/"cases.yaml").read_text())
    case_meta={r["id"]:r for r in bundle["cases"]}
    case_scores={r["id"]:r for r in (
        json.loads(x) for x in (ROOT/"results/case_results.jsonl").read_text().splitlines())}
    diffs={r["case"]:r for r in json.loads(
        (PHASE/"results/helm_diff_replay.json").read_text())["rows"]}
    result={}
    for ident,case in case_meta.items():
        family=case["family"]
        result[ident]={"id":ident,"family":family,"label":case["label"],
                       "old_user":case["old_user"],"intent":case.get("intent",""),
                       "docs":bundle["families"][family]["documentation"],
                       "diff":PHASE/"results"/"helm_diff_transcripts"/diffs[ident]["transcript"],
                       "score":case_scores[ident]}
    return result


def assign(participant_id:str,alltasks:dict)->list[tuple[str,str]]:
    seed=int.from_bytes(hashlib.sha256(("n02-human-20261115/"+participant_id).encode()).digest()[:8],"big")
    rng=random.Random(seed)
    positives=[p for p in alltasks if alltasks[p]["label"]=="positive"]
    negatives=[n for n in alltasks if alltasks[n]["label"]!="positive"]
    selected=rng.sample(positives,4)+rng.sample(negatives,6)
    rng.shuffle(selected)
    arms=["diff_docs","diff_docs_plus_cid"]*5
    rng.shuffle(arms)
    return list(zip(selected,arms))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--participant-id",required=True,help="Local pseudonym; NOT actual name")
    ap.add_argument("--dry-run",action="store_true")
    args=ap.parse_args()
    trials=tasks()
    assignments=assign(args.participant_id,trials)
    pseudonym=hashlib.sha256(args.participant_id.encode()).hexdigest()[:16]
    if args.dry_run:
        print("Dry run ONLY, no timers or research observations recorded.")
        print(json.dumps([{"trial":i+1,"case":ident,"arm":arm}
                          for i,(ident,arm) in enumerate(assignments)],indent=2))
        return
    if OUT.exists():
        previous=[json.loads(x) for x in OUT.read_text().splitlines() if x.strip()]
        if any(o.get("participant")==pseudonym for o in previous):
            raise SystemExit("Participant already recorded; do not silently duplicate their sessions.")
    print("N02 research participation: You will inspect public synthetic release scenarios.")
    print("Your participation is voluntary; no real-world private Kubernetes values are shown.")
    print("Only a pseudonym hash, trial choices, decisions and elapsed seconds are saved locally.")
    if input("I consent to the local anonymous timing study [type yes]: ").strip().lower()!="yes":
        raise SystemExit("Consent not given; no observations written.")
    OUT.parent.mkdir(parents=True,exist_ok=True)
    for i,(ident,arm) in enumerate(assignments,1):
        trial=trials[ident]
        print(f"\n=== Task {i}/10; family={trial['family']}; interface={arm} ===")
        print("Historical user configuration (this is NOT a real customer's release):")
        print(yaml.safe_dump(trial["old_user"],sort_keys=False).strip())
        print("The installed chart is being upgraded. Decide if user behavior is at risk.")
        print("Open the REAL native helm-diff output while you work:")
        print(trial["diff"])
        print("Official migration / chart documentation:")
        print(trial["docs"])
        if arm=="diff_docs_plus_cid":
            r=trial["score"]
            print("\nCID signal (extra information on top of diff and docs):")
            print(json.dumps({
                "risk_alert":r["score_counterfactual"]>=5,
                "risk_score":r["score_counterfactual"],
                "lost_effect_positions":r["lost_effect_positions"],
                "vanished_user_literals":r["vanished_operator_literals"],
            },indent=2))
        else:
            print("\nBaseline: use only the native helm-diff and upstream docs.")
        input("Press Enter to begin timing; then inspect diff/docs and enter a decision...")
        started=time.monotonic()
        choice=""
        while choice not in ("risk","safe","unsure"):
            choice=input("Risk of lost operator intent? [risk/safe/unsure]: ").strip().lower()
        remediation=input("If risk, how would you migrate; otherwise enter none: ").strip()
        duration=time.monotonic()-started
        record={"participant":pseudonym,"trial":i,"case":ident,"family":trial["family"],
                "arm":arm,"decision":choice,"remediation":remediation,
                "elapsed_seconds":round(duration,3),
                "measurement":"real human elapsed monotonic seconds, not estimated",
                "version":"N02 human stopwatch protocol v1"}
        with OUT.open("a") as f:
            f.write(json.dumps(record,ensure_ascii=False)+"\n")
        print(f"Saved observation. Review elapsed time {duration:.1f}s.")
    print("Thank you. No oracle labels were shown during the review.")


if __name__=="__main__":
    main()
