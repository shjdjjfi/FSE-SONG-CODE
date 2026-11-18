#!/usr/bin/env python3
"""Run the TypeScript incremental API output-deletion probe on v5.9 and v6.0."""
from __future__ import annotations
import json
import shutil
import subprocess
import tarfile
import urllib.request
from pathlib import Path
from run_n21 import HERE, write_json, sha_file

TS6_SHA = "0ae5c188a2f5db22df72fe5e74dcbc122afb52031a86dbac33e78a86db39c65e"

def main():
    runtime = HERE / "runtime"
    tsc5 = runtime / "compiler" / "package" / "lib" / "typescript.js"
    tsc6 = runtime / "compiler6" / "package" / "lib" / "typescript.js"
    if not tsc5.exists():
        raise RuntimeError("Run `run_n21.py prepare` first")
    if not tsc6.exists():
        archive = HERE.parent / "n21_downloads" / "typescript-6.0.2.tgz"
        if not archive.exists():
            archive.parent.mkdir(parents=True, exist_ok=True)
            url = "https://registry.npmjs.org/typescript/-/typescript-6.0.2.tgz"
            tmp = archive.with_suffix(".partial")
            try:
                with urllib.request.urlopen(url, timeout=90) as src, tmp.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
                if sha_file(tmp) != TS6_SHA:
                    raise RuntimeError("TypeScript 6.0.2 downloaded SHA mismatch")
                tmp.rename(archive)
            finally:
                if tmp.exists():
                    tmp.unlink()
        if not archive.is_file() or sha_file(archive) != TS6_SHA:
            raise RuntimeError("Missing TypeScript 6.0.2 archive, or hash mismatch")
        (runtime / "compiler6").mkdir(parents=True, exist_ok=True)
        with tarfile.open(archive) as t:
            t.extractall(runtime / "compiler6", filter="data")
    results=[]
    for version, pkg in (("5.9.3",tsc5), ("6.0.2",tsc6)):
        project=runtime / "api_probe" / version
        project.mkdir(parents=True, exist_ok=True)
        (project / "src").mkdir(exist_ok=True)
        (project / "src" / "main.ts").write_text("export const n21Value: number = 23;\n",encoding="utf-8")
        write_json(project / "tsconfig.build.json", {"compilerOptions": {
            "incremental": True, "target":"ES2022", "module":"CommonJS",
            "outDir":"dist", "rootDir":"src", "tsBuildInfoFile":"cache.tsbuildinfo"},
            "include":["src/**/*.ts"]})
        outfile=project / "dist"
        if outfile.exists():
            shutil.rmtree(outfile)
        info=project / "cache.tsbuildinfo"
        if info.exists():
            info.unlink()
        cmd=["node",str(HERE/"api_incremental_probe.cjs"),str(pkg),str(project)]
        p=subprocess.run(cmd,capture_output=True,text=True,timeout=90)
        row={"version":version,"returncode":p.returncode,"stderr":p.stderr[-4000:]}
        if p.returncode==0:
            row.update(json.loads(p.stdout))
        results.append(row)
    write_json(HERE/"results"/"api_incremental_probe.json", {"kind":"real TypeScript API, synthetic minimal project",
        "source_issue":"https://github.com/nestjs/nest-cli/issues/3312",
        "controlled_fault":"delete output directory but retain incremental metadata", "observations":results})
    for x in results:
        print(x['version'], x['returncode'], x.get('states'))

if __name__=='__main__':
    main()
