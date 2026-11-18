#!/usr/bin/env python3
"""Verify archived SQLite, JSON, per-case repeats and provenance hashes."""

import argparse
import collections
import hashlib
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def child(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"Path escaped artifact root: {relative}")
    return path


def run(raw_root, baseline_root, report):
    provenance = json.loads((raw_root / "provenance.json").read_text(encoding="utf-8"))
    raw_data = raw_root / "observations.jsonl"
    assert sha(raw_data) == provenance["result_sha256"]
    obs = [json.loads(line) for line in raw_data.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(obs) == provenance["total_observations"] == 138
    groups = collections.defaultdict(list)
    checked_dbs = 0
    checked_json = 0
    for item in obs:
        groups[item["case_id"]].append(item)
        if item["family"] == "opencode":
            assert child(raw_root, item["raw_path"]).is_file()
            assert item["evidence"]["checkpoint"] == '{"phase":"completed"}'
            continue
        db = child(raw_root, item["database_path"])
        original = child(raw_root, item["raw_path"])
        assert db.exists() and original.exists()
        assert sha(db) == item["database_sha256"]
        with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as conn:
            assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert json.loads(original.read_text(encoding="utf-8")) == item["evidence"]
        checked_dbs += 1
        checked_json += 1
    assert len(groups) == provenance["unique_cases"] == 46
    assert all(len(items) == provenance["repetitions"] == 3 and
               {x["replication"] for x in items} == {1, 2, 3} for items in groups.values())
    baseline = json.loads((baseline_root / "summary.json").read_text(encoding="utf-8"))
    assert len(baseline["cases"]) == 9
    assert sum(x.get("passed_tests", 0) for x in baseline["cases"]) == 78
    assert sum(x["source"].startswith("django-test-migrations") for x in baseline["cases"]) == 6
    metrics = json.loads((ROOT / "reports/metrics.json").read_text(encoding="utf-8"))
    assert metrics["primary_positive_cases"] == 2 and metrics["primary_negative_cases"] == 13
    assert metrics["original_hypothesis_gate"]["gate_passed"] is False
    audit = {"status": "passed", "dataset_sha256": sha(raw_data),
             "verified_sqlite_database_count": checked_dbs,
             "verified_raw_json_count": checked_json,
             "unique_case_inputs": len(groups), "observations": len(obs),
             "verified_upstream_baseline_tests": 78,
             "verified_helper_baseline_runs": 6,
             "original_scientific_stopping_rule_passed": False}
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=Path, default=ROOT / "runs/full")
    ap.add_argument("--baselines", type=Path, default=ROOT / "runs/baselines_complete")
    ap.add_argument("--output", type=Path, default=ROOT / "reports/verification.json")
    args = ap.parse_args()
    run(args.raw.resolve(), args.baselines.resolve(), args.output.resolve())
