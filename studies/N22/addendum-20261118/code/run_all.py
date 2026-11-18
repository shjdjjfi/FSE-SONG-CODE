#!/usr/bin/env python3
"""Re-run independent upstream engines and record immutable raw observations.

Use isolated, installed Python interpreters; install dependencies separately.
No engine, migration, or database source is patched by this orchestrator.
"""

import argparse
import concurrent.futures
import hashlib
import json
import os
import platform
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
WORKSPACE = PROJECT.parent
PREFIX = "N22_CASE_JSON "


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command_text(argv, cwd=None, env=None):
    p = subprocess.run(argv, cwd=cwd, env=env, text=True, capture_output=True, check=True)
    return p.stdout.strip()


def one_django(task, output_root, executable, script, mode, family, domain=None, name=None):
    case_id, repetition = task
    unique = f"{case_id}__r{repetition:02d}"
    db = output_root / "databases" / f"{unique}.sqlite"
    out = output_root / "raw_json" / f"{unique}.json"
    log = output_root / "logs" / f"{unique}.log"
    argv = [str(executable), str(PROJECT / "code" / script),
            "--db", str(db), "--out", str(out), "--mode", mode]
    if domain is not None:
        argv.extend(["--domain", domain, "--name", name])
    env = dict(os.environ)
    env["PYTHONPATH"] = str(PROJECT / "fixtures") + os.pathsep + env.get("PYTHONPATH", "")
    start = time.perf_counter()
    process = subprocess.run(argv, cwd=WORKSPACE, env=env, text=True, capture_output=True)
    duration = (time.perf_counter() - start) * 1000
    log.write_text("COMMAND: " + json.dumps(argv) + "\nRETURN CODE: " + str(process.returncode) +
                   "\nSTDOUT:\n" + process.stdout + "\nSTDERR:\n" + process.stderr, encoding="utf-8")
    if process.returncode or not out.exists():
        raise RuntimeError(f"{case_id} #{repetition} failed; see {log}")
    evidence = json.loads(out.read_text(encoding="utf-8"))
    if evidence["business_oracle"]["contract_violation"] not in (True, False):
        raise AssertionError(f"No independent oracle for {case_id}")
    return {"case_id": case_id, "replication": repetition, "family": family,
            "wall_milliseconds": round(duration, 3), "evidence": evidence,
            "raw_path": out.relative_to(output_root).as_posix(),
            "database_path": db.relative_to(output_root).as_posix(),
            "database_sha256": sha256(db)}


def one_opencode(repetition, output_root, bun, upstream):
    cwd = upstream / "packages" / "core"
    original_harness = cwd / "test" / "n22_contract_replay.test.ts"
    supplied_harness = PROJECT / "code" / "opencode_replay.test.ts"
    if not original_harness.exists() or sha256(supplied_harness) != sha256(original_harness):
        raise RuntimeError("Expected N22 harness is absent or changed in the isolated OpenCode clone; "
                           "copy code/opencode_replay.test.ts to packages/core/test/n22_contract_replay.test.ts")
    command = [str(bun), "test", "test/n22_contract_replay.test.ts", "--timeout", "30000"]
    start = time.perf_counter()
    process = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    duration = (time.perf_counter() - start) * 1000
    log = output_root / "logs" / f"opencode__r{repetition:02d}.log"
    log.write_text("COMMAND: " + json.dumps(command) + "\nRETURN CODE: " + str(process.returncode) +
                   "\nSTDOUT:\n" + process.stdout + "\nSTDERR:\n" + process.stderr, encoding="utf-8")
    if process.returncode:
        raise RuntimeError(f"OpenCode native test failed; see {log}")
    captured = []
    for line in (process.stdout + "\n" + process.stderr).splitlines():
        marker = line.find(PREFIX)
        if marker >= 0:
            data = json.loads(line[marker + len(PREFIX):])
            captured.append(data)
    if len(captured) != 5 or len({x["case_id"] for x in captured}) != 5:
        raise AssertionError(f"OpenCode emitted {len(captured)} distinct observations, expected 5")
    return [{"case_id": "opencode_" + item["case_id"], "replication": repetition,
             "family": "opencode", "wall_milliseconds": round(duration / 5, 3),
             "evidence": item, "raw_path": log.relative_to(output_root).as_posix()}
            for item in captured]


def run(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    for part in ("databases", "raw_json", "logs"):
        (output / part).mkdir()
    version = {}
    for label, exe in (("django600", args.dj600), ("django601", args.dj601), ("sites", args.dj518)):
        version[label] = command_text([str(exe), "-c", "import django; print(django.get_version())"])
    if version != {"django600": "6.0", "django601": "6.0.1", "sites": "5.1.8"}:
        raise RuntimeError(f"Pinned Django environments required; got {version}")
    bun_version = command_text([str(args.bun), "--version"])
    upstream_commit = command_text(["git", "rev-parse", "HEAD"], cwd=args.opencode)
    if upstream_commit != "1fd016ef32286de9489b7b24f1029f52c49a27b3":
        raise RuntimeError(f"OpenCode source not at pinned commit: {upstream_commit}")
    candidates = [
        ("django600_fresh", args.dj600, "replay_django.py", "fresh", "django_permissions", None, None),
        ("django600_staged", args.dj600, "replay_django.py", "staged", "django_permissions", None, None),
        ("django600_staged_ungrouped", args.dj600, "replay_django.py", "staged_ungrouped", "django_permissions", None, None),
        ("django601_fresh", args.dj601, "replay_django.py", "fresh", "django_permissions", None, None),
        ("django601_staged", args.dj601, "replay_django.py", "staged", "django_permissions", None, None),
        ("django601_staged_ungrouped", args.dj601, "replay_django.py", "staged_ungrouped", "django_permissions", None, None),
        ("sites_fresh", args.dj518, "replay_django_sites.py", "fresh", "django_sites", None, None),
        ("sites_staged", args.dj518, "replay_django_sites.py", "staged", "django_sites", None, None),
        ("sites_staged_user", args.dj518, "replay_django_sites.py", "staged_user", "django_sites", None, None),
        ("sites_staged_redirect", args.dj518, "replay_django_sites.py", "staged_redirect", "django_sites", None, None),
        ("sites_staged_noop", args.dj518, "replay_django_sites.py", "staged_noop", "django_sites", None, None),
    ]
    # All variations are legitimate, user-owned content changes, NOT independent bugs.
    for n in range(args.user_variants):
        prefix = f"sites_user_variant_{n+1:03d}"
        candidates.append((prefix, args.dj518, "replay_django_sites.py", "staged_user", "django_sites",
                           f"customer-{n+1:03d}.example", f"Owner's site setting {n+1}: 北京・München"))

    tasks = [(case_id, rep, exe, script, mode, family, domain, name)
             for case_id, exe, script, mode, family, domain, name in candidates
             for rep in range(1, args.repetitions + 1)]
    started = time.perf_counter()
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = [pool.submit(one_django, (case_id, rep), output, exe, script, mode, family, domain, name)
                   for case_id, rep, exe, script, mode, family, domain, name in tasks]
        for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
            results.append(future.result())
            if i % 20 == 0:
                print(f"Completed {i}/{len(tasks)} independent Django processes", flush=True)
    for rep in range(1, args.repetitions + 1):
        results.extend(one_opencode(rep, output, args.bun, args.opencode))

    results.sort(key=lambda r: (r["case_id"], r["replication"]))
    with (output / "observations.jsonl").open("w", encoding="utf-8") as fh:
        for result in results:
            fh.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
    provenance = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "retrospective exploratory research, not blind preregistered validation",
        "python": platform.python_version(), "platform": platform.platform(),
        "django_versions": version, "bun_version": bun_version,
        "opencode_commit": upstream_commit, "opencode_test_sha256": sha256(PROJECT / "code" / "opencode_replay.test.ts"),
        "repetitions": args.repetitions, "user_variants": args.user_variants,
        "jobs": args.jobs, "unique_cases": len(candidates) + 5,
        "total_processes": len(tasks) + args.repetitions, "total_observations": len(results),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "data_design": "Each Django case uses a new SQLite database; each OpenCode scenario uses a new in-memory database.",
        "result_sha256": sha256(output / "observations.jsonl"),
    }
    (output / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(provenance, indent=2), flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, default=PROJECT / "runs" / "full")
    p.add_argument("--dj600", type=Path, default=WORKSPACE / "n22_env_dj600" / "bin/python")
    p.add_argument("--dj601", type=Path, default=WORKSPACE / "n22_env_dj601" / "bin/python")
    p.add_argument("--dj518", type=Path, default=WORKSPACE / "n22_env_dj518" / "bin/python")
    p.add_argument("--bun", type=Path, default=WORKSPACE / "n22_tooling/node_modules/@oven/bun-linux-x64/bin/bun")
    p.add_argument("--opencode", type=Path, default=WORKSPACE / "n22_upstream_opencode")
    p.add_argument("--repetitions", type=int, default=3)
    p.add_argument("--user-variants", type=int, default=30)
    p.add_argument("--jobs", type=int, default=6)
    args = p.parse_args()
    if args.repetitions < 1 or args.user_variants < 0 or not 1 <= args.jobs <= 16:
        p.error("Use repetitions >= 1, user variants >= 0, jobs 1..16")
    run(args)
