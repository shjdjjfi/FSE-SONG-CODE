#!/usr/bin/env python3
"""Reproducible TypeScript output-recovery experiments for N21.

Uses real pinned source snapshots. All faults are researcher-induced. The
independent clean compiler output is used ONLY as an evaluation oracle; the
recovery strategies never see it. No CI incident rate is estimated.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import random
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import time
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent

SOURCES = {
    "typescript-5.9.3.tgz": (
        "https://registry.npmjs.org/typescript/-/typescript-5.9.3.tgz",
        "10e108c9cf7d5f2879053dff18515fb405abf2ccef63eaaf017d9c571687a1d3",
    ),
    "ts-pattern-v5.8.0.zip": (
        "https://codeload.github.com/gvergnaud/ts-pattern/zip/refs/tags/v5.8.0",
        "766efbe8cb563aa30365aa428670a3d834cc1fdb78ceaef9b5e08ac4d286f6f9",
    ),
    "zod-3.25.76.tgz": (
        "https://registry.npmjs.org/zod/-/zod-3.25.76.tgz",
        "9e1f1a05f0dd0c1dab64ee91ceb9bf55cd44d35368c70edda80a2fdc70a88377",
    ),
    "neverthrow-v8.2.0.zip": (
        "https://codeload.github.com/supermacro/neverthrow/zip/refs/tags/v8.2.0",
        "38d548fc63ae5400b1df99c4385f38183abb6cd48243671d7762e1251b310006",
    ),
    "mitt-3.0.1.zip": (
        "https://codeload.github.com/developit/mitt/zip/refs/tags/3.0.1",
        "a362926811cb6d28e52fa7f1276c9189595081ffa18fd3ceb87a022d26ba3a2d",
    ),
    "quramy-3fa93f.zip": (
        "https://codeload.github.com/Quramy/npm-ts-workspaces-example/zip/3fa93f092298cfb6be302d9d2eb10a411f4ae3fe",
        "8580b70de243de97462b721e8acb6231d7de1e79352b7ec8d4b8cff163931a01",
    ),
    "andrewthauer-4250b1a.zip": (
        "https://codeload.github.com/andrewthauer/ts-monorepo/zip/4250b1ad404027b5f7f2637be79bac61164602fa",
        "cb02536faab6b03f6c580075c2d849b828cfcb1c5b1d4caf58cb2cc4694cd4ed",
    ),
    "typescript-repo-v5.9.3.zip": (
        "https://codeload.github.com/microsoft/TypeScript/zip/refs/tags/v5.9.3",
        "8b6465f4c5472df45119a978e6a6a459ef139981c0978cb97a280e9cf68d3f8b",
    ),
}

CASE_SPECS = {
    "typescript": {
        "kind": "native TypeScript v5.9.3 compiler/jsTyping/services project-reference subgraph; declaration-only builds",
        "solution": "tsconfig.n21.json",
        "projects": {
            "compiler": {"dir": "src/compiler", "out": "../../built/local/compiler", "info": "../../built/local/compiler/tsconfig.tsbuildinfo"},
            "jsTyping": {"dir": "src/jsTyping", "out": "../../built/local/jsTyping", "info": "../../built/local/jsTyping/tsconfig.tsbuildinfo"},
            "services": {"dir": "src/services", "out": "../../built/local/services", "info": "../../built/local/services/tsconfig.tsbuildinfo"},
        },
    },
    "libraries": {
        "kind": "constructed workspace of four independent real OSS packages",
        "solution": "tsconfig.json",
        "projects": {
            "ts-pattern": {"dir": "packages/ts-pattern", "out": "dist", "info": "cache.tsbuildinfo"},
            "zod": {"dir": "packages/zod", "out": "dist", "info": "cache.tsbuildinfo"},
            "neverthrow": {"dir": "packages/neverthrow", "out": "dist", "info": "cache.tsbuildinfo"},
            "mitt": {"dir": "packages/mitt", "out": "dist", "info": "cache.tsbuildinfo"},
        },
    },
    "andrewthauer": {
        "kind": "native, checked-in project-reference example (source unchanged)",
        "solution": "packages/tsconfig.json",
        "projects": {
            "core": {"dir": "packages/core", "out": "dist", "info": "../../.build-cache/core.tsbuildinfo"},
            "api": {"dir": "packages/api", "out": "dist", "info": "../../.build-cache/api.tsbuildinfo"},
            "cli": {"dir": "packages/cli", "out": "dist", "info": "../../.build-cache/cli.tsbuildinfo"},
            "web": {"dir": "packages/web", "out": "dist", "info": "../../.build-cache/web.tsbuildinfo"},
        },
    },
    "quramy": {
        "kind": "native, checked-in project-reference example (npm ci dependencies)",
        "solution": "tsconfig.build.json",
        "projects": {
            "x-core": {"dir": "packages/x-core", "out": "lib", "info": "tsconfig.tsbuildinfo"},
            "x-cli": {"dir": "packages/x-cli", "out": "lib", "info": "tsconfig.tsbuildinfo"},
        },
    },
}


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def clean_relative(path: str) -> Path:
    p = PurePosixPath(path)
    if p.is_absolute() or any(s in ("..", "") for s in p.parts):
        raise ValueError(f"unsafe archive path: {path}")
    return Path(*p.parts)


def extract_zip_subset(archive: Path, dest: Path, predicate, strip_first=True) -> int:
    count = 0
    with zipfile.ZipFile(archive) as z:
        for member in z.infolist():
            if member.is_dir():
                continue
            p = clean_relative(member.filename)
            parts = p.parts[1:] if strip_first else p.parts
            if not parts or not predicate(parts):
                continue
            target = dest.joinpath(*parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(z.read(member))
            count += 1
    return count


def download_inputs(downloads: Path, selected: set[str]) -> None:
    downloads.mkdir(parents=True, exist_ok=True)
    for name in selected:
        url, digest = SOURCES[name]
        dest = downloads / name
        if dest.is_file() and sha_file(dest) == digest:
            continue
        if dest.exists():
            raise RuntimeError(f"Archive exists but hash mismatches: {dest}")
        tmp = downloads / (name + ".partial")
        try:
            with urllib.request.urlopen(url, timeout=90) as response, tmp.open("wb") as f:
                shutil.copyfileobj(response, f)
            if sha_file(tmp) != digest:
                raise RuntimeError(f"SHA mismatch after download: {name}")
            tmp.replace(dest)
        finally:
            if tmp.exists():
                tmp.unlink()


def prepare_libraries(dest: Path, archives: Path) -> None:
    mapping = {
        "ts-pattern": "ts-pattern-v5.8.0.zip",
        "zod": "zod-3.25.76.tgz",
        "neverthrow": "neverthrow-v8.2.0.zip",
        "mitt": "mitt-3.0.1.zip",
    }
    for name, archive in mapping.items():
        project = dest / "packages" / name
        source = project / "src"
        source.mkdir(parents=True, exist_ok=True)
        if name == "ts-pattern":
            def pred(parts):
                return len(parts) >= 3 and parts[0] == "src" and parts[-1].endswith(".ts")
            with zipfile.ZipFile(archives / archive) as z:
                for item in z.namelist():
                    p = clean_relative(item)
                    if len(p.parts) < 3 or p.parts[1] != "src" or p.suffix != ".ts":
                        continue
                    target = source.joinpath(*p.parts[2:])
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(z.read(item))
        elif name == "zod":
            with tarfile.open(archives / archive) as t:
                for item in t:
                    p = clean_relative(item.name)
                    if (not item.isfile() or len(p.parts) < 4 or p.parts[:3] != ("package", "src", "v3")
                            or p.suffix != ".ts" or {"tests", "benchmarks"} & set(p.parts)):
                        continue
                    target = source.joinpath(*p.parts[3:])
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(t.extractfile(item).read())
        else:
            with zipfile.ZipFile(archives / archive) as z:
                for item in z.namelist():
                    p = clean_relative(item)
                    if len(p.parts) < 3 or p.parts[1] != "src" or p.suffix not in (".ts", ".tsx"):
                        continue
                    target = source.joinpath(*p.parts[2:])
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(z.read(item))
        config = {"compilerOptions": {"target": "ES2022", "module": "CommonJS", "strict": True,
            "skipLibCheck": True, "composite": True, "rootDir": "src", "outDir": "dist",
            "tsBuildInfoFile": "cache.tsbuildinfo", "types": []},
            "include": ["src/**/*.ts"], "exclude": ["**/*.test.ts", "**/tests/**"]}
        # neverthrow's own upstream tsconfig deliberately uses strict: false.
        # Using strict: true with TS 5.9 raises unrelated pre-existing type errors.
        if name == "neverthrow":
            config["compilerOptions"]["strict"] = False
        write_json(project / "tsconfig.json", config)
    write_json(dest / "tsconfig.json", {"files": [], "references": [
        {"path": CASE_SPECS["libraries"]["projects"][name]["dir"]}
        for name in mapping]})


def dependency_install(dest: Path) -> dict:
    command = ["npm", "ci", "--ignore-scripts", "--no-audit", "--no-fund"]
    begin = time.perf_counter()
    cp = subprocess.run(command, cwd=dest, capture_output=True, text=True, timeout=240)
    return {"argv": command, "exit": cp.returncode, "stdout_tail": cp.stdout[-2500:],
            "stderr_tail": cp.stderr[-2500:], "seconds": round(time.perf_counter() - begin, 4)}


def prepare_native(case: str, dest: Path, archives: Path, runtime: Path) -> dict:
    archive = "andrewthauer-4250b1a.zip" if case == "andrewthauer" else "quramy-3fa93f.zip"
    n = extract_zip_subset(archives / archive, dest, lambda p: True)
    extra = {"extracted_files": n}
    if case == "quramy":
        deps = runtime / "dependencies" / "quramy"
        deps.mkdir(parents=True, exist_ok=True)
        extract_zip_subset(archives / archive, deps, lambda p: True)
        log = ({"argv": ["npm", "ci"], "exit": 0, "reused": True}
               if (deps / "node_modules" / "@types" / "node").exists() else dependency_install(deps))
        extra["npm_ci"] = log
        if log["exit"]:
            raise RuntimeError(f"npm ci error: {log}")
        links = dest / "node_modules"
        if links.is_symlink():
            links.unlink()
        links.mkdir(exist_ok=True)
        (links / "@types").symlink_to(deps / "node_modules" / "@types", target_is_directory=True)
        (links / "minimist").symlink_to(deps / "node_modules" / "minimist", target_is_directory=True)
        (links / "@quramy").mkdir(exist_ok=True)
        for name in ("x-core", "x-cli"):
            (links / "@quramy" / name).symlink_to(Path("../../packages") / name, target_is_directory=True)
    return extra


def prepare_typescript(dest: Path, archives: Path, runtime: Path) -> dict:
    selected = {"compiler", "jsTyping", "services"}
    def predicate(parts):
        return ((len(parts) > 2 and parts[0] == "src" and parts[1] in selected
                 and parts[-1].endswith((".ts", ".json")))
                or parts == ("src", "tsconfig-base.json")
                or parts == ("package.json",)
                or parts == ("scripts", "processDiagnosticMessages.mjs"))
    extracted = extract_zip_subset(archives / "typescript-repo-v5.9.3.zip", dest, predicate)
    generated = subprocess.run(["node", "scripts/processDiagnosticMessages.mjs",
        "src/compiler/diagnosticMessages.json"], cwd=dest,
        capture_output=True, text=True, timeout=90)
    if generated.returncode:
        raise RuntimeError(f"Upstream diagnostics generation failed: {generated.stderr}")
    write_json(dest / "tsconfig.n21.json", {"files": [], "references": [
        {"path": "src/services"}, {"path": "src/jsTyping"}, {"path": "src/compiler"}]})
    deps = runtime / "dependencies" / "typescript"
    deps.mkdir(parents=True, exist_ok=True)
    if not (deps / "node_modules" / "@types" / "source-map-support").exists():
        argv = ["npm", "install", "--ignore-scripts", "--no-audit", "--no-fund", "--save-exact",
                "@types/node@22.15.3", "@types/source-map-support@0.5.10", "source-map-support@0.5.21"]
        cp = subprocess.run(argv, cwd=deps, capture_output=True, text=True, timeout=180)
        if cp.returncode:
            raise RuntimeError(f"Failed installing @types/node: {cp.stdout} {cp.stderr}")
    if not (dest / "node_modules").exists():
        (dest / "node_modules").symlink_to(deps / "node_modules", target_is_directory=True)
    return {"extracted": extracted, "subgraph": sorted(selected), "node_typings": "@types/node@22.15.3",
            "source_map_support": "0.5.21", "source_map_support_types": "0.5.10",
            "upstream_diagnostics_generator": generated.stdout.strip()}


def source_units(root: Path, spec: dict) -> dict[str, int]:
    return {name: len([f for f in ((root / p["dir"] / "src") if
                        (root / p["dir"] / "src").is_dir() else (root / p["dir"])).rglob("*")
                        if f.is_file() and f.suffix in (".ts", ".tsx")])
            for name, p in spec["projects"].items()}


def expected_tree(root: Path, spec: dict) -> dict[str, dict[str, str]]:
    answer = {}
    for name, p in spec["projects"].items():
        directory = root / p["dir"] / p["out"]
        files = {}
        if directory.is_dir():
            for f in sorted(directory.rglob("*")):
                if f.is_file() and not f.is_symlink() and f.suffix != ".tsbuildinfo":
                    files[f.relative_to(directory).as_posix()] = sha_file(f)
        answer[name] = files
    return answer


def summary_differences(expected, observed):
    missing, altered, excess = 0, 0, 0
    for p in expected:
        e, o = expected[p], observed[p]
        missing += len(e.keys() - o.keys())
        altered += sum(e[k] != o[k] for k in e.keys() & o.keys())
        excess += len(o.keys() - e.keys())
    return {"missing": missing, "altered": altered, "extra": excess}


def info_file(root: Path, p: dict) -> Path:
    return (root / p["dir"] / p["info"]).resolve(strict=False)


def run_build(root: Path, spec: dict, compiler: Path, force=False) -> dict:
    argv = ["node", str(compiler), "--build", spec["solution"], "--verbose"]
    if force:
        argv.append("--force")
    before = time.perf_counter()
    cp = subprocess.run(argv, cwd=root, capture_output=True, text=True, timeout=240)
    output = cp.stdout.replace("\r", "")
    names = []
    for m in re.finditer(r"Building project ['\"]([^'\"]+)['\"]", output):
        stem = Path(m.group(1)).parent
        for name, p in spec["projects"].items():
            if stem == (root / p["dir"]) or stem.resolve() == (root / p["dir"]).resolve():
                names.append(name)
                break
    return {"argv": argv, "exit": cp.returncode, "seconds": round(time.perf_counter() - before, 4),
            "compiled_projects": list(dict.fromkeys(names)), "stdout": output[-9000:], "stderr": cp.stderr[-4500:]}


def purge_outputs(root: Path, spec: dict) -> None:
    for p in spec["projects"].values():
        target = root / p["dir"] / p["out"]
        if target.exists():
            # Exactly a fixture-owned project's output folder; never follow symlinks.
            if target.is_symlink():
                raise RuntimeError(f"Refuse to remove linked output: {target}")
            shutil.rmtree(target)
        inf = info_file(root, p)
        if inf.is_file():
            inf.unlink()


def prepare_all(archives: Path, runtime: Path, requested: list[str]) -> None:
    names = {"typescript-5.9.3.tgz"}
    if "libraries" in requested:
        names.update({"ts-pattern-v5.8.0.zip", "zod-3.25.76.tgz", "neverthrow-v8.2.0.zip", "mitt-3.0.1.zip"})
    if "andrewthauer" in requested:
        names.add("andrewthauer-4250b1a.zip")
    if "quramy" in requested:
        names.add("quramy-3fa93f.zip")
    if "typescript" in requested:
        names.add("typescript-repo-v5.9.3.zip")
    download_inputs(archives, names)
    compiler = runtime / "compiler" / "package" / "bin" / "tsc"
    if not compiler.is_file():
        (runtime / "compiler").mkdir(parents=True, exist_ok=True)
        with tarfile.open(archives / "typescript-5.9.3.tgz") as tar:
            tar.extractall(runtime / "compiler", filter="data")
    assert compiler.is_file()
    for case in requested:
        spec = CASE_SPECS[case]
        template = runtime / "templates" / case
        if (template / "verified.json").is_file():
            print(f"[prepare] {case}: verified template already exists", flush=True)
            continue
        template.mkdir(parents=True, exist_ok=True)
        extra = {}
        if case == "libraries":
            prepare_libraries(template, archives)
        elif case == "typescript":
            extra = prepare_typescript(template, archives, runtime)
        else:
            extra = prepare_native(case, template, archives, runtime)
        build = run_build(template, spec, compiler)
        if build["exit"]:
            write_json(runtime / "prepare_failures" / f"{case}.json", {"case": case, "build": build, "extra": extra})
            raise RuntimeError(f"Build failed for {case}: {build['stderr']} {build['stdout'][-1500:]}")
        observed = expected_tree(template, spec)
        if any(not x for x in observed.values()):
            raise RuntimeError(f"Project with no outputs: {case}, { {k:len(v) for k,v in observed.items()} }")
        clean = runtime / "oracles" / case
        if not clean.exists():
            shutil.copytree(template, clean, symlinks=True)
        purge_outputs(clean, spec)
        independent = run_build(clean, spec, compiler)
        truth = expected_tree(clean, spec)
        identical = truth == observed
        meta = {"case": case, "kind": spec["kind"], "source_units": source_units(template, spec),
                "outputs": {p: len(files) for p, files in observed.items()},
                "expected_digests": truth, "compiler": "typescript@5.9.3", "initial_build": build,
                "independent_clean_build": independent, "oracle_exact_match": identical, "extra": extra}
        write_json(runtime / "metadata" / f"{case}.json", meta)
        if independent["exit"] or not identical:
            raise RuntimeError(f"Independent oracle disagrees for {case}")
        write_json(template / "verified.json", {"case": case, "source_units": meta["source_units"],
                                                "outputs": meta["outputs"]})
        print(f"[prepare] {case}: {meta['source_units']} source units; {meta['outputs']} outputs; exact clean match", flush=True)
    write_json(runtime / "environment.json", {"run_utc": datetime.now(timezone.utc).isoformat(),
               "platform": platform.platform(), "node": subprocess.check_output(["node", "--version"], text=True).strip(),
               "python": sys.version, "archives": {k: SOURCES[k][1] for k in sorted(names)}})


def target_for_fault(root: Path, project: dict, truth: dict[str, str], fault: str, seed: int) -> Path | None:
    if fault in ("intact", "buildinfo_missing"):
        return None
    suffix = ".d.ts" if fault in ("delete_dts", "corrupt_dts") else ".js"
    candidates = sorted(p for p in truth if p.endswith(suffix))
    if fault == "delete_nested_js":
        candidates = [p for p in candidates if "/" in p] or candidates
    if fault == "delete_entry_js":
        candidates = [p for p in candidates if p.endswith("index.js")] or candidates
    if not candidates:
        return None
    selected = candidates[random.Random(seed).randrange(len(candidates))]
    return root / project["dir"] / project["out"] / selected


def inject_fault(root: Path, spec: dict, project: str, truth: dict, fault: str, seed: int) -> dict:
    p = spec["projects"][project]
    target = target_for_fault(root, p, truth[project], fault, seed)
    if fault in ("intact", "buildinfo_missing"):
        if fault == "buildinfo_missing":
            inf = info_file(root, p)
            if inf.exists():
                inf.unlink()
        return {"target": None, "fault": fault}
    if fault == "extra_stale":
        file = root / p["dir"] / p["out"] / "stale/removed-module.js"
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("// synthetic obsolete compiler output\n", encoding="utf-8")
        return {"target": file.relative_to(root).as_posix(), "fault": fault}
    if fault == "erase_dist":
        dest = root / p["dir"] / p["out"]
        shutil.rmtree(dest)
        return {"target": dest.relative_to(root).as_posix(), "fault": fault}
    if target is None or not target.is_file():
        raise ValueError(f"No matching output for {project}/{fault}")
    if fault.startswith("delete_"):
        target.unlink()
    elif fault.startswith("corrupt_"):
        data = bytearray(target.read_bytes())
        if not data:
            data = bytearray(b"x")
        data[len(data) // 2] ^= 1
        target.write_bytes(data)
    else:
        raise ValueError(f"unsupported fault: {fault}")
    return {"target": target.relative_to(root).as_posix(), "fault": fault}


def detect_damage(root: Path, spec: dict, expected: dict, hashes: bool) -> tuple[list[str], dict]:
    damaged = []
    scan_bytes = 0
    for name, p in spec["projects"].items():
        out = root / p["dir"] / p["out"]
        found = {}
        if out.exists():
            for f in out.rglob("*"):
                if f.is_symlink():
                    damaged.append(name)
                    continue
                if not f.is_file():
                    continue
                # Build state is tracked separately: a .tsbuildinfo file can
                # legitimately live inside outDir but is NOT a deployable
                # output in the clean-artifact digest manifest.
                if f.suffix == ".tsbuildinfo":
                    continue
                rel = f.relative_to(out).as_posix()
                found[rel] = sha_file(f) if hashes else None
                if hashes:
                    scan_bytes += f.stat().st_size
        if set(found) != set(expected[name]) or (hashes and any(
                found[f] != expected[name][f] for f in found.keys() & expected[name].keys())):
            damaged.append(name)
    return list(dict.fromkeys(damaged)), {"bytes_hashed": scan_bytes, "digest_audit": hashes}


def input_fingerprint(root: Path, spec: dict) -> str:
    """Conservative content key over included source/config/lock files.

    A real deployment should extend this key to resolved external dependencies,
    compiler binary and environment/configuration relevant to emission. The
    controlled fixtures pin compiler and external dependency snapshots.
    """
    files = set(root.glob("tsconfig*.json")) | set(root.glob("package*.json"))
    files.update(root.glob("src/tsconfig*.json"))
    for p in spec["projects"].values():
        project = root / p["dir"]
        files.update(project.glob("tsconfig*.json"))
        files.update(project.glob("package*.json"))
        source = project / "src"
        if not source.is_dir():
            source = project
        files.update(f for f in source.rglob("*") if f.is_file() and
                     f.suffix in (".ts", ".tsx") and not f.is_symlink())
    h = hashlib.sha256()
    for f in sorted(files):
        h.update(f.relative_to(root).as_posix().encode("utf-8") + b"\0")
        h.update(f.read_bytes() + b"\0")
    return h.hexdigest()


def recover(root: Path, original: Path, spec: dict, compiler: Path,
            arm: str, manifest: dict) -> tuple[dict, list[dict]]:
    before = time.perf_counter()
    detected, scan = [], {"bytes_hashed": 0, "digest_audit": False}
    logs = []
    restored_bytes = 0
    input_key_rejected = False
    if arm == "guarded_hash" and input_fingerprint(root, spec) != input_fingerprint(original, spec):
        input_key_rejected = True
        # Fail closed on changed inputs: do not apply stale output digests.
        purge_outputs(root, spec)
        logs.append(run_build(root, spec, compiler))
    elif arm in ("selective_path", "selective_hash", "guarded_hash"):
        detected, scan = detect_damage(root, spec, manifest, hashes=(arm != "selective_path"))
        for name in detected:
            p = spec["projects"][name]
            info = info_file(root, p)
            if info.exists():
                info.unlink()
            # Remove orphan outputs, since tsc itself does not prune old names.
            out = root / p["dir"] / p["out"]
            if out.exists():
                for f in out.rglob("*"):
                    if (f.is_file() and f.suffix != ".tsbuildinfo" and
                            f.relative_to(out).as_posix() not in manifest[name]):
                        f.unlink()
        logs.append(run_build(root, spec, compiler))
    elif arm == "standard":
        logs.append(run_build(root, spec, compiler))
    elif arm == "force_all":
        logs.append(run_build(root, spec, compiler, force=True))
    elif arm == "invalidate_all":
        for p in spec["projects"].values():
            info = info_file(root, p)
            if info.exists():
                info.unlink()
        logs.append(run_build(root, spec, compiler))
    elif arm == "clean_all":
        purge_outputs(root, spec)
        logs.append(run_build(root, spec, compiler))
    elif arm == "full_cache":
        # Simulate a complete, verified cache hit. Not applicable if cache is absent!
        for p in spec["projects"].values():
            output = root / p["dir"] / p["out"]
            cached = original / p["dir"] / p["out"]
            if output.exists():
                shutil.rmtree(output)
            shutil.copytree(cached, output)
            restored_bytes += sum(f.stat().st_size for f in output.rglob("*") if f.is_file())
            source_info = info_file(original, p)
            target_info = info_file(root, p)
            target_info.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_info, target_info)
            restored_bytes += target_info.stat().st_size
    else:
        raise ValueError(arm)
    return ({"detect": detected, "scan": scan, "work_seconds": round(time.perf_counter() - before, 4),
             "restored_bytes": restored_bytes, "input_key_rejected": input_key_rejected,
             "compiled_projects": sorted(set(n for log in logs for n in log["compiled_projects"])),
             "build_succeeded": all(log["exit"] == 0 for log in logs)}, logs)


def run_trials(runtime: Path, out_dir: Path, cases: list[str], projects_by_case: dict,
               faults: list[str], arms: list[str], seeds: list[int], max_trials: int | None) -> None:
    compiler = runtime / "compiler" / "package" / "bin" / "tsc"
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / "trials.jsonl"
    errors_path = out_dir / "errors.jsonl"
    completed = set()
    if output_path.exists():
        for line in output_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                x = json.loads(line)
                completed.add((x["case"], x["project"], x["fault"], x["seed"], x["arm"]))
    trial_idx = 0
    trial = out_dir / "active_trial"
    for case in cases:
        spec = CASE_SPECS[case]
        template = runtime / "templates" / case
        meta_path = runtime / "metadata" / f"{case}.json"
        if not meta_path.is_file():
            raise RuntimeError(f"Run prepare first, missing {meta_path}")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        truth = meta["expected_digests"]
        unit_counts = meta["source_units"]
        selected = projects_by_case.get(case) or list(spec["projects"])
        for project in selected:
            for fault in faults:
                # Some native projects legitimately emit JS but no declaration,
                # or declarations only. Do not invent a missing output class.
                needed_suffix = (".d.ts" if fault in ("delete_dts", "corrupt_dts")
                                 else ".js" if fault in ("delete_nested_js", "delete_entry_js", "corrupt_js")
                                 else None)
                if needed_suffix and not any(s.endswith(needed_suffix) for s in truth[project]):
                    print(f"[skip] {case}/{project} {fault}: no {needed_suffix} emitted", flush=True)
                    continue
                for seed in seeds:
                    for arm in arms:
                        key = (case, project, fault, seed, arm)
                        if key in completed:
                            continue
                        if max_trials is not None and trial_idx >= max_trials:
                            return
                        trial_idx += 1
                        if trial.exists():
                            # Only remove our own fixed, task-created staging directory.
                            shutil.rmtree(trial)
                        shutil.copytree(template, trial, symlinks=True,
                                        ignore=shutil.ignore_patterns("verified.json"))
                        try:
                            injected = inject_fault(trial, spec, project, truth, fault, seed)
                            damaged_before = summary_differences(truth, expected_tree(trial, spec))
                            record, logs = recover(trial, template, spec, compiler, arm, truth)
                            seen = expected_tree(trial, spec)
                            differences = summary_differences(truth, seen)
                            success = record["build_succeeded"] and seen == truth
                            compiled_units = sum(unit_counts.get(name, 0) for name in record["compiled_projects"])
                            row = {"case": case, "kind": spec["kind"], "project": project,
                                "fault": fault, "seed": seed, "arm": arm, "injected": injected,
                                "before": damaged_before, "correct": success, "after": differences,
                                "compiled_source_units_proxy": compiled_units,
                                "repair": record, "logs": logs}
                            with output_path.open("a", encoding="utf-8") as f:
                                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                            print(f"[{trial_idx:04d}] {case}/{project} {fault} {arm} seed={seed} "
                                f"correct={success} sources={compiled_units} {record['work_seconds']:.2f}s", flush=True)
                        except Exception as exc:
                            with errors_path.open("a", encoding="utf-8") as f:
                                f.write(json.dumps({"key": key, "error": str(exc)}) + "\n")
                            raise
    if trial.exists():
        shutil.rmtree(trial)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action", choices=("prepare", "run"))
    ap.add_argument("--archives", type=Path, default=HERE.parent / "n21_downloads")
    ap.add_argument("--runtime", type=Path, default=HERE / "runtime")
    ap.add_argument("--results", type=Path, default=HERE / "results")
    ap.add_argument("--cases", default="libraries,andrewthauer,quramy")
    ap.add_argument("--projects", default="", help="Optional case:project,case:project")
    ap.add_argument("--faults", default="delete_nested_js,delete_dts,corrupt_js,corrupt_dts,extra_stale,intact")
    ap.add_argument("--arms", default="standard,selective_path,selective_hash,invalidate_all,clean_all,force_all,full_cache")
    ap.add_argument("--seeds", default="17")
    ap.add_argument("--max-trials", type=int)
    args = ap.parse_args()
    cases = [x for x in args.cases.split(",") if x]
    if set(cases) - set(CASE_SPECS):
        raise ValueError(f"Unknown cases {set(cases) - set(CASE_SPECS)}")
    if args.action == "prepare":
        prepare_all(args.archives.resolve(), args.runtime.resolve(), cases)
    else:
        selection = {}
        for item in [x for x in args.projects.split(",") if x]:
            a, b = item.split(":", 1)
            selection.setdefault(a, []).append(b)
        run_trials(args.runtime.resolve(), args.results.resolve(), cases, selection,
            [x for x in args.faults.split(",") if x], [x for x in args.arms.split(",") if x],
            [int(x) for x in args.seeds.split(",") if x], args.max_trials)


if __name__ == "__main__":
    main()
