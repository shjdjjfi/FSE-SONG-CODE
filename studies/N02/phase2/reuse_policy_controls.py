#!/usr/bin/env python3
"""Policy-sensitivity negative-control stress test (SIMULATED old-default reuse).

The new Chart is rendered by genuine Helm, but the old-default-value merge is
manually constructed, not read back from an installed Helm Release.
"""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys

import yaml

ROOT=Path(__file__).resolve().parent.parent
PHASE=ROOT/"phase2"
sys.path.insert(0,str(ROOT/"scripts"))
import run_study as original


def main():
    rows=[json.loads(x) for x in (PHASE/"results/holdout_cases.jsonl").read_text().splitlines()]
    pairs={r["family"]:r for r in
           json.loads((PHASE/"results/charts_provenance.json").read_text())}
    helm=ROOT/"toolchain/linux-amd64/helm"
    original_defaults={}
    records=[]
    for r in rows:
        fam=r["family"]
        pair=pairs[fam]
        if fam not in original_defaults:
            old=PHASE/"charts"/pair["old_archive"]
            process=subprocess.run([str(helm),"show","values",str(old)],
                                   text=True,capture_output=True,check=True)
            original_defaults[fam]=yaml.safe_load(process.stdout) or {}
        user={}
        node=user
        for key in r["path_keys"][:-1]:
            node=node.setdefault(key,{})
        node[r["path_keys"][-1]]=r["value"]
        override=original.deep_merge(original_defaults[fam],user)
        newchart=PHASE/"charts"/pair["new_archive"]
        result=original.render(helm,newchart,override)
        preserved=result["ok"] and r["value"] in yaml.safe_dump_all(result["documents"])
        records.append({
            "case":r["case"],"family":fam,"reset_new_default_preserved":r["new_present"],
            "reuse_old_defaults_emulated_render_ok":result["ok"],
            "reuse_old_defaults_emulated_preserved":bool(preserved),
            "warning":"not a Helm upgrade with persisted history, value-merge proxy",
            "render":{k:v for k,v in result.items() if k!="documents"},
        })
    summary={
        "n":len(records),"family_count":len({r["family"] for r in records}),
        "original_reset_then_reuse_nonlosses":sum(r["reset_new_default_preserved"] for r in records),
        "emulated_reuse_render_failures":sum(not r["reuse_old_defaults_emulated_render_ok"] for r in records),
        "emulated_reuse_value_losses":sum(r["reuse_old_defaults_emulated_render_ok"] and
                                         not r["reuse_old_defaults_emulated_preserved"] for r in records),
        "interpretation":"application runtime not tested; not exact Helm merge semantics",
    }
    (PHASE/"results"/"reuse_policy_controls.json").write_text(json.dumps(
        {"summary":summary,"rows":records},indent=2))
    print(json.dumps(summary,indent=2))

if __name__=="__main__":
    main()
