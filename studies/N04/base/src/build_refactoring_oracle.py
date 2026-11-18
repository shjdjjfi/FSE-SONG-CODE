"""Independent manually validated refactoring IDs (RefactoringMiner oracle).

The third-party oracle validates whether a refactoring claim is real (TP/FP),
not whether a flaky-test quarantine state should be transferred.  We retain
both meanings separately. The origin is never used to compute candidate
features, model tuning, or the source-derived IDoFT target set.
"""

from __future__ import annotations
import argparse
import collections
import json
from pathlib import Path
import re
import subprocess

NAME = re.compile(r"(?P<name>[A-Za-z_$][\w$]*)\((?P<args>[^)]*)\)")
RENAME = re.compile(r"^Rename Method (?P<old>.+?) renamed to (?P<new>.+?) in class (?P<class>\S+)$")
MOVE = re.compile(r"^Move(?: And Rename)? Method (?P<old>.+?) from class (?P<oldclass>\S+) to (?P<new>.+?) from class (?P<newclass>\S+)$")


def is_test_method(class_name: str, name: str, args: str, signature: str) -> bool:
    base=class_name.rsplit(".",1)[-1]
    # Strict deterministic proxy for JUnit3/4 tests; this intentionally
    # excludes parameterized, JUnit5 and custom-named @Test methods.
    return ((base.endswith(("Test","Tests","TestCase")) or base.startswith("Test")) and
            re.match(r"^test[A-Z_0-9]", name) is not None and
            not args.strip() and re.search(r"\bpublic\b",signature) is not None)


def parse_description(description: str, type_name: str):
    if type_name=="Rename Method":
        m=RENAME.fullmatch(description)
        if not m:return None
        oldclass=newclass=m.group("class")
    else:
        m=MOVE.fullmatch(description)
        if not m:return None
        oldclass=m.group("oldclass")
        newclass=m.group("newclass")
    oldsig=m.group("old");newsig=m.group("new")
    old=NAME.search(oldsig);new=NAME.search(newsig)
    if not old or not new:return None
    if not is_test_method(oldclass,old.group("name"),old.group("args"),oldsig):return None
    # New test names may differ arbitrarily after a legitimate rename. We
    # still require public, no-argument runtime entry points in test classes.
    new_base=newclass.rsplit(".",1)[-1]
    if (not (new_base.endswith(("Test","Tests","TestCase")) or new_base.startswith("Test")) or
        new.group("args").strip() or not re.search(r"\bpublic\b",newsig)):
        return None
    return {"old_id":oldclass+"."+old.group("name"),
            "new_id":newclass+"."+new.group("name"),
            "old_class":oldclass,"new_class":newclass,
            "old_method":old.group("name"),"new_method":new.group("name"),
            "same_class":oldclass==newclass}


def load_oracle(repo: Path, rev="HEAD"):
    sha=subprocess.run(["git","-C",str(repo),"rev-parse",rev],
                       capture_output=True,text=True,check=True).stdout.strip()
    p=subprocess.run(["git","-C",str(repo),"show",f"{sha}:src/test/resources/oracle/data.json"],
                     capture_output=True,check=True)
    return sha,json.loads(p.stdout)


def extract(repo:Path,rev="HEAD"):
    head, records=load_oracle(repo,rev)
    result=[]; counters=collections.Counter()
    for entry in records:
        for ref in entry["refactorings"]:
            counters["total_refactorings"]+=1
            type_name=ref.get("type","")
            label=ref.get("validation")
            if type_name not in ("Rename Method","Move Method","Move And Rename Method") or label not in ("TP","FP"):
                continue
            parsed=parse_description(ref.get("description", ""), type_name)
            if not parsed:
                counters["non_junit3_4_or_unparseable"]+=1
                continue
            if parsed["old_id"] == parsed["new_id"]:
                counters["unchanged_full_id"]+=1
                continue
            result.append({**parsed,"refactoring_type":type_name,"label":label,
                           "repository":entry["repository"].removesuffix(".git"),
                           "commit":entry["sha1"],"oracle_entry_id":entry.get("id"),
                           "source_url":entry.get("url"),
                           "description":ref.get("description"),
                           "human_validation":ref.get("validators"),
                           "source_detection_tools":ref.get("detectionTools")})
    unique={}
    for x in result:
        key=(x["repository"],x["commit"],x["old_id"],x["new_id"])
        if key in unique and unique[key]["label"]!=x["label"]:
            counters["conflicting_oracle_labels"]+=1
            unique.pop(key)
            continue
        unique[key]=x
    filtered=list(unique.values())
    repos={x["repository"] for x in filtered}
    events={(x["repository"],x["commit"]) for x in filtered}
    return {"source_repo":"https://github.com/tsantalis/RefactoringMiner",
            "oracle_git_head":head,
            "source_file":"src/test/resources/oracle/data.json",
            "independent_validated_refactoring_labels":True,
            "not_a_quarantine_decision_oracle":True,
            "selection_rule":"public, no-argument test*() method inside Test* or *Test/*Tests/*TestCase class; original evaluated true/false refactoring descriptions; no status leakage",
            "counters":dict(counters),
            "summary":{"candidate_pairs":len(filtered),"TP":sum(x["label"]=="TP" for x in filtered),
                       "FP":sum(x["label"]=="FP" for x in filtered),
                       "independent_projects":len(repos),"independent_commits":len(events)},
            "records":filtered}


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--oracle-repo",type=Path,required=True)
    p.add_argument("--rev",default="HEAD",help="Pinned RefactoringMiner Git revision (recommended)")
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    result=extract(a.oracle_repo,a.rev)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result["summary"],indent=2))
