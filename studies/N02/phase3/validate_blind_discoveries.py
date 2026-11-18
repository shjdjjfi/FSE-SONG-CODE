#!/usr/bin/env python3
"""Validate two *exploratory* cases selected by automatic schema probing.

Selection was blind to release notes, but follow-up valid values, contracts,
and repairs were chosen AFTER screening. Never pool these with confirmatory
counts or call them independent randomized incidents.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent.parent
HERE=ROOT/"phase3"
sys.path.insert(0,str(HERE))
import run_external_challenge as base

EXTENDED=[
    {"id":"E01_canary_update_strategy","original_probe_path":
     "monitoring.lokiCanary.updateStrategy.type",
     "values":{"monitoring":{"lokiCanary":{"updateStrategy":{"type":"OnDelete"}}}},
     "repair":{"lokiCanary":{"updateStrategy":{"type":"OnDelete"}}},
     "expected":"OnDelete","key":"strategy",
     "contract":"DaemonSet.spec.updateStrategy.type remains OnDelete"},
    {"id":"E02_canary_image_registry","original_probe_path":
     "monitoring.lokiCanary.image.registry",
     "values":{"monitoring":{"lokiCanary":{"image":{"registry":"quay.io"}}}},
     "repair":{"lokiCanary":{"image":{"registry":"quay.io"}}},
     "expected":"quay.io/","key":"image",
     "contract":"Canary container image is taken from the configured registry"},
]


def observed(key:str,docs:list[dict]):
    d=next((d for d in docs if d.get("kind")=="DaemonSet"
            and "canary" in (d.get("metadata") or {}).get("name","")),None)
    if not d:return None
    if key=="strategy":return (d.get("spec") or {}).get("updateStrategy",{}).get("type")
    if key=="image":
        cs=(d.get("spec",{}).get("template",{}).get("spec",{})
            .get("containers",[]))
        return cs[0].get("image") if cs else None
    raise KeyError(key)


def good(row,value)->bool:
    if row["key"]=="image":return isinstance(value,str) and value.startswith(row["expected"])
    return value==row["expected"]


def main():
    selected=[json.loads(x) for x in (HERE/"results/blind_schema_selection_all_attempts.jsonl")
              .read_text().splitlines()]
    selected_paths={r["path"] for r in selected if r["literal_loss_candidate"]}
    sample=base.CASES[1]
    oldchart=base.chart(sample,"5.47.2")
    newchart=base.chart(sample,"6.0.0")
    values0=base.context(sample)
    old_base=base.frozen.render(base.HELM,oldchart,values0)
    new_base=base.frozen.render(base.HELM,newchart,values0)
    rows=[]
    for case in EXTENDED:
        assert case["original_probe_path"] in selected_paths
        original=base.overlay(values0,case["values"])
        repaired=base.overlay(values0,case["repair"])
        old=base.frozen.render(base.HELM,oldchart,original)
        new=base.frozen.render(base.HELM,newchart,original)
        fix=base.frozen.render(base.HELM,newchart,repaired)
        oracle={}
        for stage,render in [("old",old),("new",new),("repair",fix)]:
            actual=observed(case["key"],render["documents"]) if render["ok"] else None
            oracle[stage]={"ok":render["ok"],"actual":actual,"pass":good(case,actual)}
        valid=(all(x["ok"] for x in oracle.values())
               and oracle["old"]["pass"] and not oracle["new"]["pass"]
               and oracle["repair"]["pass"])
        metrics=base.score_case(sample,old_base,new_base,old,new,case["values"])
        record={**case,"source":"auto-discovered literal-loss candidate; manually validated",
                "fixed_scorer_sha256":base.OLD_SCORER_SHA,
                "valid_manifest_contract_loss":valid,"oracle":oracle,
                "frozen_method":metrics,
                "not_kubernetes_runtime":True,
                "not_independent_confirmatory":True}
        rows.append(record)
        print(case["id"],"manifest-positive=",valid,"CID=",metrics["cid_alert"])
    dest=HERE/"results/exploratory_validated_discoveries.json"
    dest.write_text(json.dumps(rows,ensure_ascii=False,indent=2))


if __name__=="__main__":main()
