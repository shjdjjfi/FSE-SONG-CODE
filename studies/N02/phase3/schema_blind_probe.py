#!/usr/bin/env python3
"""Automated schema-only discovery (no changelog read, exploratory).

The path inclusion rule inspects old and new Helm values.yaml schemas only;
the scanner does not use documentation, manually chosen case IDs or CID scores.
All attempted paths (including failures) are archived. This detects literal
preservation, NOT Kubernetes runtime behavior or semantic correctness.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import yaml

ROOT=Path(__file__).resolve().parent.parent
HERE=ROOT/"phase3"
sys.path.insert(0,str(ROOT/"scripts"))
sys.path.insert(0,str(ROOT/"phase2"))
import run_study as frozen
import run_holdout as phase2

ORIGINAL_SCORER_SHA="64381bae392d703b7fbc20159dbaa02cf9cb6591412eb8249e6bf1f55fbf2b2e"
assert frozen.sha256(ROOT/"scripts/run_study.py")==ORIGINAL_SCORER_SHA

PAIRS=[
    ("loki","5.47.2","6.0.0",ROOT/"phase2/charts",{"loki":{"useTestSchema":True}}),
    ("traefik","24.0.0","25.0.0",ROOT/"phase2/charts",{}),
    ("kong","2.1.0","2.2.0",HERE/"charts",{}),
    ("vault","0.25.0","0.26.0",HERE/"charts",{}),
    ("vault","0.28.1","0.29.0",HERE/"charts",{}),
    ("grafana","7.3.12","8.0.0",ROOT/"phase2/charts",{}),
    ("ingress-nginx","4.10.0","4.11.0",ROOT/"phase2/charts",{}),
    ("metrics-server","3.11.0","3.12.0",ROOT/"phase2/charts",{}),
    ("external-dns","1.14.4","1.15.0",ROOT/"phase2/charts",{}),
]
BLOCK=("secret","password","token","credential","private","certificate",
       "cert","passphrase","auth","license","pem")


def strings(obj:Any,path:tuple[str,...]=()):
    if isinstance(obj,dict):
        for k,v in obj.items():yield from strings(v,path+(str(k),))
    elif isinstance(obj,str) and "\n" not in obj and "{{" not in obj:
        if len(obj)<=160 and not any(t in ".".join(path).lower() for t in BLOCK):
            yield path


def exists(obj:Any,path:tuple[str,...])->bool:
    for part in path:
        if not isinstance(obj,dict) or part not in obj:return False
        obj=obj[part]
    return True


def override(path:tuple[str,...],value:str)->dict:
    result={}
    target=result
    for part in path[:-1]:target=target.setdefault(part,{})
    target[path[-1]]=value
    return result


def main():
    helm=ROOT/"toolchain/linux-amd64/helm"
    results=[]
    summary=[]
    for family,oldver,newver,folder,context in PAIRS:
        oldchart=folder/f"{family}-{oldver}.tgz"
        newchart=folder/f"{family}-{newver}.tgz"
        if not oldchart.exists() or not newchart.exists():
            summary.append({"pair":f"{family} {oldver}->{newver}","status":"archive_missing"})
            continue
        oldvals=phase2.load_values(helm,oldchart)
        newvals=phase2.load_values(helm,newchart)
        paths=sorted((p for p in strings(oldvals) if not exists(newvals,p)),
                     key=lambda p:hashlib.sha256(("20261115/"+family+"/"+".".join(p)).encode()).digest())
        examined=0
        lost=0
        for path in paths:
            digest=hashlib.sha256((f"{family}/{oldver}/"+".".join(path)).encode()).hexdigest()[:10]
            user_value=phase2.new_value(path,f"n02-blind-{digest}")
            user=override(path,user_value)
            history=frozen.deep_merge(context,user)
            old=frozen.render(helm,oldchart,history)
            record={"family":family,"versions":[oldver,newver],
                    "path":".".join(path),"values":user,
                    "selection":"automatic old string leaf absent from new values.yaml",
                    "old_render_ok":old["ok"]}
            if old["ok"] and phase2.has_value(old["documents"],user_value):
                new=frozen.render(helm,newchart,history)
                seen_new=bool(new["ok"] and phase2.has_value(new["documents"],user_value))
                record.update({"old_exposed":True,"new_render_ok":new["ok"],
                               "new_exposed":seen_new,
                               "literal_loss_candidate":new["ok"] and not seen_new})
                examined+=1
                lost+=int(record["literal_loss_candidate"])
            else:
                record.update({"old_exposed":False,"literal_loss_candidate":False,
                               "error":old.get("error","")[-200:]})
            results.append(record)
        summary.append({"pair":f"{family} {oldver}->{newver}",
                        "old_string_keys_absent_from_new":len(paths),
                        "exposed_old_candidates_evaluated":examined,
                        "lost_literals_after_upgrade":lost})
        print(summary[-1],flush=True)
    out=HERE/"results"
    (out/"blind_schema_selection_all_attempts.jsonl").write_text(
        "\n".join(json.dumps(r,ensure_ascii=False) for r in results)+"\n")
    (out/"blind_schema_summary.json").write_text(json.dumps({
        "selection_without_documentation":True,
        "exploratory_not_independent_confirmatory":True,
        "old_scorer_sha256":ORIGINAL_SCORER_SHA,
        "pairs":summary,
        "total_candidates":len(results),
        "total_literal_loss_candidates":sum(r["literal_loss_candidate"] for r in results),
        "limitations":"Sentinel loss is NOT a runtime failure; manually validate before positive label."
    },ensure_ascii=False,indent=2))


if __name__=="__main__":main()
