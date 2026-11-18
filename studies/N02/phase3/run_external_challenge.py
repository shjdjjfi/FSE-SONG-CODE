#!/usr/bin/env python3
"""Documented external historical-change challenges; no CID retuning.

These are intentional challenge cases from release notes, not unbiased
population sampling, real Pods, a human study, or production incidents.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

import yaml

ROOT=Path(__file__).resolve().parent.parent
HERE=ROOT/"phase3"
sys.path.insert(0,str(ROOT/"scripts"))
import run_study as frozen

HELM=ROOT/"toolchain/linux-amd64/helm"
OLD_SCORER_SHA="64381bae392d703b7fbc20159dbaa02cf9cb6591412eb8249e6bf1f55fbf2b2e"
assert frozen.sha256(ROOT/"scripts/run_study.py")==OLD_SCORER_SHA

CHARTS={
    "loki":ROOT/"phase2/charts",
    "kong":HERE/"charts",
    "vault":HERE/"charts",
    "traefik":ROOT/"phase2/charts",
}
CONT={"loki":{"loki":{"useTestSchema":True}}}
DOCS={
    "loki":"https://grafana.com/docs/loki/latest/setup/upgrade/upgrade-to-6x/",
    "kong":"https://github.com/Kong/charts/blob/main/charts/kong/UPGRADE.md",
    "vault":"https://github.com/hashicorp/vault-helm/blob/main/CHANGELOG.md",
    "traefik":"https://github.com/traefik/traefik-helm-chart",
}
CASES=[
    {"id":"L01_canary_disabled","family":"loki","old":"5.47.2","new":"6.0.0",
     "values":{"monitoring":{"lokiCanary":{"enabled":False}}},
     "repair":{"lokiCanary":{"enabled":False}},
     "oracle":"canary_daemonset_presence","expected":False,"source_documented":True},
    {"id":"L02_canary_label","family":"loki","old":"5.47.2","new":"6.0.0",
     "values":{"monitoring":{"lokiCanary":{"labelname":"n02_canary_contract"}}},
     "repair":{"lokiCanary":{"labelname":"n02_canary_contract"}},
     "oracle":"canary_label","expected":"n02_canary_contract","source_documented":True},
    {"id":"L03_canary_image","family":"loki","old":"5.47.2","new":"6.0.0",
     "values":{"monitoring":{"lokiCanary":{"image":{"repository":"example.invalid/n02canary"}}}},
     "repair":{"lokiCanary":{"image":{"repository":"example.invalid/n02canary"}}},
     "oracle":"canary_image_repository","expected":"example.invalid/n02canary","source_documented":True},
    {"id":"L04_external_config","family":"loki","old":"5.47.2","new":"6.0.0",
     "values":{"loki":{"externalConfigSecretName":"n02-config-external"}},
     "repair":{"loki":{"configObjectName":"n02-config-external"}},
     "oracle":"loki_config_reference","expected":"n02-config-external","source_documented":True},
    {"id":"G01_pdb_default","family":"kong","old":"2.1.0","new":"2.2.0",
     "values":{"podDisruptionBudget":{"enabled":True}},
     "repair":{"podDisruptionBudget":{"enabled":True,"maxUnavailable":"50%"}},
     "oracle":"pdb_max_unavailable","expected":"50%","source_documented":True},
    {"id":"G02_pdb_disabled","family":"kong","old":"2.1.0","new":"2.2.0",
     "values":{"podDisruptionBudget":{"enabled":False}},
     "repair":{"podDisruptionBudget":{"enabled":False}},
     "oracle":"pdb_presence","expected":False,"source_documented":False},
    {"id":"V01_ha_replicas","family":"vault","old":"0.25.0","new":"0.26.0",
     "repair_chart":"0.26.1",
     "values":{"server":{"ha":{"enabled":True,"replicas":2}}},
     "repair":{"server":{"ha":{"enabled":True,"replicas":2}}},
     "oracle":"vault_ha_replicas","expected":2,"source_documented":True},
    {"id":"V02_ha_default","family":"vault","old":"0.25.0","new":"0.26.0",
     "values":{"server":{"ha":{"enabled":True,"replicas":3}}},
     "repair":{"server":{"ha":{"enabled":True,"replicas":3}}},
     "oracle":"vault_ha_replicas","expected":3,"source_documented":False},
    {"id":"V03_config_tpl","family":"vault","old":"0.28.1","new":"0.29.0",
     "repair_chart":"0.29.1",
     "values":{"server":{"standalone":{"config":
       'ui = true\nstorage "file" { path = "/vault/data/{{ .Release.Name }}" }\n'}}},
     "repair":{"server":{"standalone":{"config":
       'ui = true\nstorage "file" { path = "/vault/data/{{ .Release.Name }}" }\n'}}},
     "oracle":"vault_templated_config","expected":"/vault/data/n02",
     "source_documented":True},
    {"id":"T01_unused_gateway","family":"traefik","old":"24.0.0","new":"25.0.0",
     "values":{"experimental":{"kubernetesGateway":{"gateway":{"enabled":True}}}},
     "repair":{"experimental":{"kubernetesGateway":{"gateway":{"enabled":True}}}},
     "oracle":"traefik_gateway_presence","expected":False,"source_documented":False},
]


def chart(case:dict,version:str)->Path:
    return CHARTS[case["family"]]/f"{case['family']}-{version}.tgz"


def context(case:dict)->dict:
    return copy.deepcopy(CONT.get(case["family"],{}))


def overlay(a:dict,b:dict)->dict:
    return frozen.deep_merge(a,b)


def extract(case:dict,docs:list[dict])->Any:
    oracle=case["oracle"]
    if oracle.startswith("canary_"):
        canaries=[d for d in docs if d["kind"]=="DaemonSet"
                  and "canary" in (d.get("metadata") or {}).get("name","").lower()]
        if oracle=="canary_daemonset_presence":
            return bool(canaries)
        containers=[c for d in canaries for c in
                    (d.get("spec",{}).get("template",{}).get("spec",{})
                     .get("containers",[]))]
        if oracle=="canary_image_repository":
            return next((c.get("image","").split(":")[0] for c in containers),None)
        if oracle=="canary_label":
            args=[str(arg) for c in containers for arg in c.get("args",[])]
            unique=[a for a in args if "labelname" in a.lower()]
            return " ".join(unique) if unique else None
    if oracle=="loki_config_reference":
        refs=[]
        for d in docs:
            template=d.get("spec",{}).get("template",{}).get("spec",{})
            for vol in template.get("volumes",[]) or []:
                for ty in ("configMap","secret"):
                    ref=(vol.get(ty) or {}).get("name") if isinstance(vol.get(ty),dict) else None
                    if isinstance(ref,str):
                        refs.append(ref)
        return sorted(set(refs))
    if oracle=="pdb_presence":
        return any(d["kind"]=="PodDisruptionBudget" for d in docs)
    if oracle=="pdb_max_unavailable":
        pdb=next((d for d in docs if d["kind"]=="PodDisruptionBudget"),None)
        value=(pdb or {}).get("spec",{}).get("maxUnavailable")
        return str(value) if value is not None else None
    if oracle=="vault_ha_replicas":
        sts=next((d for d in docs if d["kind"]=="StatefulSet"
                  and "vault" in (d.get("metadata") or {}).get("name","")),None)
        return (sts or {}).get("spec",{}).get("replicas")
    if oracle=="vault_templated_config":
        manifest=yaml.safe_dump_all(docs,sort_keys=True)
        return {"resolved_path":case["expected"] in manifest,
                "literal_template":"{{ .Release.Name }}" in manifest}
    if oracle=="traefik_gateway_presence":
        return any(d["kind"]=="Gateway" for d in docs)
    raise KeyError(oracle)


def contract_pass(case:dict,observed:Any)->bool:
    oracle=case["oracle"]
    expected=case["expected"]
    if oracle in ("canary_label","loki_config_reference","canary_image_repository"):
        if isinstance(observed,list):return expected in observed
        return isinstance(observed,str) and expected in observed
    if oracle=="vault_templated_config":
        return observed["resolved_path"] and not observed["literal_template"]
    return observed==expected


def score_case(case:dict,old_base:dict,new_base:dict,old:dict,new:dict,
               original_user:dict)->dict:
    old_effect=frozen.effect(frozen.flatten_docs(old_base["documents"]),
                             frozen.flatten_docs(old["documents"]))
    new_effect=frozen.effect(frozen.flatten_docs(new_base["documents"]),
                             frozen.flatten_docs(new["documents"]))
    lost=old_effect-new_effect
    gained=new_effect-old_effect
    vanished=frozen.lost_literals(original_user,old,new)
    score=(100.0*bool(old_effect and not new_effect)
           +10.0*len(lost)/max(len(old_effect),1)
           +1.0*min(len(gained),100)/max(len(new_effect),1)
           +60.0*bool(vanished))
    diff=frozen.effect(frozen.flatten_docs(old["documents"]),
                       frozen.flatten_docs(new["documents"]))
    new_defaults=yaml.safe_load(subprocess.run(
        [str(HELM),"show","values",str(chart(case,case["new"]))],
        text=True,capture_output=True,check=True).stdout) or {}
    def leaves(a:Any,p:tuple[str,...]=()):
        if isinstance(a,dict):
            for k,v in a.items():yield from leaves(v,p+(str(k),))
        else:yield p
    missing=0
    for path in leaves(original_user):
        obj=new_defaults
        for p in path:
            if not isinstance(obj,dict) or p not in obj:
                missing+=1
                break
            obj=obj[p]
    return {
        "score_counterfactual":round(score,6),
        "cid_alert":score>=5,
        "score_manifest_diff_magnitude":len(diff),
        "missing_default_keys":missing,
        "vanished_literals":vanished,
        "old_effect_positions":len(old_effect),
        "new_effect_positions":len(new_effect),
        "lost_effect_positions":len(lost)
    }


def main():
    out=HERE/"results"
    out.mkdir(parents=True,exist_ok=True)
    rows=[]
    provenance={}
    for case in CASES:
        for version in [case["old"],case["new"],case.get("repair_chart",case["new"])]:
            path=chart(case,version)
            if path.exists():
                provenance[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
    defaults={}
    for case in CASES:
        pair=(case["family"],case["old"],case["new"])
        if pair not in defaults:
            d=context(case)
            defaults[pair]=(frozen.render(HELM,chart(case,case["old"]),d),
                            frozen.render(HELM,chart(case,case["new"]),d))
        old_default,new_default=defaults[pair]
        history=overlay(context(case),case["values"])
        repair=overlay(context(case),case["repair"])
        old=frozen.render(HELM,chart(case,case["old"]),history)
        new=frozen.render(HELM,chart(case,case["new"]),history)
        fix=frozen.render(HELM,chart(case,case.get("repair_chart",case["new"])),repair)
        render={name:{"ok":r["ok"],"resources":r.get("resource_count"),
                      "stderr":r.get("error","")[-800:],
                      "stdout_sha256":r.get("stdout_sha256")} for name,r in
                (("old",old),("new",new),("repair",fix))}
        observations={}
        for name,r in (("old",old),("new",new),("repair",fix)):
            if r["ok"]:
                value=extract(case,r["documents"])
                observations[name]={"actual":value,"pass":contract_pass(case,value)}
            else:
                observations[name]={"actual":None,"pass":False}
        if old["ok"] and new["ok"] and fix["ok"] and observations["old"]["pass"]:
            if not observations["new"]["pass"] and observations["repair"]["pass"]:
                status="confirmed_manifest_positive"
            elif observations["new"]["pass"]:
                status="confirmed_preserved_control"
            else:
                status="unrepaired_or_unverified_change"
        else:
            status="invalid_or_nonrenderable_oracle"
        metrics=(score_case(case,old_default,new_default,old,new,case["values"])
                 if all(r["ok"] for r in (old_default,new_default,old,new))
                 else {})
        row={
            "id":case["id"],"family":case["family"],
            "old_version":case["old"],"new_version":case["new"],
            "repair_chart_version":case.get("repair_chart",case["new"]),
            "values":case["values"],"repair":case["repair"],
            "context":context(case),"oracle":case["oracle"],
            "expected":case["expected"],"official_doc":DOCS[case["family"]],
            "source_documented":case["source_documented"],
            "status":status,"render":render,"observations":observations,
            "method":metrics,
            "evidence_level":"actual Helm template + independently specified field oracle; NOT application runtime"
        }
        rows.append(row)
        print(f"{case['id']:<26} {status:<38} "
              f"old/new/fix={int(observations['old']['pass'])}/"
              f"{int(observations['new']['pass'])}/"
              f"{int(observations['repair']['pass'])} "
              f"CID={metrics.get('cid_alert','N/A')}",flush=True)
        (out/"challenge_cases.jsonl").write_text(
            "\n".join(json.dumps(x,ensure_ascii=False) for x in rows)+"\n")
    positives=[r for r in rows if r["status"]=="confirmed_manifest_positive"]
    controls=[r for r in rows if r["status"]=="confirmed_preserved_control"]
    s={"candidate_count":len(rows),"positives":len(positives),"controls":len(controls),
       "unconfirmed":len(rows)-len(positives)-len(controls),
       "positive_families":sorted({r["family"] for r in positives}),
       "CID_tp":sum(r["method"].get("cid_alert",False) for r in positives),
       "CID_fp":sum(r["method"].get("cid_alert",False) for r in controls),
       "sensitivity":(sum(r["method"].get("cid_alert",False) for r in positives)/len(positives)
                      if positives else None),
       "FPR":(sum(r["method"].get("cid_alert",False) for r in controls)/len(controls)
              if controls else None),
       "missing_key_baseline_TP":sum(r["method"].get("missing_default_keys",0)>0 for r in positives),
       "official_docs_explicit_positive":sum(r["source_documented"] for r in positives),
       "no_runtime_or_real_human":True,
       "selection_caveat":"upstream release notes guided candidates before evaluation",
       "chart_sha256":provenance,
       "scorer_sha256":OLD_SCORER_SHA}
    (out/"challenge_summary.json").write_text(json.dumps(s,ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in s.items() if k!="chart_sha256"},indent=2))


if __name__=="__main__":
    main()
