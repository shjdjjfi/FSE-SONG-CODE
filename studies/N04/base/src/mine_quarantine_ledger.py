"""Audit versioned, public CI quarantine decisions from real repositories.

Actual ledger mutations are observed actions, not hypothetical policy outputs.
Removal has multiple causes (rescue, expiry/deletion, policy change); never
interpret it automatically as a successful unquarantine.  Matching a rename
requires evidence beyond two adjacent ledger versions.
"""

from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import subprocess

ACTION=re.compile(r"https://github\.com/[^\s'\";,]+/actions/runs/\d+")


def git(repo,*args):
    return subprocess.run(["git","-C",str(repo),*args],capture_output=True,
                          text=True,check=True).stdout


def snapshot(repo,sha,path):
    raw=json.loads(git(repo,"show",sha+":"+path))
    entries=raw.get("entries",[])
    result={}
    for e in entries:
        if not isinstance(e,dict):continue
        identifier=e.get("file") or e.get("test") or e.get("job")
        if not identifier:continue
        result[identifier]=e
    return result


def mine(repo,path):
    history=git(repo,"log","--reverse","--format=%H%x09%cs%x09%s","--",path)
    commits=[];prev={};all_decisions=[];errors=[]
    for i,line in enumerate(history.splitlines()):
        bits=line.split("\t",2)
        if len(bits)!=3:continue
        sha,date,subject=bits
        try: cur=snapshot(repo,sha,path)
        except Exception as error:
            errors.append({"commit":sha,"error":type(error).__name__+": "+str(error)[:200]})
            continue
        added=sorted(set(cur)-set(prev))
        removed=sorted(set(prev)-set(cur))
        changed=sorted(key for key in set(prev)&set(cur) if prev[key]!=cur[key])
        for key in added:
            e=cur[key]
            all_decisions.append({"kind":"added_to_quarantine","commit":sha,"date":date,
                                  "identifier":key,"issue":e.get("issue"),
                                  "quarantined_at":e.get("quarantinedAt"),
                                  "reason":e.get("reason",""),
                                  "linked_action_runs":ACTION.findall(e.get("reason",""))})
        for key in removed:
            old=prev[key]
            all_decisions.append({"kind":"removed_from_quarantine_ambiguous_reason",
                                  "commit":sha,"date":date,"identifier":key,
                                  "previous_reason":old.get("reason",""),
                                  "commit_subject":subject})
        possible=[]
        for old in removed:
            for new in added:
                old_info=prev[old];new_info=cur[new]
                reasons_equal=bool(old_info.get("reason") and
                    old_info.get("reason")==new_info.get("reason"))
                runs_old=set(ACTION.findall(old_info.get("reason","")))
                runs_new=set(ACTION.findall(new_info.get("reason","")))
                if reasons_equal or runs_old.intersection(runs_new):
                    possible.append({"old":old,"new":new,
                                     "same_reason":reasons_equal,
                                     "shared_action_runs":sorted(runs_old & runs_new)})
        commits.append({"commit":sha,"date":date,"subject":subject,
                        "n_active":len(cur),"added":added,"removed":removed,
                        "modified_existing":changed,
                        "same_evidence_identity_change_candidates":possible})
        prev=cur
        if (i+1)%25==0:print("ledger processed",i+1,"commits",flush=True)
    return {"source_repo":git(repo,"config","--get","remote.origin.url").strip(),
            "ledger_path":path,"interpretation":"Real source-controlled quarantine actions, NOT proof of a historical test rename or CI runtime saving",
            "critical_caution":"A removed entry may indicate test deletion, expiry, fix, or policy change; matching old/new identities requires source confirmation",
            "summary":{"ledger_revisions":len(commits),
                       "add_decisions":sum(d["kind"]=="added_to_quarantine" for d in all_decisions),
                       "remove_decisions_unresolved":sum(d["kind"].startswith("removed") for d in all_decisions),
                       "distinct_identifiers_ever_added":len({d["identifier"] for d in all_decisions if d["kind"]=="added_to_quarantine"}),
                       "added_entries_with_action_links":sum(bool(d.get("linked_action_runs")) for d in all_decisions if d["kind"]=="added_to_quarantine"),
                       "possible_rename_with_same_evidence":sum(len(x["same_evidence_identity_change_candidates"]) for x in commits),
                       "current_active_quarantine_identifiers":len(prev),
                       "parse_errors":len(errors)},
            "commits":commits,"decisions":all_decisions,"errors":errors}


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--repo",type=Path,required=True)
    p.add_argument("--ledger",required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    data=mine(a.repo,a.ledger)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(data,indent=2),encoding="utf-8")
    print(json.dumps(data["summary"],indent=2))
