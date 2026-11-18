"""Analysis tables and project-cluster confidence intervals for N04."""

from __future__ import annotations

import argparse
import collections
import csv
import json
import random
from pathlib import Path

from n04_benchmark import load_pairs, test_statistics


def rows(path:Path):
    with path.open(newline="",encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_table(path:Path,data:list[dict]):
    if not data:
        return
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(data[0]))
        w.writeheader();w.writerows(data)


def ci_by_project(items:list[dict], numerator, denominator, seed:int=2027):
    by_project=collections.defaultdict(list)
    for r in items:
        by_project[r["project"]].append(r)
    projects=sorted(by_project)
    aggregate={p:(sum(numerator(r) for r in group),sum(denominator(r) for r in group))
               for p,group in by_project.items()}
    def calc(cluster):
        num=sum(aggregate[p][0] for p in cluster)
        den=sum(aggregate[p][1] for p in cluster)
        return num/den if den else None
    point=calc(projects)
    rng=random.Random(seed)
    vals=[calc([rng.choice(projects) for _ in projects]) for _ in range(1500)]
    vals=sorted(x for x in vals if x is not None)
    return {"point":point,"ci95":[vals[int(.025*len(vals))],vals[int(.975*len(vals))-1]] if vals else None,
            "clusters":len(projects)}


def main(migration:Path, history:Path, dataset:Path, dest:Path):
    dest.mkdir(parents=True,exist_ok=True)
    pairs,_=load_pairs(dataset)
    types={o.uid:{"method_changed":o.name!=n.name,
                  "class_changed":o.cls!=n.cls,"file_changed":o.file!=n.file,
                  "full_node_changed":(o.name,o.cls,o.file)!=(n.name,n.cls,n.file)} for o,n in pairs}
    p=rows(migration)
    for x in p:
        x.update(types.get(x["uid"],{}))
    methods=sorted(set(r["method"] for r in p))
    category=[]
    for typ in ("method_changed","class_changed","file_changed","full_node_changed"):
        for group in (False,True):
            for method in methods:
                segment=[x for x in p if x["method"]==method and x.get(typ)==group]
                if segment:
                    n=len(segment)
                    category.append({"category":typ,"value":group,"method":method,
                                     "events_over_three_seeds":n,
                                     "distinct_test_transitions":len(set(x["uid"] for x in segment)),
                                     "projects":len(set(x["project"] for x in segment)),
                                     "recovery_rate":sum(x["present_pred"]==x["uid"] for x in segment)/n,
                                     "combined_false_transfer":sum(bool(x["absent_pred"]) or (bool(x["present_pred"]) and x["present_pred"]!=x["uid"]) for x in segment)/(2*n)})
    write_table(dest/"identity_change_subsets.csv",category)

    project_rows=[]
    for method in methods:
        for project in sorted(set(x["project"] for x in p)):
            group=[x for x in p if x["method"]==method and x["project"]==project]
            t=test_statistics(group)
            project_rows.append({"method":method,"project":project,"repeated_events":t["pairs"],
                                 "distinct_events":len(set(x["uid"] for x in group)),
                                 "recovery_rate":t["recovery_rate"],
                                 "false_transfer_rate":t["combined_false_transfer_rate"]})
    write_table(dest/"per_project.csv",project_rows)

    h=rows(history)
    for x in h:
        for key in ("future_flaky_10","preserved_quarantine","reset_quarantine","globally_flaky_30"):
            x[key]=(x[key]=="True")
    missed_delta=ci_by_project(h,
        lambda x: int(x["future_flaky_10"] and (not x["reset_quarantine"]))-int(x["future_flaky_10"] and (not x["preserved_quarantine"])),
        lambda x: int(x["future_flaky_10"]))
    lower_only=[x for x in p if x["method"] in ("method_name","semantic_anchor")]
    per_seed_summary=[]
    for method in ("method_name","semantic_anchor"):
        for s in (17,29,43):
            data=[x for x in lower_only if x["method"]==method and x["seed"]==str(s)]
            stat=test_statistics(data)
            per_seed_summary.append({"seed":s,"method":method,
                                     "events":stat["pairs"],
                                     "recovery_rate":stat["recovery_rate"],
                                     "false_transfer_rate":stat["combined_false_transfer_rate"]})
    write_table(dest/"per_seed_primary.csv",per_seed_summary)
    report={"migration":{"source_pairs":len(pairs),
                          "method_changes_total":sum(x["method_changed"] for x in types.values()),
                          "class_changes_total":sum(x["class_changed"] for x in types.values()),
                          "file_changes_total":sum(x["file_changed"] for x in types.values()),
                          "pairing_by_index_curated":True},
            "history_replay":{"missed_future_flaky_increase_reset_minus_preserved":missed_delta,
                              "unit":"test x commit x seed; project clusters resampled; outcomes genuine, reset artificial"},
            "multiple_testing_warning":"Subgroup analyses are exploratory; three resamplings are not independent external replications.",
            "posthoc_model_warning":"hybrid_posthoc introduced after initial result inspection; do not use as a confirmatory success claim."}
    (dest/"analysis.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))


if __name__=="__main__":
    q=argparse.ArgumentParser()
    q.add_argument("--migration",type=Path,default=Path("results/migration_benchmark/predictions.csv"))
    q.add_argument("--history",type=Path,default=Path("results/history_replay/real_history_decisions.csv"))
    q.add_argument("--dataset",type=Path,default=Path("data/TestMigrationsInPy/projects"))
    q.add_argument("--out",type=Path,default=Path("results/analysis"))
    a=q.parse_args()
    main(a.migration,a.history,a.dataset,a.out)
