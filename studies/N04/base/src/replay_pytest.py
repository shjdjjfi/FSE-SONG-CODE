"""End-to-end pytest 8.4.2 lastfailed-cache mechanism experiment.

This is a *controlled fixture*, never represented as observational CI data.
Each variant is executed with the real pytest binary and an isolated cache.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time


def run_pytest(cwd: Path, cache: Path, collect=False):
    cmd = [sys.executable, "-m", "pytest", "-q", "--tb=no", "-o",
           f"cache_dir={cache}"]
    if collect:
        cmd += ["--lf", "--lfnf", "none", "--collect-only"]
    else:
        cmd += ["test_cases.py"]
    started = time.perf_counter()
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=60)
    stdout = result.stdout + result.stderr
    nodes = [line.strip() for line in stdout.splitlines()
             if "::test_" in line and not line.strip().startswith("<")]
    return {"command": cmd, "returncode": result.returncode,
            "duration_ms": round((time.perf_counter()-started)*1000, 2),
            "selected_nodes": nodes, "selected_count": len(nodes),
            "output": stdout[-1700:]}


def modify_cache(cache: Path, old_name: str, new_name: str):
    p = cache / "v" / "cache" / "lastfailed"
    data = json.loads(p.read_text())
    matches = [x for x in data if x.endswith("::" + old_name)]
    if len(matches) != 1:
        raise AssertionError(f"Expected 1 old node, got {matches}")
    old = matches[0]
    data[old.replace("::"+old_name, "::"+new_name)] = data.pop(old)
    p.write_text(json.dumps(data, sort_keys=True))
    return old


def execute(seed: int):
    with tempfile.TemporaryDirectory(prefix="n04-pytest-") as dirname:
        root = Path(dirname)
        old_name = f"test_original_failure_{seed}"
        new_name = f"test_renamed_failure_{seed}"
        before = (f"def test_unrelated_pass_1(): assert True\n"
                  f"def {old_name}(): assert False\n"
                  f"def test_unrelated_pass_2(): assert 1 == 1\n")
        after = before.replace(old_name, new_name)
        file = root / "test_cases.py"
        cache = root / "cache"
        file.write_text(before)
        baseline = run_pytest(root, cache)
        if baseline["returncode"] != 1:
            raise AssertionError(f"Old fixture did not yield a failure: {baseline}")
        old_cache_collect = run_pytest(root, cache, collect=True)
        file.write_text(after)
        stale_collect = run_pytest(root, cache, collect=True)
        cache_path = cache / "v" / "cache" / "lastfailed"
        stale_cache = json.loads(cache_path.read_text())
        entry = modify_cache(cache, old_name, new_name)
        repaired_collect = run_pytest(root, cache, collect=True)
        # An explicit assertion change must block automatic history transfer.
        altered = after.replace(f"def {new_name}(): assert False", f"def {new_name}(): assert True")
        changed_body = "assert False" not in altered and "assert True" in altered
        src_has_equal_body = hashlib.sha256(before.split(f"def {old_name}(): ")[1].splitlines()[0].encode()).digest() == hashlib.sha256(after.split(f"def {new_name}(): ")[1].splitlines()[0].encode()).digest()
        file.write_text(altered)
        changed_name_body = hashlib.sha256(after.split(f"def {new_name}(): ")[1].splitlines()[0].encode()).digest() == hashlib.sha256(altered.split(f"def {new_name}(): ")[1].splitlines()[0].encode()).digest()
        return {"seed":seed, "old_id":entry,
                "baseline_run": baseline, "baseline_same_id": old_cache_collect,
                "stale_renamed": stale_collect, "identity_migrated": repaired_collect,
                "cached_prior_failures": len(stale_cache),
                "body_equal_after_rename": src_has_equal_body,
                "body_equal_after_semantic_change": changed_name_body,
                "semantic_change_confirmed": changed_body}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--seeds", nargs="+", type=int, default=[17,29,43])
    args = p.parse_args()
    experiments = [execute(seed) for seed in args.seeds]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"type":"controlled_pytest_mechanism",
        "pytest_version": subprocess.run([sys.executable,"-m","pytest","--version"],
        capture_output=True,text=True).stdout.strip(),
        "experiments": experiments},indent=2), encoding="utf-8")
    for record in experiments:
        print("seed",record["seed"],"same",record["baseline_same_id"]["selected_count"],
              "stale",record["stale_renamed"]["selected_count"],
              "migrated",record["identity_migrated"]["selected_count"])


if __name__ == "__main__":
    main()
