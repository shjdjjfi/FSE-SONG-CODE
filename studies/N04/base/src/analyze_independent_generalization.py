"""Paired event-/repository-level uncertainty on an independent refactoring test.

RefactoringMiner TP is an independently adjudicated *source refactoring* label;
no statement here treats RefactoringMiner FP as quarantine false inheritance.
"""

from __future__ import annotations
import argparse
from collections import defaultdict
import json
from pathlib import Path
import random


def percentile(vals,p):
    vals=sorted(vals)
    return round(vals[max(0,min(len(vals)-1,int((len(vals)-1)*p)))],4)


def rate(rows,arm):
    return sum(x["oracle_target_matched"][arm] for x in rows)/len(rows) if rows else None


def boot(rows,unit,draws=3000,seeds=(17,29,43)):
    grouped=defaultdict(list)
    for row in rows:
        key=row["repository"] if unit=="repository" else row["repository"]+"@"+row["commit"]
        grouped[key].append(row)
    keys=sorted(grouped)
    a=[];b=[];delta=[]
    for seed in seeds:
        rng=random.Random(seed)
        for _ in range(draws):
            sample=[row for k in (rng.choice(keys) for _ in keys) for row in grouped[k]]
            x=rate(sample,"guarded_with_group_guard")
            y=rate(sample,"unique_name")
            a.append(x);b.append(y);delta.append(x-y)
    return {"unit":unit,"clusters":len(keys),"draws_per_seed":draws,"seeds":list(seeds),
            "guarded_recall_95_bootstrap":[percentile(a,.025),percentile(a,.975)],
            "name_only_recall_95_bootstrap":[percentile(b,.025),percentile(b,.975)],
            "guarded_minus_name_95_bootstrap":[percentile(delta,.025),percentile(delta,.975)]}


def main(d):
    tp=[r for r in d["records"] if r["oracle_refactoring_label"]=="TP"]
    old_edges=defaultdict(list)
    for r in tp:
        old_edges[(r["repository"],r["commit"],r["old_id"])].append(r)
    uniquely_resolved=[r for edges in old_edges.values() if len(edges)==1 for r in edges]
    split_olds=[key for key,edges in old_edges.items() if len(edges)>1]
    recall=rate(tp,"guarded_with_group_guard")
    baseline=rate(tp,"unique_name")
    repos=sorted({r["repository"] for r in tp})
    per=[]
    for repo in repos:
        rows=[r for r in tp if r["repository"]==repo]
        per.append({"repository":repo,"n_tp":len(rows),
                    "n_commits":len({r["commit"] for r in rows}),
                    "guarded_recovered":sum(r["oracle_target_matched"]["guarded_with_group_guard"] for r in rows),
                    "name_only_recovered":sum(r["oracle_target_matched"]["unique_name"] for r in rows)})
    out={"warning":"Independent RefactoringMiner method-refactoring TP labels, not quarantined test IDs or ground-truth industrial savings",
         "no_training_on_external_projects":True,
         "n_repositories":len(repos),"n_positive_commits":len({(r["repository"],r["commit"]) for r in tp}),
         "positive_pairs":len(tp),"recovered_guarded":round(recall*len(tp)),
         "recovered_strong_name_baseline":round(baseline*len(tp)),
         "distinct_old_test_ids":len(old_edges),
         "one_to_many_split_old_ids":len(split_olds),
         "split_case_ids":[list(k) for k in split_olds],
         "unique_target_only_cases":len(uniquely_resolved),
         "unique_target_guarded_recall":round(rate(uniquely_resolved,"guarded_with_group_guard"),4),
         "unique_target_name_baseline_recall":round(rate(uniquely_resolved,"unique_name"),4),
         "guarded_minus_name_percentage_points":round((recall-baseline)*100,3),
         "per_repository":per,
         "event_bootstrap":boot(tp,"event"),
         "repository_bootstrap":boot(tp,"repository")}
    return out


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    result=main(json.loads(a.input.read_text()))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))
