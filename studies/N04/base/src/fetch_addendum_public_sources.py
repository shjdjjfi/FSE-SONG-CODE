"""Clone pinned public source inputs without modifying any original projects.

This helper is optional; the ZIP includes frozen results. It deliberately
refuses to use existing paths by default, and never checks out a worktree.
"""

from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess


REPOS={
    "fusion":("https://github.com/Runfusion/Fusion",None),
    "trycua":("https://github.com/trycua/cua",None),
    "riptide":("https://github.com/zalando/riptide",["cef45a1e325b5b1fdc4c47def3269ad3578b1fe1"]),
    "refactoringminer":("https://github.com/tsantalis/RefactoringMiner",["bc89d3de19a7566e4c2ce76f34c3394735de8ae4"]),
    "oracle_cassandra":("https://github.com/apache/cassandra",[]),
    "oracle_checkstyle":("https://github.com/checkstyle/checkstyle",[]),
    "oracle_infinispan":("https://github.com/infinispan/infinispan",[]),
    "oracle_closure-compiler":("https://github.com/google/closure-compiler",[]),
}


def run(*args):
    subprocess.run(args,check=True)


def read_git(path,*args):
    return subprocess.run(["git","-C",str(path),*args],capture_output=True,
                          check=True,text=True).stdout.strip()


def main(oracle_path,root,reuse=False):
    root=root.resolve()
    data=json.loads(oracle_path.read_text())
    commits={k:set(revisions or ()) for k,(_,revisions) in REPOS.items()}
    for entry in data["records"]:
        for key,(url,_) in REPOS.items():
            if url==entry["repository"]:commits[key].add(entry["commit"])
    root.mkdir(parents=True,exist_ok=True)
    for key,(url,_) in REPOS.items():
        dest=root/key
        if dest.exists():
            if not reuse:raise FileExistsError(f"Refusing to change existing repository: {dest} (use --reuse only for your own verified clones)")
            actual=read_git(dest,"config","--get","remote.origin.url").removesuffix(".git")
            if actual!=url:raise ValueError(f"Repository mismatch at {dest}: {actual} != {url}")
        else:
            # Full commit history is needed for ledger evolution; source-oracle
            # code only needs each exact event commit and its direct parent.
            shallow=["--depth=1"] if key not in ("fusion","trycua") else []
            run("git","clone","--filter=blob:none","--no-checkout",*shallow,url,str(dest))
        for revision in sorted(commits[key]):
            # A 2-deep fetch is sufficient to read commit and direct parent,
            # without downloading the full history of giant Java repos.
            if key not in ("fusion","trycua"):
                run("git","-C",str(dest),"fetch","--filter=blob:none","--depth=2","origin",revision)
                resolved=read_git(dest,"rev-parse",revision+"^{commit}")
                print(key,revision[:12],"->",resolved[:12],flush=True)
        print("ready",key,flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--oracle",type=Path,required=True)
    p.add_argument("--output-root",type=Path,required=True)
    p.add_argument("--reuse",action="store_true")
    a=p.parse_args()
    main(a.oracle,a.output_root,a.reuse)
