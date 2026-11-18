#!/usr/bin/env python3
"""Direct local Turborepo 2.6.0 cache test on two real TS source snapshots.

The constructed workspace and fault injections are explicitly artificial;
the task executions and caching are handled by the real Turbo CLI.
"""
from __future__ import annotations
import os
import shutil
import subprocess
import time
from pathlib import Path
from run_n21 import HERE, CASE_SPECS, expected_tree, purge_outputs, write_json

def command(root, binary, project, force=False):
    argv=[str(binary), "run", "build", "--filter="+project, "--output-logs=full"]
    if force:
        argv.append("--force")
    env=dict(os.environ, TURBO_TELEMETRY_DISABLED="1", CI="1", TURBO_API="", TURBO_TOKEN="")
    start=time.perf_counter()
    p=subprocess.run(argv,cwd=root,env=env,capture_output=True,text=True,timeout=120)
    return {"argv":argv,"exit":p.returncode,"seconds":round(time.perf_counter()-start,3),
            "stdout":p.stdout[-4500:],"stderr":p.stderr[-3500:]}

def main():
    runtime=HERE/"runtime"
    out=HERE/"results"/"turborepo"
    out.mkdir(parents=True,exist_ok=True)
    template=runtime/"turbo_template"
    compiler=runtime/"compiler"/"package"/"bin"/"tsc"
    if not (template/"node_modules"/"turbo").is_dir():
        if template.exists():
            raise RuntimeError("Partial Turbo fixture: inspect before retrying")
        shutil.copytree(runtime/"templates"/"libraries",template)
        purge_outputs(template,CASE_SPECS["libraries"])
        write_json(template/"package.json",{"name":"n21-turbo-holdout","private":True,
            "version":"1.0.0","packageManager":"npm@11.9.0",
            "workspaces":["packages/*"],"devDependencies":{"turbo":"2.6.0"}})
        for project in CASE_SPECS["libraries"]["projects"]:
            write_json(template/"packages"/project/"package.json",{
                "name":"n21-"+project,"private":True,"version":"1.0.0",
                "scripts":{"build":f'node "{compiler}" -b'}})
        cp=subprocess.run(["npm","install","--ignore-scripts","--no-audit","--no-fund"],
            cwd=template,capture_output=True,text=True,timeout=240)
        if cp.returncode:
            write_json(out/"install_failure.json",{"stdout":cp.stdout,"stderr":cp.stderr})
            raise RuntimeError(cp.stderr)
    binary=template/"node_modules"/".bin"/"turbo"
    if not binary.exists():
        raise RuntimeError("Turbo CLI not installed")
    # Explicit inputs prevent generated outputs (which are untracked in this
    # constructed non-git fixture) from changing task hashes on deletion.
    write_json(template/"turbo.json",{"$schema":"https://turbo.build/schema.json",
        "tasks":{"build":{"inputs":["src/**","tsconfig.json","package.json"],
                            "outputs":["dist/**","cache.tsbuildinfo"]}}})
    observations=[]
    for project in ("ts-pattern","zod"):
        spec={"solution": "tsconfig.json", "projects": {project:
            {"dir":"packages/"+project, "out":"dist", "info":"cache.tsbuildinfo"}}}
        for fault in ("delete_js","corrupt_js"):
            for cache in ("available","forced_miss"):
                scratch=out/"scratch"/project/fault/cache
                if scratch.exists():
                    shutil.rmtree(scratch)
                shutil.copytree(template,scratch,ignore=shutil.ignore_patterns("node_modules",".turbo"))
                (scratch/"node_modules").symlink_to(template/"node_modules",target_is_directory=True)
                cold=command(scratch,binary,"n21-"+project)
                if cold["exit"]:
                    write_json(out/"failure.json",{"project":project,"cold":cold})
                    raise RuntimeError(f"Turbo cold build failed: {cold}")
                truth=expected_tree(scratch,spec)[project]
                choices=sorted(x for x in truth if "/" in x and x.endswith(".js"))
                target=scratch/"packages"/project/"dist"/choices[0]
                if fault=="delete_js":
                    target.unlink()
                else:
                    data=bytearray(target.read_bytes())
                    data[len(data)//2]^=1
                    target.write_bytes(data)
                warm=command(scratch,binary,"n21-"+project,force=cache=="forced_miss")
                files=expected_tree(scratch,spec)[project]
                observations.append({"project":project,"fault":fault,"cache":cache,
                    "target":choices[0],"cold":cold,"recovery":warm,
                    "correct":warm["exit"]==0 and files==truth,
                    "outputs":len(truth)})
                print(f"turbo {project} {fault} {cache} => exit={warm['exit']} correct={files==truth}",flush=True)
    write_json(out/"observations.json",{"turbo_version":"2.6.0",
        "experiment_scope":"constructed workspace; real cache/task execution; synthetic fault",
        "observations":observations})
    if (out/"scratch").exists():
        shutil.rmtree(out/"scratch")

if __name__=="__main__":
    main()
