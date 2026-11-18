#!/usr/bin/env python3
"""Safety control: a changed source with an artificially old mtime.

This checks a key precondition of the N21 manifest approach. Output-hash
verification alone does not establish input identity. A deployable recovery
gate must verify the compiler/inputs before trusting a prior output manifest.
"""

from __future__ import annotations
import hashlib
import json
import os
import shutil
import time
from pathlib import Path

from run_n21 import (HERE, CASE_SPECS, expected_tree, purge_outputs,
    run_build, recover, summary_differences, write_json)


def digest_inputs(base: Path, spec: dict) -> str:
    files = set(base.glob("tsconfig*.json")) | set(base.glob("package*.json"))
    for p in spec["projects"].values():
        project = base / p["dir"]
        files.update(project.glob("tsconfig*.json"))
        files.update(project.glob("package*.json"))
        src = project / "src"
        files.update(x for x in src.rglob("*") if x.is_file() and x.suffix in (".ts", ".tsx"))
    h=hashlib.sha256()
    for file in sorted(files):
        h.update(file.relative_to(base).as_posix().encode()+b"\0")
        h.update(file.read_bytes()+b"\0")
    return h.hexdigest()


def mutate_one_input(root: Path, spec: dict, project: str) -> str:
    p = root / spec["projects"][project]["dir"] / "src"
    target = next((x for x in sorted(p.glob("index.ts")) if x.is_file()), None)
    if target is None:
        target = next(x for x in sorted(p.rglob("*.ts")) if x.is_file())
    old_stat=target.stat()
    with target.open("a", encoding="utf-8") as f:
        f.write("\nexport const n21SafetyProbe = 2027;\n")
    # Simulate mtime preservation/backdating under restore; do not claim this is
    # a natural CI trace. Set before tsbuildinfo without modifying build info.
    ts = old_stat.st_mtime - 3600
    os.utime(target,(ts,ts))
    return target.relative_to(root).as_posix()


def main():
    runtime=HERE/"runtime"
    compiler=runtime/"compiler"/"package"/"bin"/"tsc"
    selected=[("libraries","mitt"),("andrewthauer","core"),("quramy","x-core")]
    results=[]
    for case,project in selected:
        spec=CASE_SPECS[case]
        template=runtime/"templates"/case
        meta=json.loads((runtime/"metadata"/f"{case}.json").read_text())
        expected=meta["expected_digests"]
        baseline_input=digest_inputs(template,spec)
        for arm in ("standard","selective_hash","invalidate_all","guarded_hash","clean_all"):
            trial=runtime/"drift_probe"/case/arm
            if trial.exists():
                shutil.rmtree(trial)
            shutil.copytree(template,trial,symlinks=True)
            touched=mutate_one_input(trial,spec,project)
            changed_input=digest_inputs(trial,spec)!=baseline_input
            assert changed_input
            if arm=="guarded_hash":
                actual, logs=recover(trial,template,spec,compiler,arm,expected)
                repaired={"input_key_rejected":actual["input_key_rejected"],
                          "seconds":actual["work_seconds"], "logs":logs}
            else:
                before, logs=recover(trial,template,spec,compiler,arm,expected)
                repaired={"input_key_rejected":False,"seconds":before["work_seconds"],"logs":logs}
            clean=runtime/"drift_probe"/case/"clean_oracle"
            if clean.exists():
                shutil.rmtree(clean)
            shutil.copytree(template,clean,symlinks=True)
            mutate_one_input(clean,spec,project)
            purge_outputs(clean,spec)
            oracle_log=run_build(clean,spec,compiler)
            if oracle_log["exit"]:
                raise RuntimeError(f"drift oracle compile failed: {oracle_log}")
            truth=expected_tree(clean,spec)
            before=expected_tree(trial,spec)
            observed=summary_differences(truth,before)
            row={"case":case,"project":project,"arm":arm,"source_mutation":touched,
                 "source_mtime_backdated_by_3600s":True,"input_key_different":changed_input,
                 "correct_against_new_clean_oracle":truth==before,"error_counts":observed,
                 "work":repaired,"clean_oracle":oracle_log}
            results.append(row)
            print(f"drift {case}/{project} {arm}: correct={row['correct_against_new_clean_oracle']} "
                  f"input_rejected={row['work']['input_key_rejected']}",flush=True)
        # Only remove our own scratch trials after complete per case.
        shutil.rmtree(runtime/"drift_probe"/case)
    write_json(HERE/"results"/"input_drift_probe.json",{"purpose":"same-output-manifest is unsafe if inputs change",
        "fault_origin":"synthetic source edit with deliberately backdated mtime", "observations":results})

if __name__=="__main__":
    main()
