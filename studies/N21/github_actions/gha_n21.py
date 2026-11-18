#!/usr/bin/env python3
"""GitHub Actions N21/Attest fixture (NOT a natural industrial incident).

The fixture has two independent TypeScript build units. The workflow creates
complete and deliberately partial caches in a warm job, then uses the actual
Attest/typescript-cache-action in other GitHub-hosted jobs. Evidence contains
exact emitted-file SHA-256 digests from a trusted independent cold build.

Local testing of this script does NOT count as actual GitHub Actions execution.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import shutil
import subprocess
import tempfile
import time
from pathlib import Path


def put_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def root_path(args: argparse.Namespace) -> Path:
    return args.root.resolve()


def compiler() -> Path:
    if "N21_TSC" in os.environ:
        p = Path(os.environ["N21_TSC"]).resolve()
    else:
        p = (Path.cwd() / "node_modules" / "typescript" / "bin" / "tsc").resolve()
    if not p.is_file():
        raise RuntimeError(f"TypeScript compiler unavailable: {p}; install typescript@5.9.3")
    return p


def input_files(root: Path):
    # Emitted *.d.ts are TypeScript files too, but are *outputs* under dist/.
    # Including them would incorrectly treat a damaged declaration output as
    # an input change and trigger a full clean fallback in guarded_sha.
    files = [root / "tsconfig.json"]
    for name in ("alpha", "beta"):
        project = root / "packages" / name
        files.append(project / "tsconfig.json")
        files.extend(p for p in (project / "src").rglob("*")
                     if p.is_file() and p.suffix in (".ts", ".tsx"))
    return sorted(files)


def input_digest(root: Path) -> str:
    h = hashlib.sha256(b"typescript@5.9.3\0")
    for p in input_files(root):
        h.update(p.relative_to(root).as_posix().encode("utf-8") + b"\0")
        h.update(p.read_bytes() + b"\0")
    return h.hexdigest()


def init_fixture(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for project in ("alpha", "beta"):
        package = root / "packages" / project
        (package / "src").mkdir(parents=True, exist_ok=True)
        (package / "src" / "index.ts").write_text(
            f"export const {project} = '{project}-n21';\n", encoding="utf-8")
        put_json(package / "tsconfig.json", {
            "compilerOptions": {"target": "ES2022", "module": "CommonJS", "strict": True,
                                "declaration": True, "composite": True, "rootDir": "src",
                                "outDir": "dist", "tsBuildInfoFile": "cache.tsbuildinfo"},
            "include": ["src/**/*.ts"]})
    put_json(root / "tsconfig.json", {"files": [], "references": [
        {"path": "packages/alpha"}, {"path": "packages/beta"}]})


def output_snapshot(root: Path) -> dict[str, dict[str, str]]:
    snapshot = {}
    for project in ("alpha", "beta"):
        dist = root / "packages" / project / "dist"
        snapshot[project] = {p.relative_to(dist).as_posix(): hash_file(p)
                             for p in sorted(dist.rglob("*")) if p.is_file() and
                             p.suffix != ".tsbuildinfo"} if dist.is_dir() else {}
    return snapshot


def diff(expected: dict, found: dict) -> dict:
    missing, wrong, extra = 0, 0, 0
    for project in expected:
        e, f = expected[project], found[project]
        missing += len(e.keys() - f.keys())
        wrong += sum(e[k] != f[k] for k in e.keys() & f.keys())
        extra += len(f.keys() - e.keys())
    return {"missing": missing, "altered": wrong, "extra": extra}


def run_build(root: Path, force=False) -> dict:
    argv = ["node", str(compiler()), "-b", "tsconfig.json", "--verbose"]
    if force:
        argv.append("--force")
    start = time.perf_counter()
    c = subprocess.run(argv, cwd=root, capture_output=True, text=True, timeout=90)
    return {"argv": argv, "exit": c.returncode,
            "seconds": round(time.perf_counter() - start, 5),
            "stdout_tail": c.stdout[-3000:], "stderr_tail": c.stderr[-1500:]}


def clean_build_outputs(root: Path) -> None:
    for name in ("alpha", "beta"):
        package = root / "packages" / name
        dist = package / "dist"
        if dist.exists():
            if dist.is_symlink():
                raise ValueError("Refuse to purge a linked output")
            shutil.rmtree(dist)
        (package / "cache.tsbuildinfo").unlink(missing_ok=True)


def write_trusted_oracle(root: Path, path: Path) -> None:
    clean_build_outputs(root)
    build = run_build(root)
    if build["exit"]:
        raise RuntimeError(build["stderr_tail"] + build["stdout_tail"])
    expected = output_snapshot(root)
    if any(not v for v in expected.values()):
        raise RuntimeError("Missing cold-build emitted files")
    put_json(path, {"typescript": "5.9.3", "source_hash": input_digest(root),
                    "expected": expected, "cold_build": build,
                    "created_by": "isolated independent cold compile"})


def remove_js_from_alpha(root: Path) -> None:
    target = root / "packages" / "alpha" / "dist" / "index.js"
    if not target.is_file():
        raise RuntimeError(f"Expected generated JS missing: {target}")
    target.unlink()


def inject_fault(root: Path, fault: str) -> None:
    if fault == "none":
        return
    if fault == "delete_js":
        remove_js_from_alpha(root)
    elif fault == "corrupt_dts":
        p = root / "packages" / "alpha" / "dist" / "index.d.ts"
        p.write_bytes(p.read_bytes() + b"\n// n21 controlled corruption\n")
    elif fault == "extra_stale":
        p = root / "packages" / "alpha" / "dist" / "old-removed.js"
        p.write_bytes(b"// controlled obsolete output\n")
    else:
        raise ValueError(fault)


def selectively_repair(root: Path, expected: dict) -> tuple[list[str], int, dict]:
    found = output_snapshot(root)
    damaged = [name for name in expected if found[name] != expected[name]]
    # Scan volume records the I/O cost of hashing all emitted output files.
    scan_bytes = sum(p.stat().st_size for name in expected
                     for p in (root / "packages" / name / "dist").rglob("*")
                     if p.is_file() and p.suffix != ".tsbuildinfo")
    for name in damaged:
        package = root / "packages" / name
        (package / "cache.tsbuildinfo").unlink(missing_ok=True)
        dist = package / "dist"
        for p in dist.rglob("*"):
            if p.is_file() and p.relative_to(dist).as_posix() not in expected[name]:
                p.unlink()
    return damaged, scan_bytes, run_build(root)


def experiment(root: Path, oracle_path: Path, metrics_path: Path,
               strategy: str, fault: str, cache_state: str) -> dict:
    oracle = json.loads(oracle_path.read_text(encoding="utf-8"))
    if oracle["typescript"] != "5.9.3":
        raise RuntimeError("Compiler version mismatch")
    expected = oracle["expected"]
    inject_fault(root, fault)
    before = diff(expected, output_snapshot(root))
    cpu_before = resource.getrusage(resource.RUSAGE_CHILDREN)
    t0 = time.perf_counter()
    scan_bytes, damaged, rejected = 0, [], False
    if strategy == "attest_only":
        build = run_build(root)
    elif strategy == "guarded_sha":
        if oracle["source_hash"] != input_digest(root):
            rejected = True
            clean_build_outputs(root)
            build = run_build(root)
        else:
            damaged, scan_bytes, build = selectively_repair(root, expected)
    elif strategy == "clean_all":
        clean_build_outputs(root)
        build = run_build(root)
    elif strategy == "force_all":
        build = run_build(root, force=True)
    else:
        raise ValueError(strategy)
    work_seconds = time.perf_counter() - t0
    cpu_after = resource.getrusage(resource.RUSAGE_CHILDREN)
    after = diff(expected, output_snapshot(root))
    result = {"test_environment": "GitHub Actions runner only if GITHUB_ACTIONS=true",
              "observed_in_github_actions": os.environ.get("GITHUB_ACTIONS") == "true",
              "runner_name": os.environ.get("RUNNER_NAME"),
              "runner_os": os.environ.get("RUNNER_OS"),
              "github_run_id": os.environ.get("GITHUB_RUN_ID"),
              "cache_state": cache_state, "strategy": strategy, "fault": fault,
              "before": before, "after": after,
              "correct_against_trusted_oracle": build["exit"] == 0 and after == {
                  "missing": 0, "altered": 0, "extra": 0},
              "detected_projects": damaged, "input_rejected": rejected,
              "output_sha_scanned_bytes": scan_bytes,
              "work_seconds": round(work_seconds, 5),
              "build_child_cpu_user_seconds": round(cpu_after.ru_utime - cpu_before.ru_utime, 5),
              "build_child_cpu_system_seconds": round(cpu_after.ru_stime - cpu_before.ru_stime, 5),
              "build": build}
    put_json(metrics_path, result)
    print(json.dumps({k: result[k] for k in ("cache_state", "strategy", "fault",
                    "correct_against_trusted_oracle", "before", "after", "work_seconds")},
                    sort_keys=True))
    return result


def local_smoke(metrics_path: Path) -> None:
    rows = []
    with tempfile.TemporaryDirectory(prefix="n21_gha_smoke_") as d:
        root = Path(d) / "fixture"
        oracle = Path(d) / "expected.json"
        init_fixture(root)
        write_trusted_oracle(root, oracle)
        # Each verification starts from a separately copied, fully cached state.
        for fault in ("none", "delete_js", "corrupt_dts", "extra_stale"):
            for strategy in ("attest_only", "guarded_sha", "clean_all", "force_all"):
                trial = Path(d) / "trial"
                if trial.exists():
                    shutil.rmtree(trial)
                shutil.copytree(root, trial)
                result = experiment(trial, oracle, Path(d) / "smoke.json",
                                    strategy, fault, "local_complete_cache_copy")
                rows.append(result)
                if strategy in ("guarded_sha", "clean_all") and not result["correct_against_trusted_oracle"]:
                    raise AssertionError(f"Local smoke failed: {strategy}/{fault}")
                if strategy == "guarded_sha" and result["input_rejected"]:
                    raise AssertionError(f"Output damage misclassified as input drift: {fault}")
    put_json(metrics_path.resolve(), {"run_mode": "local script smoke, not GitHub Actions or Attest execution",
                                      "typescript": "5.9.3", "expected_rows": 16,
                                      "observations": rows})
    print("Local harness smoke completed: 16 cases (not GitHub Actions execution)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("task", choices=["init", "cold", "partial", "experiment", "smoke"])
    ap.add_argument("--root", type=Path, default=Path("n21_gha_fixture"))
    ap.add_argument("--oracle", type=Path, default=Path("n21_gha_evidence/expected.json"))
    ap.add_argument("--metrics", type=Path, default=Path("n21_gha_evidence/result.json"))
    ap.add_argument("--fault", default="none")
    ap.add_argument("--strategy", default="attest_only")
    ap.add_argument("--cache-state", default="complete")
    args = ap.parse_args()
    if args.task == "smoke":
        local_smoke(args.metrics)
        return
    root = root_path(args)
    if args.task == "init":
        init_fixture(root)
    elif args.task == "cold":
        write_trusted_oracle(root, args.oracle.resolve())
    elif args.task == "partial":
        remove_js_from_alpha(root)
    else:
        result = experiment(root, args.oracle.resolve(), args.metrics.resolve(),
                            args.strategy, args.fault, args.cache_state)
        # Keep a failed *correctness* observation in the archive; the GitHub
        # job should succeed if the harness itself ran and recorded the truth.
        if result["build"]["exit"]:
            print("Compiler exit was nonzero, preserved as an observation")


if __name__ == "__main__":
    main()
