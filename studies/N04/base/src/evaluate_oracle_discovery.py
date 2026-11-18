"""Independent end-to-end successor search on third-party validated Java refactorings.

The independent oracle supplies *old test IDs and evaluation labels only*.
Each algorithm enumerates post-commit test methods from changed Java files,
then finds a successor without reading the proposed target ID or TP/FP label.
RefactoringMiner FP labels are NOT a gold standard for 'unsafe quarantine'.
"""

from __future__ import annotations
import argparse
from collections import Counter,defaultdict
from difflib import SequenceMatcher
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from java_source import methods_at


def git(repo,*args):
    p=subprocess.run(["git","-C",str(repo),*args],text=True,capture_output=True)
    if p.returncode:raise RuntimeError(p.stderr[:250])
    return p.stdout.strip()


def resolve_old(repo,sha,old_fqn,tree):
    suffix=old_fqn.rsplit(".",1)[0].replace(".","/")+".java"
    matches=[p for p in tree if p.endswith(suffix)]
    if len(matches)!=1:return None
    return next((m for m in methods_at(str(repo),sha,matches[0]) if m.fqn==old_fqn),None)


def pick_unique(candidates,pred):
    choices=[m for m in candidates if pred(m)]
    return choices[0].fqn if len(choices)==1 else None


def propose(old,candidates):
    new=[m for m in candidates if m.fqn!=old.fqn]
    exact_body=pick_unique(new,lambda m:m.body_hash==old.body_hash)
    same_name=pick_unique(new,lambda m:m.name==old.name)
    stable_calls=pick_unique(new,lambda m:m.name==old.name and
                            set(m.calls)==set(old.calls) and
                            SequenceMatcher(None,m.body[:2500],old.body[:2500]).ratio()>=.30)
    # Source-only proxy of N04's guarded hierarchy. No target labels, no
    # RefactoringMiner refactoring types, and no tuning on the test corpus.
    guarded=exact_body or stable_calls
    return {"exact_id":pick_unique(candidates,lambda m:m.fqn==old.fqn),
            "unique_name":same_name,
            "unique_body":exact_body,
            "guarded_lineage":guarded,
            "name_calls_guard":stable_calls}


def evaluate(oracle,repos):
    groups=defaultdict(list)
    excluded=Counter(); event_info=[]; predictions={}
    for row in oracle["records"]:
        if row["repository"] in repos:
            groups[(row["repository"],row["commit"])].append(row)
        else:excluded["repository_not_fetched"]+=1
    for (url,sha),entries in sorted(groups.items()):
        repo=repos[url]
        try:
            before=git(repo,"rev-parse",sha+"^1")
            parent_tree=git(repo,"ls-tree","-r","--name-only",before).splitlines()
            child_paths=set(git(repo,"ls-tree","-r","--name-only",sha).splitlines())
            changed=git(repo,"diff","--no-renames","--name-only",before,sha).splitlines()
            changed_new=[p for p in changed if p in child_paths and p.endswith(".java")
                         and ("/test/" in p.lower() or p.lower().startswith("test/"))]
            successors={}
            for path in changed_new:
                for method in methods_at(str(repo),sha,path):
                    if method.is_test:
                        successors[method.fqn]=method
            pool=list(successors.values())
        except Exception as ex:
            excluded["event_unavailable"]+=len(entries)
            event_info.append({"repository":url,"commit":sha,"error":str(ex)[:180]})
            continue
        event_info.append({"repository":url,"commit":sha,"n_oracle_proposals":len(entries),
                           "changed_test_java_files":len(changed_new),
                           "new_test_method_candidates":len(pool)})
        old_ids={x["old_id"] for x in entries}
        for old_id in sorted(old_ids):
            old=resolve_old(repo,before,old_id,parent_tree)
            if not old:
                excluded["old_test_method_missing"]+=1
                continue
            predictions[(url,sha,old_id)]=propose(old,pool)
        print("discovered candidates",url,sha[:8],"methods",len(pool),flush=True)
    # Unique group guard operates on unique OLD IDs, not the oracle's many
    # redundant TP/FP pairs for one OLD test. This avoids proposal duplication.
    group_counts=Counter()
    for (url,sha,old),arms in predictions.items():
        if arms["guarded_lineage"]:group_counts[(url,sha,arms["guarded_lineage"])]+=1
    for (url,sha,old),arms in predictions.items():
        target=arms["guarded_lineage"]
        arms["guarded_with_group_guard"]=target if target and group_counts[(url,sha,target)]==1 else None
    results=[]
    for entry in oracle["records"]:
        key=(entry["repository"],entry["commit"],entry["old_id"])
        if key not in predictions:continue
        preds=predictions[key]
        results.append({"repository":entry["repository"],"commit":entry["commit"],
                        "old_id":entry["old_id"],"third_party_proposed_target":entry["new_id"],
                        "oracle_refactoring_label":entry["label"],
                        "test_identity_transfer_ground_truth":None,
                        "predicted_targets":preds,
                        "oracle_target_matched":{arm:(value==entry["new_id"]) for arm,value in preds.items()}})
    arms=("exact_id","unique_name","unique_body","guarded_lineage",
          "name_calls_guard","guarded_with_group_guard")
    tp=[r for r in results if r["oracle_refactoring_label"]=="TP"]
    fp=[r for r in results if r["oracle_refactoring_label"]=="FP"]
    summary=[]
    for arm in arms:
        pos=sum(r["oracle_target_matched"][arm] for r in tp)
        neg=sum(r["oracle_target_matched"][arm] for r in fp)
        summary.append({"arm":arm,"independently_confirmed_refactoring_pairs":len(tp),
                        "independent_target_recovered":pos,
                        "independent_target_recall":round(pos/len(tp),4) if tp else None,
                        "refactoring_proposals_labeled_FP":len(fp),
                        "predicted_same_target_as_refactoring_FP":neg,
                        "warning":"FP of a Move Method may still entail test identity continuity, so this count is NOT unsafe quarantine inheritance"})
    per_repository=[]
    for url in sorted({r["repository"] for r in results}):
        positive=[r for r in tp if r["repository"]==url]
        negative=[r for r in fp if r["repository"]==url]
        per_repository.append({"repository":url,"TP":len(positive),"FP":len(negative),
                               "guarded_TP_recovered":sum(r["oracle_target_matched"]["guarded_with_group_guard"] for r in positive),
                               "name_only_TP_recovered":sum(r["oracle_target_matched"]["unique_name"] for r in positive)})
    return {"scope":"True end-to-end successor discovery from Git-changed Java test files, evaluated against independent RefactoringMiner test-method refactoring oracle",
            "no_target_or_label_in_prediction":True,
            "not_quarantine_oracle":True,
            "strong_caveat":"A refactoring FP is not automatically a negative test-identity label; performance is method-refactoring target recall only, not safety or industrial impact",
            "excluded":dict(excluded),"event_info":event_info,
            "summary":summary,"per_repository":per_repository,"records":results}


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--oracle",type=Path,required=True)
    p.add_argument("--repo",nargs=2,action="append",default=[],metavar=("URL","PATH"))
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    result=evaluate(json.loads(a.oracle.read_text()),dict(a.repo))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps({"excluded":result["excluded"],"summary":result["summary"],
                      "per_repository":result["per_repository"]},indent=2))
