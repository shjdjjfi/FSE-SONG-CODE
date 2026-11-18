#!/usr/bin/env python3
"""Compiler-version holdout: TypeScript 6.0.2, independent TS6 oracle."""
from __future__ import annotations
import json
import shutil
from pathlib import Path
from run_n21 import (HERE, CASE_SPECS, expected_tree, inject_fault,
    purge_outputs, recover, run_build, summary_differences, write_json)


def main():
    runtime=HERE/"runtime"
    base=runtime/"ts6_holdout"/"base"
    if base.exists():
        shutil.rmtree(base)
    base.parent.mkdir(parents=True,exist_ok=True)
    template=runtime/"templates"/"libraries"
    shutil.copytree(template,base,symlinks=True)
    spec=CASE_SPECS["libraries"]
    compiler=runtime/"compiler6"/"package"/"bin"/"tsc"
    purge_outputs(base,spec)
    baseline=run_build(base,spec,compiler)
    report={"typescript":"6.0.2","real_source_snapshots":"ts-pattern 5.8.0, zod 3.25.76",
            "compiler_initial_build":baseline,"independent_oracle":None,"trials":[]}
    if baseline["exit"]:
        write_json(HERE/"results"/"version_holdout.json",report)
        raise RuntimeError(f"TS6 baseline failed: {baseline['stdout'][-1000:]}")
    clean=runtime/"ts6_holdout"/"oracle"
    if clean.exists():
        shutil.rmtree(clean)
    shutil.copytree(base,clean,symlinks=True)
    purge_outputs(clean,spec)
    independent=run_build(clean,spec,compiler)
    truth=expected_tree(clean,spec)
    match=truth==expected_tree(base,spec)
    report["independent_oracle"]={"compile":independent,"exact":match}
    if independent["exit"] or not match:
        write_json(HERE/"results"/"version_holdout.json",report)
        raise RuntimeError("TS6 clean oracle mismatch")
    for project in ("ts-pattern","zod"):
        for fault in ("delete_nested_js","corrupt_js","extra_stale"):
            for arm in ("standard","selective_path","selective_hash","clean_all","full_cache"):
                trial=runtime/"ts6_holdout"/"active"
                if trial.exists():
                    shutil.rmtree(trial)
                shutil.copytree(base,trial,symlinks=True)
                injected=inject_fault(trial,spec,project,truth,fault,17)
                before=summary_differences(truth,expected_tree(trial,spec))
                rec,logs=recover(trial,base,spec,compiler,arm,truth)
                observed=expected_tree(trial,spec)
                row={"project":project,"fault":fault,"arm":arm,
                    "correct":observed==truth and rec["build_succeeded"],
                    "before":before,"after":summary_differences(truth,observed),
                    "repair":rec,"logs":logs,"injected":injected}
                report["trials"].append(row)
                print(f"TS6 {project} {fault} {arm}: correct={row['correct']} "
                      f"{rec['work_seconds']:.2f}s",flush=True)
    scratch=runtime/"ts6_holdout"
    if scratch.exists():
        shutil.rmtree(scratch)
    write_json(HERE/"results"/"version_holdout.json",report)

if __name__=="__main__":
    main()
