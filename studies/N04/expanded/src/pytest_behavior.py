"""Executable pytest cache identity interventions, isolated per scenario.

Run using pinned pytest 8.4.2, optionally a newer version:
  uv run --no-project --with pytest==8.4.2 python src/pytest_behavior.py
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest
from pytest_cache_bridge import rewrite_cache


PRE = {
    "function_rename": "def test_stable():\n    assert True\n\ndef test_old():\n    assert False\n\ndef test_other():\n    assert True\n",
    "file_move": "def test_stable():\n    assert True\n\ndef test_old():\n    assert False\n\ndef test_other():\n    assert True\n",
    "parameter_ids": "import pytest\n\n@pytest.mark.parametrize('value', [0, 1], ids=['alpha','beta'])\ndef test_parameter(value):\n    assert value > 0\n\ndef test_unrelated():\n    assert True\n",
    "semantic_change": "def test_stable():\n    assert True\n\ndef test_old():\n    assert False\n\ndef test_other():\n    assert True\n",
    "split": "def test_stable():\n    assert True\n\ndef test_old():\n    assert False\n\ndef test_other():\n    assert True\n",
}
POST = {
    "function_rename": "def test_stable():\n    assert True\n\ndef test_new():\n    assert False\n\ndef test_other():\n    assert True\n",
    "file_move": PRE["file_move"],
    "parameter_ids": "import pytest\n\n@pytest.mark.parametrize('value', [0, 1], ids=['one','two'])\ndef test_parameter(value):\n    assert value > 0\n\ndef test_unrelated():\n    assert True\n",
    "semantic_change": "def test_stable():\n    assert True\n\ndef test_old():\n    assert True  # same identity; behavior now different\n\ndef test_other():\n    assert True\n",
    "split": "def test_stable():\n    assert True\n\ndef test_old_part_a():\n    assert False\n\ndef test_old_part_b():\n    assert True\n\ndef test_other():\n    assert True\n",
}


def call_pytest(cwd: Path, *args: str) -> dict:
    start = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:faulthandler", "-q", "--tb=no", *args],
        cwd=cwd, capture_output=True, text=True, timeout=65,
        env={"PATH": __import__("os").environ.get("PATH", ""), "PYTHONDONTWRITEBYTECODE":"1"},
    )
    combined = proc.stdout + "\n" + proc.stderr
    counts = re.findall(r"(\d+) tests? collected", combined)
    if not counts:
        counts = re.findall(r"collected (\d+) items?", combined)
    collected = int(counts[-1]) if counts else (0 if "no tests collected" in combined else None)
    return {"command": ["python", "-m", "pytest", "-q", "--tb=no", *args],
            "exit_code": proc.returncode, "stdout": proc.stdout,
            "stderr": proc.stderr,"collected_count":collected,
            "elapsed_seconds":time.perf_counter()-start}


def exercise(scenario: str) -> dict:
    with tempfile.TemporaryDirectory(prefix=f"n04-{scenario}-") as dirname:
        root = Path(dirname)
        old_file = root / "test_original.py"
        old_file.write_text(PRE[scenario], encoding="utf-8")
        first = call_pytest(root)
        unchanged = call_pytest(root, "--lf", "--lfnf", "none", "--collect-only")
        if scenario == "file_move":
            new_file = root / "test_moved.py"
            old_file.rename(new_file)
        else:
            new_file = old_file
        new_file.write_text(POST[scenario], encoding="utf-8")
        updated = call_pytest(root, "--lf", "--lfnf", "none", "--collect-only")
        bridge_audit = rewrite_cache(root, "test_original.py", new_file.name,
                                     PRE[scenario], POST[scenario])
        bridged = call_pytest(root, "--lf", "--lfnf", "none", "--collect-only")
        empty = call_pytest(root, "--lf", "--lfnf", "none", "--collect-only",
                            "-o", "cache_dir=empty-cache")
        return {"scenario": scenario, "pytest_version": pytest.__version__,
                "first_run": first, "same_identity_selection": unchanged,
                "after_edit_selection": updated, "bridge_audit":bridge_audit,
                "after_bridge_selection":bridged, "empty_cache_control": empty,
                "expectation":"Controlled mechanism check only; failure not stochastic"}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=Path("results/pytest_behavior"))
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    scenarios = [exercise(s) for s in PRE]
    result = {"pytest_version":pytest.__version__,"python":sys.version,
              "result_type":"real pytest executions of controlled fixtures",
              "scenarios": scenarios}
    dest = args.out / ("pytest_" + pytest.__version__ + ".json")
    dest.write_text(json.dumps(result,indent=2),encoding="utf-8")
    for r in scenarios:
        print(f"{r['scenario']}: previous={r['same_identity_selection']['collected_count']}, "
              f"changed={r['after_edit_selection']['collected_count']}, "
              f"bridged={r['after_bridge_selection']['collected_count']}, "
              f"empty={r['empty_cache_control']['collected_count']}")
    print("Saved", dest)


if __name__ == "__main__":
    main()
