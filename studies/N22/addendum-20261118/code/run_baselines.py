#!/usr/bin/env python3
"""Run unchanged upstream native suite and current migration-test helper."""

import argparse
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent


def run(args):
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    (root / "logs").mkdir()
    (root / "databases").mkdir()
    (root / "json").mkdir()
    records = []

    for rep in range(1, args.repetitions + 1):
        for name, python in (("django600", args.dj600), ("django601", args.dj601)):
            db = root / "databases" / f"{name}_helper_{rep}.sqlite"
            out = root / "json" / f"{name}_helper_{rep}.json"
            argv = [str(python), str(ROOT / "code" / "baseline_django_test_migrations.py"),
                    "--db", str(db), "--out", str(out)]
            env = dict(os.environ)
            env["PYTHONPATH"] = str(ROOT / "fixtures") + os.pathsep + env.get("PYTHONPATH", "")
            start = time.perf_counter()
            proc = subprocess.run(argv, cwd=WORKSPACE, env=env, capture_output=True, text=True)
            wall_ms = round(1000 * (time.perf_counter() - start), 3)
            (root / "logs" / f"{name}_helper_{rep}.log").write_text(
                f"$ {json.dumps(argv)}\nexit={proc.returncode}\n{proc.stdout}\n{proc.stderr}", encoding="utf-8")
            if proc.returncode or not out.exists():
                raise RuntimeError(f"Helper baseline {name}/{rep} failed")
            observed = json.loads(out.read_text(encoding="utf-8"))
            if observed["detected_violation"]:
                raise AssertionError("Migration helper unexpectedly detected an unfixed permission defect")
            records.append({"case": f"{name}_helper", "replication": rep,
                            "source": "django-test-migrations 1.7.0", "wall_milliseconds": wall_ms,
                            "detected_violation": observed["detected_violation"],
                            "oracle": observed["oracle"]})

        argv = [str(args.bun), "test", "test/v1-migration.test.ts", "--timeout", "30000"]
        start = time.perf_counter()
        proc = subprocess.run(argv, cwd=args.opencode / "packages/core", capture_output=True, text=True)
        wall_ms = round(1000 * (time.perf_counter() - start), 3)
        (root / "logs" / f"opencode_native_suite_{rep}.log").write_text(
            f"$ {json.dumps(argv)}\nexit={proc.returncode}\n{proc.stdout}\n{proc.stderr}", encoding="utf-8")
        if proc.returncode or "26 pass" not in (proc.stdout + proc.stderr):
            raise RuntimeError(f"Upstream OpenCode native suite did not report expected 26 passes, replication {rep}")
        records.append({"case": "opencode_native_v1_migration_suite", "replication": rep,
                        "source": "unchanged upstream suite, 26 tests", "wall_milliseconds": wall_ms,
                        "passed_tests": 26, "failed_tests": 0,
                        "legacy_agent_missing_case_in_shipped_tests": False})

    summary = {"created_utc": datetime.now(timezone.utc).isoformat(),
               "characterization": "The helper baseline mutes Django signals. It is not a fair complete contract baseline; see metrics.json for that strong baseline.",
               "replications": args.repetitions, "cases": records}
    (root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"baseline_runs": len(records), "out": str(root)}, indent=2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=ROOT / "runs/baselines")
    ap.add_argument("--dj600", type=Path, default=WORKSPACE / "n22_env_dj600/bin/python")
    ap.add_argument("--dj601", type=Path, default=WORKSPACE / "n22_env_dj601/bin/python")
    ap.add_argument("--bun", type=Path, default=WORKSPACE / "n22_tooling/node_modules/@oven/bun-linux-x64/bin/bun")
    ap.add_argument("--opencode", type=Path, default=WORKSPACE / "n22_upstream_opencode")
    ap.add_argument("--repetitions", type=int, default=3)
    options = ap.parse_args()
    run(options)
