"""Exploratory two-stage identity matching: exact names then renamed fallback.

This method is deliberately a *simple baseline*: it is not presented as a
novel FSE contribution. Thresholds and fallback choices were formulated after
inspecting the previous corpus, so the experiment is not confirmatory.
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
from pathlib import Path

import n04_benchmark as b
from strong_baseline_extension import score_top


def fallback(old, candidates, allow_content):
    top=[]
    for x in candidates:
        if old.name == x.name:
            continue
        seq=b.score(old,x,"source_similarity")
        oa,ob=set(old.tokens),set(x.tokens)
        jac=len(oa&ob)/len(oa|ob) if oa|ob else 0
        canonical=bool(b.norm_name(old.name)) and b.norm_name(old.name)==b.norm_name(x.name)
        if canonical and seq>=.75 and jac>=.60:
            top.append((.90+.10*seq,x.uid,"case_normalization"))
        elif allow_content and seq>=.965 and jac>=.93 and old.assertions==x.assertions:
            top.append((.80+.15*seq,x.uid,"exact_behavioral_anchor"))
    top.sort(reverse=True)
    if not top or (len(top)>1 and top[0][0]-top[1][0]<.06):
        return "",""
    return top[0][1],top[0][2]


def experiment(pairs,seeds):
    allrows=[]
    for seed in seeds:
        examples=b.choose_candidates(pairs,seed,12)
        precomp={q["uid"]:{"name_body_tiebreak":{
            "present":score_top(q["old"],q["present_candidates"],"name_body_tiebreak"),
            "absent":score_top(q["old"],q["absent_candidates"],"name_body_tiebreak")}}
            for q in examples}
        projects=sorted(set(q["project"] for q in examples))
        for project in projects:
            th,margin,_=b.tune([q for q in examples if q["project"]!=project],precomp,"name_body_tiebreak")
            for q in (q for q in examples if q["project"]==project):
                uid=q["uid"]
                matched={}
                for mode in ("present","absent"):
                    selected=b.accept(precomp[uid]["name_body_tiebreak"][mode],th,margin)
                    if mode=="present":
                        candidates=q["present_candidates"]
                    else:
                        candidates=q["absent_candidates"]
                    matched[("name_body_tiebreak",mode)]=(selected,"exact_name_tiebreak" if selected else "")
                    for method, allow_content in (("hierarchical_case",False),
                                                   ("hierarchical_case_content",True)):
                        back,origin=fallback(q["old"],candidates,allow_content) if not selected else ("","")
                        matched[(method,mode)]=(selected or back, "exact_name_tiebreak" if selected else origin)
                for method in ("name_body_tiebreak","hierarchical_case","hierarchical_case_content"):
                    allrows.append({"seed":seed,"project":project,"commit":q["commit"],"uid":uid,
                                    "method":method,"present_pred":matched[(method,"present")][0],
                                    "absent_pred":matched[(method,"absent")][0],
                                    "present_route":matched[(method,"present")][1],
                                    "absent_route":matched[(method,"absent")][1],
                                    "training_threshold":th,"training_margin":margin})
        print("hierarchy seed",seed,"completed",flush=True)
    return allrows


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--dataset",type=Path,default=Path("data/TestMigrationsInPy/projects"))
    p.add_argument("--out",type=Path,default=Path("results/hierarchical_linker"))
    p.add_argument("--seeds",nargs="+",type=int,default=[17,29,43])
    a=p.parse_args()
    pairs,audit=b.load_pairs(a.dataset)
    rows=experiment(pairs,a.seeds)
    a.out.mkdir(parents=True,exist_ok=True)
    b.write_csv(a.out/"predictions.csv",rows)
    summary={m:b.test_statistics([r for r in rows if r["method"]==m])
             for m in ("name_body_tiebreak","hierarchical_case","hierarchical_case_content")}
    diffs={m:b.bootstrap_project_difference(rows,m,"name_body_tiebreak")
           for m in summary if m!="name_body_tiebreak"}
    report={"status":"exploratory post-hoc method; simple-baseline family, not novel",
            "summary":summary,"paired_project_cluster_bootstrap_vs_name_body_tiebreak":diffs,
            "audit":audit["counts"],"seeds":a.seeds,
            "limits":["Rules selected after reviewing prior results.",
                      "No CI quarantine actions observed in benchmark data.",
                      "False transfers from absent cases are controlled candidate removals."]}
    (a.out/"results.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({m:{"recovery":v["recovery_rate"],
                          "false":v["combined_false_transfer_rate"],
                          "cost_5":v["cost_ratio_5"]} for m,v in summary.items()},indent=2))


if __name__=="__main__":
    main()
