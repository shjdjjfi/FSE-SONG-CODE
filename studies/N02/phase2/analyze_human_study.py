#!/usr/bin/env python3
"""Descriptive audit of ACTUAL participant observations; no surrogate times."""
from __future__ import annotations
import json
from pathlib import Path
import statistics
import yaml

ROOT=Path(__file__).resolve().parent.parent
PATH=ROOT/"phase2/results/human_review_observations.jsonl"
DEST=ROOT/"phase2/results/human_review_summary.json"


def main():
    truth={r["id"]:r["label"]=="positive" for r in
           yaml.safe_load((ROOT/"cases.yaml").read_text())["cases"]}
    data=[json.loads(x) for x in PATH.read_text().splitlines() if x.strip()] if PATH.exists() else []
    summary={"observations":len(data),"actual_human_participants":
             len({r["participant"] for r in data}),"arms":{}}
    for arm in ("diff_docs","diff_docs_plus_cid"):
        sub=[x for x in data if x["arm"]==arm]
        positives=[x for x in sub if truth[x["case"]]]
        negatives=[x for x in sub if not truth[x["case"]]]
        tp=sum(x["decision"]=="risk" for x in positives)
        fp=sum(x["decision"]=="risk" for x in negatives)
        seconds=[x["elapsed_seconds"] for x in sub]
        summary["arms"][arm]={
            "judgments":len(sub),"positive_judgments":len(positives),
            "negative_judgments":len(negatives),"tp":tp,"fp":fp,
            "recall":tp/len(positives) if positives else None,
            "false_alarm_rate":fp/len(negatives) if negatives else None,
            "median_review_seconds":statistics.median(seconds) if seconds else None,
            "sum_review_minutes":sum(seconds)/60 if seconds else None}
    summary["status"]="ACTUAL_OBSERVATIONS" if data else "NO_HUMAN_PARTICIPANTS; no human-time evidence"
    summary["comparative_claim_allowed"]=False
    if data:
        summary["note"]="Small nonindependent randomized tasks; preregister power and analyze by human reviewer before claiming a difference."
    DEST.write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))


if __name__=="__main__":
    main()
