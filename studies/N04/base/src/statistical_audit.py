"""Conservative confidence audit, exact bounds, and paired cluster effect.

Intervals are descriptive: source-derived positive target assignments do not
have independently adjudicated maintainer labels. Revisions in an event are
not IID Bernoulli trials; event bootstrap is the primary paired interval.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import random

from scipy.stats import beta


def clopper_pearson(k: int, n: int, alpha=.05):
    if n == 0: return [None, None]
    return [round(float(beta.ppf(alpha/2,k,n-k+1)),4) if k else 0.0,
            round(float(beta.ppf(1-alpha/2,k+1,n-k)),4) if k<n else 1.0]


def paired_bootstrap(d: dict, focus="guarded_lineage", reference="git_path_same_method", draws=3000):
    all_rows = d["predictions"]
    choices = {}
    for row in all_rows:
        if row["arm"] not in (focus, reference):continue
        if row["status"]!="MovedOrRenamed" or not row["gold_target"] or row["group_ambiguous"]:continue
        choices.setdefault((row["event_id"],row["case_id"]), {})[row["arm"]]=int(row["correct_single_target"])
    paired = [(event,arms[focus],arms[reference]) for (event,_),arms in choices.items()
              if focus in arms and reference in arms]
    events=sorted({x[0] for x in paired})
    by_event={event:[row for row in paired if row[0]==event] for event in events}
    deltas=[]
    for seed in (17,29,43):
        rand=random.Random(seed)
        for _ in range(draws):
            sample=[x for event in (rand.choice(events) for _ in events)
                    for x in by_event[event]]
            if sample:
                deltas.append(sum(x[1]-x[2] for x in sample)/len(sample))
    deltas.sort()
    observed=sum(x[1]-x[2] for x in paired)/len(paired)
    return {"focus":focus,"baseline":reference,
            "paired_positive_instances":len(paired),"independent_migration_clusters":len(events),
            "delta_recall":round(observed,4),"event_bootstrap_95":
            [round(deltas[int(.025*(len(deltas)-1))],4),round(deltas[int(.975*(len(deltas)-1))],4)],
            "bootstrap_seeds":[17,29,43],"draws_per_seed":draws}


def analyze(d: dict):
    rows=[]
    for r in d["summary"]:
        k=r["false_inheritance_on_deleted"];n=r["deleted_negative"]
        k2=r["false_inheritance_on_uncontested_deleted"];n2=r["uncontested_deleted_negative"]
        rows.append({"arm":r["arm"],
                     "positive_recall_exact_95":clopper_pearson(r["correct_individual_links"],r["eligible_individual_positive"]),
                     "all_deleted_false_rate_exact_95":clopper_pearson(k,n),
                     "uncontested_deleted_false_rate_exact_95":clopper_pearson(k2,n2)})
    guard=next(x for x in d["summary"] if x["arm"]=="guarded_lineage")
    upper=clopper_pearson(guard["false_inheritance_on_uncontested_deleted"],guard["uncontested_deleted_negative"])[1]
    return {"intervals_note":"Exact binomial intervals are descriptive and optimistic if cases cluster; migration/event-cluster bootstrap is reported separately",
            "calibration_target": {"maximum_false_inheritance_rate":.02,
              "meets_target_on_raw_IDoFT_deleted_labels":guard["deleted_false_rate"]<=.02,
              "meets_target_on_uncontested_point_estimate":guard["uncontested_deleted_false_rate"]<=.02,
              "statistically_certifies_target_with_95_percent_confidence":upper<=.02,
              "interpretation":"FAILED: 4/9 raw false transfers, and 0/5 filtered has an upper 95% bound far above 2%"},
            "binomial_intervals":rows,"paired_effects":[paired_bootstrap(d),paired_bootstrap(d,reference="name_and_context"),paired_bootstrap(d,reference="exact_body")]}


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--evaluation",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    result=analyze(json.loads(a.evaluation.read_text()))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result["calibration_target"],indent=2))
