#!/usr/bin/env python3
"""Reproduce and compare npm platform-lock repair on actual host OS.

Controlled real-npm defect, not a mined industrial incident. Native checks run
only on the host OS; --os/--cpu simulation is never treated as native execution.
All installations disable lifecycle scripts. All output paths are new, scoped
under --output. No existing source lockfile is modified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

from repair import repair_lock, RepairRejected


CASES = {
    "rollup": ("rollup", "4.18.1", "require('rollup').rollup({input:'virtual',plugins:[{name:'inline',resolveId(id){return id==='virtual'?id:null},load(id){return id==='virtual'?'export const n=3':null}}]}).then(b=>b.generate({format:'esm'})).then(x=>{if(!Array.isArray(x.output)||!x.output[0].code)throw Error('empty output')}).catch(e=>{console.error(e);process.exit(1)})"),
    "esbuild": ("esbuild", "0.25.2", "require('esbuild').transformSync('const x = 3')"),
    "biome": ("@biomejs/biome", "1.9.4", None),
    "swc": ("@swc/core", "1.10.14", "require('@swc/core').transformSync('const x = 3', {jsc:{parser:{syntax:'ecmascript'}}})"),
    "lightningcss": ("lightningcss", "1.29.3", "require('lightningcss').transform({filename:'a.css',code:Buffer.from('a{color:red}')})"),
}
STRATEGIES = ("unmodified", "npm11-in-place", "npm12-in-place", "strict-donor", "clean-regenerate")
TIMEOUT = 180


def write_json(path: Path, value: object):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def call(args: list[str], cwd: Path, env: dict, timeout: int = TIMEOUT) -> dict:
    t = time.monotonic()
    try:
        p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", env=env, timeout=timeout, shell=False)
        code, stdout, stderr = p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired as e:
        code, stdout, stderr = 124, str(e.stdout or ""), str(e.stderr or "") + " timeout"
    return {"command": args, "returncode": code,
            "seconds": round(time.monotonic() - t, 4),
            "stdout_tail": stdout[-1800:], "stderr_tail": stderr[-2200:]}


def npm(version: str, args: list[str], cwd: Path, env: dict) -> dict:
    exe = Path(__file__).resolve().parent / "tools" / version / "node_modules/npm/bin/npm-cli.js"
    if not exe.is_file():
        raise FileNotFoundError(f"Install npm@{version} at {exe.parent.parent.parent.parent} (see README)")
    return call(["node", str(exe), *args, "--ignore-scripts", "--no-audit", "--no-fund"], cwd, env)


def demand_ok(observation: dict, context: str):
    if observation["returncode"]:
        raise RuntimeError(f"{context}: {json.dumps(observation)}")


def manifest(label: str, parent: str, pin: str):
    return {"name": f"n24-{label}", "version": "1.0.0", "private": True,
            "dependencies": {parent: pin, "picocolors": "1.0.0"}}


def make_manifest_loose(work: Path, parent: str):
    p = work / "package.json"
    obj = read_json(p)
    assert obj["dependencies"]["picocolors"] == "1.0.0"
    obj["dependencies"]["picocolors"] = "^1.0.0"
    write_json(p, obj)
    lock_path = work / "package-lock.json"
    lock = read_json(lock_path)
    assert lock["packages"][""]["dependencies"]["picocolors"] == "1.0.0"
    lock["packages"][""]["dependencies"]["picocolors"] = "^1.0.0"
    write_json(lock_path, lock)


def selector_matches(values: object, actual: str) -> bool:
    if not isinstance(values, list) or not values:
        return True
    positives = [s for s in values if isinstance(s, str) and not s.startswith("!")]
    negatives = [s[1:] for s in values if isinstance(s, str) and s.startswith("!")]
    return actual not in negatives and (not positives or actual in positives)


def host_metadata() -> dict:
    p = subprocess.run(["node", "-p", "JSON.stringify({os:process.platform,cpu:process.arch,node:process.version})"],
                       capture_output=True, text=True, check=True)
    obj = json.loads(p.stdout)
    obj["libc"] = "glibc" if obj["os"] == "linux" and platform.libc_ver()[0] == "glibc" else (
        "musl" if obj["os"] == "linux" else "not-applicable")
    obj["runner"] = os.environ.get("RUNNER_OS", "local")
    obj["runner_arch"] = os.environ.get("RUNNER_ARCH", platform.machine())
    return obj


def variant_report(packages: dict, parent: str, donor: dict, host: dict) -> dict:
    declared = donor["packages"]["node_modules/" + parent]["optionalDependencies"]
    platform_names, expected_here, absent_here, installed_here = [], [], [], []
    for name in sorted(declared):
        entry = donor["packages"].get("node_modules/" + name, {})
        if not (entry.get("os") and entry.get("cpu")):
            continue
        platform_names.append(name)
        present = "node_modules/" + name in packages
        # npm 10-era Rollup publishes some gnu/musl variants without `libc`
        # metadata. Infer only this suffix for *observability*, never repair.
        suffix_ok = not (host["os"] == "linux" and (
            (name.endswith("-musl") and host["libc"] == "glibc") or
            (name.endswith("-gnu") and host["libc"] == "musl")))
        if (suffix_ok and selector_matches(entry.get("os"), host["os"]) and
                selector_matches(entry.get("cpu"), host["cpu"]) and
                selector_matches(entry.get("libc"), host["libc"])):
            expected_here.append(name)
            if not present:
                absent_here.append(name)
            else:
                installed_here.append(name)
    return {"expected_portable_variants": len(platform_names),
            "present_portable_variants": sum("node_modules/" + n in packages for n in platform_names),
            "host_expected": expected_here, "host_missing": absent_here,
            "host_present": installed_here}


def changes(before: dict, after: dict, excluded: set[str]) -> dict:
    a, b = before["packages"], after["packages"]
    keys = set(a) | set(b)
    changed = [k for k in keys if k not in excluded and k in a and k in b and
               a[k].get("version") != b[k].get("version")]
    new = [k for k in keys if k not in excluded and k not in a and k in b]
    removed = [k for k in keys if k not in excluded and k in a and k not in b]
    modified_existing = [k for k in keys if k in a and k in b and a[k] != b[k]]
    return {"changed_non_target_versions": len(changed),
            "changed_non_target_version_keys": sorted(changed),
            "new_non_target_lock_nodes": sorted(new),
            "removed_non_target_lock_nodes": sorted(removed),
            "modified_existing_lock_nodes": sorted(modified_existing),
            "total_lock_nodes_changed_or_added": len([k for k in keys if a.get(k) != b.get(k)])}


def executable_check(case: str, work: Path, env: dict) -> dict:
    expression = CASES[case][2]
    if expression:
        return call(["node", "-e", expression], work, env, timeout=40)
    name = "biome.cmd" if os.name == "nt" else "biome"
    binary = work / "node_modules" / ".bin" / name
    if not binary.is_file():
        return {"command": [str(binary), "--version"], "returncode": 127,
                "seconds": 0, "stdout_tail": "", "stderr_tail": "CLI binary missing"}
    # The Windows .cmd wrapper needs cmd.exe; shell=False is preserved.
    cmd = ["cmd", "/d", "/s", "/c", str(binary), "--version"] if os.name == "nt" else [str(binary), "--version"]
    return call(cmd, work, env, timeout=40)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--families", default=",".join(CASES))
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--source-linux-locks", type=Path,
                    help="Import npm10 warm lockfiles created by the Linux producer job")
    args = ap.parse_args()
    selection = [c.strip() for c in args.families.split(",")]
    if any(c not in CASES for c in selection) or len(selection) != len(set(selection)):
        ap.error("Unknown or duplicate family")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    environment = dict(os.environ)
    environment.update(npm_config_cache=str(output / "_npm_cache"),
                       npm_config_audit="false", npm_config_fund="false",
                       npm_config_ignore_scripts="true", npm_config_update_notifier="false",
                       npm_config_fetch_retries="1", npm_config_fetch_timeout="60000")
    host = host_metadata()
    data = {"study": "N24", "evidence_class": "controlled npm-induced fault, not natural CI incident",
            "source_date_utc": "2026-11-18", "host": host,
            "github_sha": os.environ.get("GITHUB_SHA"),
            "github_run_id": os.environ.get("GITHUB_RUN_ID"),
            "strategies": list(STRATEGIES), "families": selection,
            "results": [], "errors": []}
    for case in selection:
        parent, pin, _ = CASES[case]
        work = output / case
        work.mkdir()
        fresh = work / "full_clean"
        warm = work / "warm_old"
        donor_work = work / "donor"
        for folder in (fresh, warm, donor_work):
            folder.mkdir()
        write_json(fresh / "package.json", manifest(case, parent, pin))
        write_json(warm / "package.json", manifest(case, parent, pin))
        setup = {}
        try:
            setup["full_lock_generation"] = npm("npm11", ["install", "--package-lock-only"], fresh, environment)
            demand_ok(setup["full_lock_generation"], f"{case} complete lock generation")
            setup["old_cold_install"] = npm("npm10", ["install"], warm, environment)
            demand_ok(setup["old_cold_install"], f"{case} npm10 cold install")
            full_old = read_json(warm / "package-lock.json")
            # This is the exact reproduction described by npm/cli#7961:
            # retain node_modules, remove the lockfile, then warm regenerate.
            (warm / "package-lock.json").unlink()
            setup["old_warm_regeneration"] = npm("npm10", ["install", "--package-lock-only"], warm, environment)
            demand_ok(setup["old_warm_regeneration"], f"{case} npm10 warm regeneration")
            write_json(donor_work / "package.json", {
                "name": "n24-independent-donor", "version": "1.0.0", "private": True,
                "dependencies": {parent: pin}})
            setup["independent_donor_generation"] = npm("npm11", ["install", "--package-lock-only"], donor_work, environment)
            demand_ok(setup["independent_donor_generation"], f"{case} donor")
            for folder in (fresh, warm):
                make_manifest_loose(folder, parent)
            complete, local_broken = read_json(fresh / "package-lock.json"), read_json(warm / "package-lock.json")
            broken = local_broken
            if args.source_linux_locks:
                imported = args.source_linux_locks.resolve() / case / "npm10_warm.json"
                if not imported.is_file():
                    raise FileNotFoundError(f"Missing Linux-produced source lock {imported}")
                broken = read_json(imported)
                if (broken.get("packages", {}).get("node_modules/" + parent, {}).get("version") != pin or
                    broken.get("packages", {}).get("", {}).get("dependencies", {}).get(parent) != pin):
                    raise RuntimeError("Cross-host source parent pin or package identity mismatch")
            donor = read_json(donor_work / "package-lock.json")
            setup["input_source"] = "Linux-hosted producer artifact" if args.source_linux_locks else "current native host"
            setup["local_npm10_warm_sha256"] = sha(warm / "package-lock.json")
            write_json(output / "evidence_locks" / case / "reference.json", complete)
            write_json(output / "evidence_locks" / case / "npm10_warm.json", broken)
            write_json(output / "evidence_locks" / case / "independent_donor.json", donor)
            old_cold_host = variant_report(full_old["packages"], parent, donor, host)
            input_broken_host = variant_report(broken["packages"], parent, donor, host)
            input_full_host = variant_report(complete["packages"], parent, donor, host)
            setup["old_cold_host"] = old_cold_host
            setup["broken_host"] = input_broken_host
            setup["complete_host"] = input_full_host
            setup["reproduced_defect"] = input_broken_host["present_portable_variants"] < input_full_host["present_portable_variants"]
            setup["input_hashes_sha256"] = {"complete": sha(fresh / "package-lock.json"),
                                            "npm10_warm": sha(warm / "package-lock.json"),
                                            "donor": sha(donor_work / "package-lock.json")}
            # The independent reference is run on the actual host, not a simulated target.
            reference = work / "independent_reference"
            reference.mkdir()
            shutil.copyfile(fresh / "package.json", reference / "package.json")
            shutil.copyfile(fresh / "package-lock.json", reference / "package-lock.json")
            setup["reference_install"] = npm("npm11", ["ci"], reference, environment)
            setup["reference_runtime"] = executable_check(case, reference, environment) if setup["reference_install"]["returncode"] == 0 else None
            setup["reference_usable"] = bool(setup["reference_runtime"] and setup["reference_runtime"]["returncode"] == 0)
            variants = set(donor["packages"]["node_modules/" + parent].get("optionalDependencies", {}))
            excluded = {"node_modules/" + v for v in variants}
            for condition, original in (("npm10_warm_defect", broken), ("intact_negative_control", complete)):
                for strategy in STRATEGIES:
                    trial = work / f"{condition}_{strategy}"
                    trial.mkdir()
                    write_json(trial / "package.json", read_json(fresh / "package.json"))
                    write_json(trial / "package-lock.json", original)
                    repair_metadata = None
                    treatment = {"command": [strategy], "returncode": 0, "seconds": 0.0,
                                 "stdout_tail": "no modification", "stderr_tail": ""}
                    start = time.monotonic()
                    if strategy == "npm11-in-place":
                        treatment = npm("npm11", ["install", "--package-lock-only"], trial, environment)
                    elif strategy == "npm12-in-place":
                        treatment = npm("npm12", ["install", "--package-lock-only"], trial, environment)
                    elif strategy == "strict-donor":
                        try:
                            new, repair_metadata = repair_lock(original, donor, parent)
                            write_json(trial / "package-lock.json", new)
                        except RepairRejected as err:
                            treatment = {"command": ["strict-donor"], "returncode": 78,
                                         "seconds": 0, "stdout_tail": "", "stderr_tail": str(err)}
                    elif strategy == "clean-regenerate":
                        (trial / "package-lock.json").unlink()
                        treatment = npm("npm11", ["install", "--package-lock-only"], trial, environment)
                    if strategy == "strict-donor":
                        treatment["seconds"] = round(time.monotonic() - start + setup["independent_donor_generation"]["seconds"], 4)
                    valid = (trial / "package-lock.json").is_file()
                    result = read_json(trial / "package-lock.json") if valid else {}
                    if valid:
                        write_json(output / "evidence_locks" / case /
                                   f"{condition}_{strategy}.json", result)
                    delta = changes(original, result, excluded) if valid else None
                    variant = variant_report(result.get("packages", {}), parent, donor, host) if valid else None
                    old_hash = sha(trial / "package-lock.json") if valid else None
                    installation = (npm("npm11", ["ci"], trial, environment) if valid and treatment["returncode"] == 0
                                    else {"command": ["ci"], "returncode": 78, "seconds": 0, "stdout_tail": "", "stderr_tail": "repair not applied"})
                    binary = (executable_check(case, trial, environment) if installation["returncode"] == 0 else
                              {"command": ["native-check"], "returncode": 78, "seconds": 0,
                               "stdout_tail": "", "stderr_tail": "npm ci failed or was skipped"})
                    data["results"].append({"family": case, "parent": parent, "pin": pin,
                        "condition": condition, "strategy": strategy,
                        "fault_present": setup["reproduced_defect"] if condition == "npm10_warm_defect" else False,
                        "reference_usable": setup["reference_usable"],
                        "repaired_runtime_ok": installation["returncode"] == 0 and binary["returncode"] == 0,
                        "treatment": treatment, "repair_audit": repair_metadata,
                        "comparison": delta, "platform_coverage": variant,
                        "npm_ci": installation, "native_execution": binary,
                        "lock_sha256": old_hash,
                        "lock_sha256_unchanged_by_ci": old_hash == sha(trial / "package-lock.json") if valid else None,
                        "lockfile_bytes": (trial / "package-lock.json").stat().st_size if valid else None})
            data.setdefault("setup", {})[case] = setup
            write_json(output / "runs.json", data)
            print(json.dumps({"family": case, "reproduced_fault": setup["reproduced_defect"],
                "reference_usable": setup["reference_usable"],
                "host": host, "finished_results": len(data["results"])}), flush=True)
        except Exception as e:
            data["errors"].append({"family": case, "exception": repr(e), "setup": setup})
            write_json(output / "runs.json", data)
            print(f"ERROR {case}: {e!r}", file=sys.stderr, flush=True)
    write_json(output / "runs.json", data)
    if data["errors"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
