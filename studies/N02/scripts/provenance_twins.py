#!/usr/bin/env python3
"""Old-default-versus-explicit-value twins from actual historical Helm charts.

For each sampled changed default leaf, construct two release histories:
  H0 old: the operator never wrote the key;
  H1 old: the operator explicitly set exactly the old built-in default.
They yield identical old-version rendered resources by construction, but the
reset-then-reuse policy must respect H1's operator-supplied Config.
Finding an H0/H1 divergence does NOT prove an upgrade bug; it establishes
why intent cannot be inferred from manifests alone.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import random
import subprocess
from typing import Any

import yaml

from run_study import effect, flatten_docs, render


ROOT = Path(__file__).resolve().parent.parent
SEED = 17
MAX_PER_FAMILY = 35


def leaves(value: Any, prefix: tuple[str,...]=()) -> dict[tuple[str,...], Any]:
    if isinstance(value, dict):
        result = {}
        for k,v in value.items():
            result.update(leaves(v,prefix+(str(k),)))
        return result
    if type(value) in (str,int,bool,float):
        return {prefix:value}
    return {}


def set_nested(path: tuple[str,...], value: Any) -> dict:
    result: Any=value
    for key in reversed(path):
        result={key:result}
    return result


def main() -> None:
    helm = ROOT/"toolchain/linux-amd64/helm"
    config = yaml.safe_load((ROOT/"cases.yaml").read_text())["families"]
    rng=random.Random(SEED)
    records=[]
    summary=[]
    for family,pair in config.items():
        old=ROOT/"charts"/pair["from"]
        new=ROOT/"charts"/pair["to"]
        defaults={}
        for stage,chart in (("old",old),("new",new)):
            result=subprocess.run([str(helm),"show","values",str(chart)],
                                  capture_output=True,text=True,check=True)
            defaults[stage]=yaml.safe_load(result.stdout)
        oldleaf=leaves(defaults["old"])
        newleaf=leaves(defaults["new"])
        candidates=[p for p in oldleaf.keys() & newleaf.keys()
                    if type(oldleaf[p])==type(newleaf[p]) and oldleaf[p]!=newleaf[p]]
        candidates=sorted(candidates)
        rng.shuffle(candidates)
        trial=candidates[:MAX_PER_FAMILY]
        baseline_old=render(helm,old,{})
        baseline_new=render(helm,new,{})
        if not baseline_old["ok"] or not baseline_new["ok"]:
            raise RuntimeError(f"Default render failed for {family}")
        divergent=0
        for path in trial:
            explicitly_written = set_nested(path,oldleaf[path])
            old_explicit=render(helm,old,explicitly_written)
            new_explicit=render(helm,new,explicitly_written)
            old_identical = (
                old_explicit["ok"] and
                not effect(flatten_docs(baseline_old["documents"]),
                           flatten_docs(old_explicit["documents"]))
            )
            if new_explicit["ok"]:
                new_change=effect(flatten_docs(baseline_new["documents"]),
                                  flatten_docs(new_explicit["documents"]))
                divergence=old_identical and bool(new_change)
            else:
                new_change=set()
                divergence=False
            divergent+=int(divergence)
            records.append({
                "family":family,"value_path":".".join(path),
                "old_default":oldleaf[path],"new_default":newleaf[path],
                "old_explicit_render_success":old_explicit["ok"],
                "old_same_manifest_with_explicit_old_default":old_identical,
                "new_reset_then_reuse_explicit_render_success":new_explicit["ok"],
                "new_reset_then_reuse_differs_from_implicit":divergence,
                "new_changed_semantic_fields":len(new_change),
                "errors": [q["error"][-250:] for q in (old_explicit,new_explicit) if not q["ok"]],
            })
        summary.append({
            "family":family,"scalar_default_drift_candidates":len(candidates),
            "sampled":len(trial),"old_render_identical":sum(
                x["old_same_manifest_with_explicit_old_default"] for x in records
                if x["family"]==family
            ),
            "new_divergence_with_explicit_old_default":divergent,
        })
        print(f"{family}: changed-default scalar keys={len(candidates)}, "
              f"sample={len(trial)}, provenance-twin divergences={divergent}",flush=True)
        (ROOT/"results/provenance_twins.json").write_text(
            json.dumps({
                "design":"structured counterfactual over old vs explicit-equal-to-default release config",
                "seed":SEED,"sample_cap_per_family":MAX_PER_FAMILY,
                "policy":"reset-then-reuse emulation (new defaults + old explicit Config)",
                "not_observed_release":True,
                "not_application_failure_oracle":True,
                "chart_families":summary,"cases":records,
            },indent=2,ensure_ascii=False)
        )
    print("PROVENANCE EXPERIMENT COMPLETE",flush=True)


if __name__=="__main__":
    main()
