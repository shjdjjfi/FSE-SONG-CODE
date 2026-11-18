#!/usr/bin/env python3
"""Execute *real committed* package-lock files on independent current hosts.

This is a retrospective reproducibility replay, not proof of a contemporaneous
production outage. Only package.json and package-lock.json are restored: no
project build scripts or actual business workloads are claimed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import time
import urllib.request
from pathlib import Path

from lock_lab import (STRATEGIES, call, changes, demand_ok, executable_check, host_metadata,
                      npm, read_json, sha, variant_report, write_json)
from repair import RepairRejected, repair_lock


# Selected *after* a structural gap was observed in the 17-repository audit.
# This is an explicitly post-hoc positive-case replay, not a prevalence sample.
SOURCES = {
    "cloudreve": {"repo": "cloudreve/frontend", "sha": "c7b6fa5288ed0490a5589ddff4f56ea1f96a5315", "families": ["rollup", "esbuild", "swc"]},
    "clasp": {"repo": "google/clasp", "sha": "e9441e57b0ae398fdb8524dada9372c1ed8590e0", "families": ["biome"]},
    "ollama": {"repo": "ollama/ollama-js", "sha": "c276d078eee37a0df003b9ee2120ec70327f32e9", "families": ["swc"]},
}
PARENTS = {"rollup": "rollup", "esbuild": "esbuild", "swc": "@swc/core", "biome": "@biomejs/biome"}


def download(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "fse-n24-replay/1.0"})
    with urllib.request.urlopen(req, timeout=55) as r:
        return r.read()


def npm_with_peer_fallback(argv: list[str], folder: Path, env: dict, npm_version: str = "npm11") -> tuple[dict, list, bool]:
    """Save strict result, then optional compat retry (never hide the failure)."""
    first = npm(npm_version, argv, folder, env)
    attempts = [first]
    if first["returncode"] == 0:
        return first, attempts, False
    fallback = npm(npm_version, [*argv, "--legacy-peer-deps"], folder, env)
    attempts.append(fallback)
    return fallback, attempts, True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--projects", default=",".join(SOURCES))
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    projects = [p.strip() for p in args.projects.split(",")]
    if any(p not in SOURCES for p in projects):
        ap.error("unknown project")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ)
    env.update(npm_config_cache=str(output / "_npm_cache"),
               npm_config_ignore_scripts="true", npm_config_audit="false", npm_config_fund="false",
               npm_config_update_notifier="false", npm_config_fetch_retries="1",
               npm_config_fetch_timeout="60000")
    host = host_metadata()
    report = {"study": "N24-historical-replay", "evidence_class": "Real committed lockfile, current-host replay; original industrial CI outcome unknown",
              "selection": "Post-hoc positives out of 17 fixed public repositories",
              "host": host, "github_sha": os.environ.get("GITHUB_SHA"),
              "github_run_id": os.environ.get("GITHUB_RUN_ID"), "projects": projects,
              "results": [], "errors": [], "setup": {}}
    for project in projects:
        source = SOURCES[project]
        root = output / project
        root.mkdir()
        setup = {"repo": source["repo"], "git_sha": source["sha"], "families": source["families"]}
        try:
            for name in ("package.json", "package-lock.json"):
                url = f"https://raw.githubusercontent.com/{source['repo']}/{source['sha']}/{name}"
                blob = download(url)
                (root / name).write_bytes(blob)
                setup[name] = {"source": url, "sha256": hashlib.sha256(blob).hexdigest(), "bytes": len(blob)}
            original = read_json(root / "package-lock.json")
            fixture_manifest = read_json(root / "package.json")
            setup["lockfile_version"] = original.get("lockfileVersion")
            donors, eligible, excluded = {}, [], set()
            for family in source["families"]:
                parent = PARENTS[family]
                node = original.get("packages", {}).get("node_modules/" + parent)
                if not isinstance(node, dict) or not node.get("version"):
                    setup.setdefault("skipped_parent", {})[family] = "no exact parent at root node_modules path"
                    continue
                version = node["version"]
                for variant in node.get("optionalDependencies", {}):
                    excluded.add("node_modules/" + variant)
                isolated = root / ("donor_" + family)
                isolated.mkdir()
                write_json(isolated / "package.json", {"name": "n24-replay-donor", "version": "1.0.0",
                                                       "private": True, "dependencies": {parent: version}})
                receipt = npm("npm11", ["install", "--package-lock-only"], isolated, env)
                setup.setdefault("donor_generations", {})[family] = receipt
                if receipt["returncode"]:
                    continue
                donors[family] = read_json(isolated / "package-lock.json")
                eligible.append(family)
            setup["eligible_families"] = eligible
            write_json(output / "evidence_locks" / project / "historical_original.json", original)
            for strategy in STRATEGIES:
                trial = root / strategy
                trial.mkdir()
                write_json(trial / "package.json", fixture_manifest)
                write_json(trial / "package-lock.json", original)
                treatment = {"command": [strategy], "returncode": 0, "seconds": 0.0,
                             "stdout_tail": "no modification", "stderr_tail": ""}
                treatment_attempts = [treatment]
                treatment_peer_fallback = False
                audit = {}
                if strategy == "npm11-in-place":
                    treatment, treatment_attempts, treatment_peer_fallback = npm_with_peer_fallback(
                        ["install", "--package-lock-only"], trial, env)
                elif strategy == "npm12-in-place":
                    treatment, treatment_attempts, treatment_peer_fallback = npm_with_peer_fallback(
                        ["install", "--package-lock-only"], trial, env, "npm12")
                elif strategy == "clean-regenerate":
                    (trial / "package-lock.json").unlink()
                    treatment, treatment_attempts, treatment_peer_fallback = npm_with_peer_fallback(
                        ["install", "--package-lock-only"], trial, env)
                elif strategy == "strict-donor":
                    t = time.monotonic()
                    working = original
                    for family in eligible:
                        try:
                            working, answer = repair_lock(working, donors[family], PARENTS[family])
                            audit[family] = answer
                        except RepairRejected as e:
                            audit[family] = {"rejected": str(e)}
                    write_json(trial / "package-lock.json", working)
                    treatment["seconds"] = round(time.monotonic() - t + sum(
                        setup["donor_generations"][f]["seconds"] for f in eligible), 4)
                    treatment_attempts = [treatment]
                valid = (trial / "package-lock.json").is_file()
                updated = read_json(trial / "package-lock.json") if valid else {}
                if valid:
                    write_json(output / "evidence_locks" / project / (strategy + ".json"), updated)
                structural = changes(original, updated, excluded) if valid else None
                if valid and treatment["returncode"] == 0:
                    install, ci_attempts, ci_peer_fallback = npm_with_peer_fallback(["ci"], trial, env)
                else:
                    install = {"command": ["ci"], "returncode": 78, "seconds": 0, "stderr_tail": "not runnable", "stdout_tail": ""}
                    ci_attempts, ci_peer_fallback = [install], False
                outcomes = {}
                for family in eligible:
                    parent = PARENTS[family]
                    out = executable_check(family, trial, env) if install["returncode"] == 0 else {
                        "command": ["native-check"], "returncode": 78, "seconds": 0,
                        "stdout_tail": "", "stderr_tail": "npm ci failed"}
                    cover = variant_report(updated.get("packages", {}), parent, donors[family], host) if valid else None
                    outcomes[family] = {"native_execution": out, "native_execution_ok": out["returncode"] == 0,
                                        "coverage": cover}
                report["results"].append({"project": project, "repo": source["repo"],
                    "commit": source["sha"], "strategy": strategy,
                    "treatment": treatment, "treatment_attempts": treatment_attempts,
                    "treatment_peer_fallback": treatment_peer_fallback,
                    "npm_ci": install, "npm_ci_attempts": ci_attempts,
                    "ci_peer_fallback": ci_peer_fallback, "per_parent": outcomes,
                    "repair_audit": audit, "comparison": structural,
                    "lock_sha256": sha(trial / "package-lock.json") if valid else None})
                write_json(output / "runs.json", report)
            report["setup"][project] = setup
            write_json(output / "runs.json", report)
            print(json.dumps({"project": project, "source_commit": source["sha"],
                              "families": eligible, "n_strategies": len(STRATEGIES)}), flush=True)
        except Exception as e:
            report["errors"].append({"project": project, "error": repr(e), "setup": setup})
            report["setup"][project] = setup
            write_json(output / "runs.json", report)
            print(f"HISTORICAL ERROR {project}: {e!r}", file=sys.stderr, flush=True)
    write_json(output / "runs.json", report)
    if report["errors"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
