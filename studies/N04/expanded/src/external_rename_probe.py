"""Independent, name-only stress probe from ICPC 2021 public Excel tables.

These rows are published Rename Method refactoring annotations. They DO NOT
prove that a flaky-test history can safely be transferred: renamed test names
can negate the original behavior, and the XLSX lacks runnable old/new sources.
We never advertise this as an end-to-end lineage or CI experiment.

Requires read-only openpyxl and the CC BY 4.0 author spreadsheet, available at
https://zenodo.org/records/4608143 (ICPC2021-Public.xlsx).
"""

from __future__ import annotations

import argparse
import collections
import csv
import difflib
import hashlib
import json
import random
import re
from pathlib import Path

import openpyxl

METHODS=("exact_method_name", "normalized_method_name", "fuzzy_edit",
         "fuzzy_token", "hybrid_lexical", "hybrid_polarity_veto")


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def stem(name):
    return re.sub(r"(?i)^test[_-]?", "", name).replace("_", "").lower()


def words(name):
    separated = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name)
    separated = re.sub(r"([A-Z])([A-Z][a-z])", r"\1 \2", separated)
    return tuple(x.lower() for x in re.findall(r"[A-Za-z0-9]+", separated))


def polarity_changed(a,b):
    """Conservative syntactic warning, not ground-truth semantic equivalence."""
    def neg(parts):
        return any(x in {"not","never","dont","doesnt","shouldnt","cannot","cant","without"}
                   for x in parts)
    return neg(words(a)) != neg(words(b))


def sim(a,b):
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


def score(old,new,method):
    if method == "exact_method_name":
        return float(old == new)
    if method == "normalized_method_name":
        return float(bool(stem(old)) and stem(old) == stem(new))
    edit = sim(stem(old),stem(new))
    wa, wb=set(words(old)),set(words(new))
    jac=len(wa&wb)/len(wa|wb) if wa|wb else 0.0
    if method == "fuzzy_edit":
        return edit
    if method == "fuzzy_token":
        return jac
    if method in ("hybrid_lexical", "hybrid_polarity_veto"):
        val=.75*edit+.25*jac
        if method=="hybrid_polarity_veto" and polarity_changed(old,new):
            return 0.0
        return val
    raise ValueError(method)


def load_xlsx(p):
    w=openpyxl.load_workbook(p,read_only=True,data_only=True)
    records={}
    duplicates=collections.Counter()
    for sheet in w.worksheets:
        if not sheet.title.startswith("Pattern-"):
            continue
        for row in sheet.iter_rows(min_row=4,values_only=True):
            if len(row) < 5 or not isinstance(row[1],int) or not isinstance(row[2],str) or not isinstance(row[4],str):
                continue
            key=str(row[1])
            record={"refactoring_id":key,"before":row[2],"after":row[4]}
            if key in records and records[key]!=record:
                raise RuntimeError(f"Conflicting ICPC refactoring id {key}")
            duplicates[key]+=1
            records[key]=record
    return sorted(records.values(),key=lambda x:x["refactoring_id"]),{
        "source_xlsx_sha256":sha(p.read_bytes()),"total_sheet_rows":sum(duplicates.values()),
        "unique_refactoring_ids":len(records),"ids_repeated_across_sheets":sum(n>1 for n in duplicates.values()),
        "duplicate_new_names":sum(v>1 for v in collections.Counter(x["after"] for x in records.values()).values()),
        "polarity_flip_warnings":sum(polarity_changed(x["before"],x["after"]) for x in records.values()),
    }


def candidates(rows,seed,k=16):
    out=[]
    for q in rows:
        old=q["before"]
        other=[x for x in rows if x["refactoring_id"] != q["refactoring_id"]]
        # All distractor names are real annotated names. The selection is
        # intentionally difficult for fuzzy lexicons; no labels used to rank.
        other.sort(key=lambda x:(-sim(stem(old),stem(x["after"])),x["refactoring_id"]))
        hard=other[:max(1,(k-1)//2)]
        rng=random.Random(int(sha(f"{seed}:{q['refactoring_id']}".encode())[:15],16))
        rest=other[len(hard):]
        rng.shuffle(rest)
        distractors=hard+rest[:k-1-len(hard)]
        out.append({"refactoring_id":q["refactoring_id"],"old":old,
                    "present":[q]+distractors,"absent":distractors})
    return out


def top(q,method,mode):
    z=sorted(((score(q["old"],x["after"],method),x["refactoring_id"]) for x in q[mode]),reverse=True)
    if not z:
        return (0.,0.,"")
    return (z[0][0],z[0][0]-(z[1][0] if len(z)>1 else 0),z[0][1])


def take(t,th,margin):
    sc,gap,ref=t
    return ref if sc >=th and gap > margin+1e-12 else ""


def metrics(pred):
    n=len(pred)
    recovered=sum(x["pred"]==x["id"] for x in pred)
    present_wrong=sum(bool(x["pred"]) and x["pred"]!=x["id"] for x in pred)
    absent_wrong=sum(bool(x["absent_pred"]) for x in pred)
    return {"cases":n,"recovered":recovered,"recovery_rate":recovered/n if n else 0,
            "present_wrong":present_wrong,"absent_wrong":absent_wrong,
            "combined_false_link_rate":(present_wrong+absent_wrong)/(2*n) if n else 0}


def calibrate(train,precomp,method):
    best=None
    for i in range(0,101,2):
        th=i/100
        for m in (0,.015,.04,.075,.125,.2):
            judged=[{"id":q["refactoring_id"],
                     "pred":take(precomp[(q["refactoring_id"],method,"present")],th,m),
                     "absent_pred":take(precomp[(q["refactoring_id"],method,"absent")],th,m)} for q in train]
            val=metrics(judged)
            if val["combined_false_link_rate"] <=.02+1e-12:
                key=(val["recovery_rate"],-val["combined_false_link_rate"],th,m)
                if best is None or key>best[0]:
                    best=(key,th,m)
    return (best[1],best[2]) if best else (1.01,1.)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--xlsx",type=Path,default=Path("data/ICPC2021-Public.xlsx"))
    p.add_argument("--out",type=Path,default=Path("results/icpc2021_rename_probe"))
    p.add_argument("--seeds",type=int,nargs="+",default=[17,29,43])
    a=p.parse_args()
    rows,audit=load_xlsx(a.xlsx)
    allpred=[]
    tune_rows=[]
    for seed in a.seeds:
        examples=candidates(rows,seed)
        precomp={(q["refactoring_id"],m,mode):top(q,m,mode)
                 for q in examples for m in METHODS for mode in ("present","absent")}
        for fold in range(5):
            train=[q for q in examples if int(sha(q["refactoring_id"].encode())[:7],16)%5 !=fold]
            test=[q for q in examples if int(sha(q["refactoring_id"].encode())[:7],16)%5 ==fold]
            for method in METHODS:
                th,margin=calibrate(train,precomp,method)
                tune_rows.append({"seed":seed,"fold":fold,"method":method,"threshold":th,"margin":margin})
                for q in test:
                    key=q["refactoring_id"]
                    pred=take(precomp[(key,method,"present")],th,margin)
                    absent=take(precomp[(key,method,"absent")],th,margin)
                    allpred.append({"seed":seed,"fold":fold,"id":key,
                                    "method":method,"pred":pred,"absent_pred":absent})
        print("ICPC seed",seed,"complete",flush=True)
    a.out.mkdir(parents=True,exist_ok=True)
    for filename, records in (("predictions.csv",allpred),("tuning.csv",tune_rows)):
        with (a.out/filename).open("w",newline="",encoding="utf-8") as f:
            writer=csv.DictWriter(f,fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)
    report={"dataset":"ICPC 2021 public annotated test method name evolution tables",
            "source":"https://zenodo.org/records/4608143",
            "audit":audit,
            "method_results":{m:metrics([r for r in allpred if r["method"]==m]) for m in METHODS},
            "polarity_flip_examples":[r for r in rows if polarity_changed(r["before"],r["after"])][:30],
            "unit":"annotated renamed-method IDs, NOT underlying projects (project IDs absent)",
            "validity":["Source XLSX contains published old/new names but not per-commit runnable source.",
                        "Renamed method association is not a validated safe quarantine-history transfer.",
                        "Candidate negatives and target-absent cases are generated stress probes, not real CI failures.",
                        "Folds can contain same unknown source projects: no claim of held-out projects.",
                        "Polarity changes are warning heuristics, not proof of changed semantics."]}
    (a.out/"results.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({k:{"recovery":v["recovery_rate"],"false":v["combined_false_link_rate"]}
                      for k,v in report["method_results"].items()},indent=2))


if __name__=="__main__":
    main()
