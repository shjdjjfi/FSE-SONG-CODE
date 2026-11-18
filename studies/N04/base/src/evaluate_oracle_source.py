"""Source-based test of *candidate verification* on independently adjudicated refactorings.

The human-validated RefactoringMiner oracle supplies candidate pairs, not
production quarantine labels.  It is not an end-to-end new-identity discovery
benchmark.  Source-derived features below never read TP/FP before prediction.
"""

from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from difflib import SequenceMatcher
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from java_source import methods_at


def git(repo,*args):
    p=subprocess.run(["git","-C",str(repo),*args],text=True,capture_output=True)
    if p.returncode:raise RuntimeError(p.stderr[:280])
    return p.stdout.strip()


def tree(repo,sha):
    return git(repo,"ls-tree","-r","--name-only",sha).splitlines()


def resolve(java_paths,fqn):
    full_class=fqn.rsplit(".",1)[0]
    class_file=full_class.replace(".","/")+".java"
    matches=[p for p in java_paths if p.endswith(class_file)]
    if len(matches)==1:return matches[0]
    return None


def inspect(oracle,repos):
    cache={};rows=[];excluded=Counter()
    for entry in oracle["records"]:
        repo=repos.get(entry["repository"])
        if not repo:excluded["repository_not_fetched"]+=1;continue
        sha=entry["commit"]
        key=(str(repo),sha)
        if key not in cache:
            try:
                parent=git(repo,"rev-parse",sha+"^1")
                cache[key]={"before":parent,"after":sha,
                            "oldpaths":tree(repo,parent),"newpaths":tree(repo,sha)}
            except RuntimeError:
                cache[key]=None
        context=cache[key]
        if not context:excluded["commit_parent_unavailable"]+=1;continue
        old_path=resolve(context["oldpaths"],entry["old_id"])
        new_path=resolve(context["newpaths"],entry["new_id"])
        if not old_path or not new_path:
            excluded["unique_source_path_missing"]+=1
            continue
        try:
            old=next((m for m in methods_at(str(repo),context["before"],old_path) if m.fqn==entry["old_id"]),None)
            new=next((m for m in methods_at(str(repo),context["after"],new_path) if m.fqn==entry["new_id"]),None)
        except Exception:
            old=new=None
        if not old or not new:
            excluded["method_missing_or_java_parser"]+=1
            continue
        old_after_path=resolve(context["newpaths"],entry["old_id"])
        new_before_path=resolve(context["oldpaths"],entry["new_id"])
        survives=bool(old_after_path and any(m.fqn==entry["old_id"] for m in
                          methods_at(str(repo),context["after"],old_after_path)))
        preexists=bool(new_before_path and any(m.fqn==entry["new_id"] for m in
                          methods_at(str(repo),context["before"],new_before_path)))
        body_equal=old.body_hash==new.body_hash
        body_similarity=SequenceMatcher(None,old.body[:2500],new.body[:2500]).ratio()
        name_equal=old.name==new.name
        name_similarity=SequenceMatcher(None,old.name,new.name).ratio()
        old_calls=set(old.calls);new_calls=set(new.calls)
        call_equal=old_calls==new_calls
        # Existing N04 validator, applied without any TP/FP input; no
        # training on this independent corpus. Source candidate generation
        # is given here by the third-party oracle, which is a limitation.
        n04_pair=bool(body_equal or (name_equal and body_similarity>=.30))
        continuity_gate=(not survives and not preexists)
        strategies={
            "exact_test_id":entry["old_id"]==entry["new_id"],
            "name_only":name_equal,
            "exact_body":body_equal,
            "n04_pair_unmodified":n04_pair,
            "n04_pair_with_liveness_guard":n04_pair and continuity_gate,
            "strict_body_and_liveness":body_equal and continuity_gate,
            "exact_body_and_calls":body_equal and call_equal,
        }
        rows.append({"repository":entry["repository"],"commit":sha,
                     "oracle_label":entry["label"],
                     "old_id":entry["old_id"],"new_id":entry["new_id"],
                     "refactoring_type":entry["refactoring_type"],
                     "old_path":old_path,"new_path":new_path,
                     "old_exists_after":survives,"new_exists_before":preexists,
                     "body_equal":body_equal,"call_equal":call_equal,
                     "body_similarity":round(body_similarity,4),
                     "name_similarity":round(name_similarity,4),
                     "predictions":strategies})
        if len(rows)%25==0:print("source oracle parsed",len(rows),flush=True)
    summary=[]
    for arm in ("exact_test_id","name_only","exact_body","n04_pair_unmodified",
                "n04_pair_with_liveness_guard","strict_body_and_liveness","exact_body_and_calls"):
        tp=[r for r in rows if r["oracle_label"]=="TP"]
        fp=[r for r in rows if r["oracle_label"]=="FP"]
        summary.append({"arm":arm,"positive_refactoring_cases":len(tp),
                        "candidate_recovered":sum(r["predictions"][arm] for r in tp),
                        "oracle_false_positive_cases":len(fp),
                        "transfers_on_false_refactoring_candidates":sum(r["predictions"][arm] for r in fp),
                        "positive_recall":round(sum(r["predictions"][arm] for r in tp)/len(tp),4) if tp else None,
                        "negative_transfer_rate":round(sum(r["predictions"][arm] for r in fp)/len(fp),4) if fp else None,
                        "positive_migration_events":len({(r["repository"],r["commit"]) for r in tp}),
                        "negative_migration_events":len({(r["repository"],r["commit"]) for r in fp})})
    return {"scope":"Independent TP/FP refactoring-proposal verification on fetched pinned Java commits; this is NOT empirical production quarantine inheritance",
            "oracle":"RefactoringMiner human-validated data.json; never used for feature computation",
            "selection_bias":"The third-party oracle supplies one candidate new FQN; this is a validator not an end-to-end candidate discovery test",
            "tested_source_repos":sorted(repos),
            "excluded":dict(excluded),"summary":summary,"rows":rows}


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--oracle",type=Path,required=True)
    p.add_argument("--repo",nargs=2,action="append",default=[],metavar=("URL","PATH"))
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    d=inspect(json.loads(a.oracle.read_text()),{name:path for name,path in a.repo})
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(d,indent=2),encoding="utf-8")
    print(json.dumps({"excluded":d["excluded"],"summary":d["summary"]},indent=2))
