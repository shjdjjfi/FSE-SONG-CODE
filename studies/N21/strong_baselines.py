#!/usr/bin/env python3
"""Run Wireit 0.14.12 on public TS source snapshots with injected output loss.

This is a real execution of Wireit, not a mathematical proxy. Only the damage
is synthetic. A full cache hit and an absent cache are deliberately separate.
"""

from __future__ import annotations
import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

from run_n21 import HERE, CASE_SPECS, expected_tree, purge_outputs, write_json


def run_cwd(path: Path, cache: str) -> dict:
    argv = ["npm", "run", "build"]
    env = dict(os.environ, WIREIT_CACHE=cache, CI="true", npm_config_ignore_scripts="true")
    start = time.perf_counter()
    cp = subprocess.run(argv, cwd=path, env=env, capture_output=True, text=True, timeout=120)
    return {"exit":cp.returncode,"seconds":round(time.perf_counter()-start,3),
            "argv":argv,"cache":cache,"stdout":cp.stdout[-6000:],"stderr":cp.stderr[-4000:]}


def main():
    runtime = HERE / "runtime"
    source = runtime / "templates" / "libraries" / "packages"
    deps = runtime / "dependencies" / "wireit"
    deps.mkdir(parents=True,exist_ok=True)
    if not (deps / "node_modules" / "wireit" / "bin" / "wireit.js").is_file():
        p = subprocess.run(["npm","install","--ignore-scripts","--no-audit","--no-fund","--save-exact","wireit@0.14.12"],
           cwd=deps,capture_output=True,text=True,timeout=240)
        if p.returncode:
            raise RuntimeError(p.stderr+"\n"+p.stdout)
    compiler = runtime / "compiler" / "package" / "bin" / "tsc"
    out = HERE / "results" / "wireit"
    out.mkdir(parents=True,exist_ok=True)
    results=[]
    for name in ("ts-pattern","zod"):
        for profile,cache,clean in (("local","local","if-file-deleted"),
                                    ("none","none","if-file-deleted"),
                                    ("always","none",True)):
            for fault in ("delete_js","corrupt_js"):
                target=out / "scratch" / name / profile / fault
                if target.exists():
                    # Only replace a known trial-specific temp path created here.
                    shutil.rmtree(target)
                shutil.copytree(source / name,target)
                p={"dir":".","out":"dist","info":"cache.tsbuildinfo"}
                spec={"solution":"tsconfig.json","projects":{name:p}}
                purge_outputs(target,spec)
                conf={"name":"wireit-n21-reproduction","private":True,
                      "scripts":{"build":"wireit"},
                      "wireit":{"build":{"command":f'node "{compiler}" -b',
                        "files":["src/**/*.ts","tsconfig.json"],
                        "output":["dist/**","cache.tsbuildinfo"],"clean":clean}}}
                write_json(target/"package.json",conf)
                (target/"node_modules").symlink_to(deps / "node_modules",target_is_directory=True)
                cold=run_cwd(target,cache)
                if cold["exit"]:
                    raise RuntimeError(f"Cold Wireit failed: {name}/{profile}/{fault}: {cold}")
                expected=expected_tree(target,spec)
                choices=sorted(k for k in expected[name] if k.endswith(".js") and "/" in k)
                if not choices:
                    raise RuntimeError(f"No nested JS for {name}")
                chosen=choices[len(choices)//2]
                victim=target / "dist" / chosen
                if fault=="delete_js":
                    victim.unlink()
                else:
                    dat=bytearray(victim.read_bytes())
                    dat[len(dat)//2]^=1
                    victim.write_bytes(dat)
                recovery=run_cwd(target,cache)
                found=expected_tree(target,spec)
                results.append({"project":name,"profile":profile,"fault":fault,
                    "damaged_file":chosen,"cold":cold,"recovery":recovery,
                    "correct":found==expected,
                    "post_mismatches":len(set(expected[name])^set(found[name]))+
                     sum(expected[name][n]!=found[name][n] for n in expected[name].keys()&found[name].keys())})
                print(f"wireit {name} {profile} {fault}: exit={recovery['exit']} correct={found==expected} ",flush=True)
    write_json(out/"observations.json",{"wireit":"0.14.12","typescript":"5.9.3",
        "note":"faults are controlled; full-cache availability is deliberately varied", "observations":results})
    scratch=out/"scratch"
    if scratch.exists():
        shutil.rmtree(scratch)

if __name__=="__main__":
    main()
