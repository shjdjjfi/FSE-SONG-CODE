#!/usr/bin/env python3
"""Blind-to-researcher deterministic summary of raw multi-run N24 results."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def wilson(x: int, n: int, z: float = 1.959963984540054) -> list:
    if not n:
        return [None, None]
    p, zz = x / n, z * z
    d = 1 + zz / n
    midpoint = (p + zz / (2 * n)) / d
    radius = z * math.sqrt((p * (1 - p) + zz / (4 * n)) / n) / d
    return [round(max(0, midpoint - radius), 4), round(min(1, midpoint + radius), 4)]


def summarize(paths: list[Path]) -> dict:
    observations = []
    environments = []
    warnings = []
    seen = set()
    for path in paths:
        p = path / "runs.json" if path.is_dir() else path
        if not p.is_file():
            warnings.append(f"Missing run file: {p}")
            continue
        data = json.loads(p.read_text(encoding="utf-8"))
        host = data.get("host", {})
        key = (data.get("github_run_id"), host.get("os"), host.get("cpu"), str(p))
        if key in seen:
            warnings.append(f"Duplicate input ignored: {p}")
            continue
        seen.add(key)
        environments.append({"source": str(p), "host": host,
                             "run": data.get("github_run_id"),
                             "commit": data.get("github_sha"),
                             "families": data.get("families"), "errors": data.get("errors", [])})
        observations.extend({**r, "host": host, "source": str(p)} for r in data.get("results", []))
        if data.get("errors"):
            warnings.append(f"Runtime errors in {p}: {len(data['errors'])}")
    groups = {}
    for r in observations:
        k = (r["condition"], r["strategy"])
        groups.setdefault(k, []).append(r)
    rates = {}
    for (condition, strategy), records in sorted(groups.items()):
        n = len(records)
        valid = [r for r in records if r.get("reference_usable")]
        correct = sum(r["repaired_runtime_ok"] for r in valid)
        ci_success = sum(r["npm_ci"]["returncode"] == 0 for r in valid)
        version_churn = [r["comparison"]["changed_non_target_versions"] for r in records if r.get("comparison")]
        missing_host = sum(len(r["platform_coverage"]["host_missing"]) for r in records if r.get("platform_coverage"))
        rates[f"{condition}/{strategy}"] = {
            "n": n, "reference_usable_n": len(valid),
            "npm_ci_ok_n": ci_success,
            "native_execution_success_n": correct,
            "native_execution_success_fraction": round(correct / len(valid), 4) if valid else None,
            "wilson_95_ci": wilson(correct, len(valid)),
            "missing_host_platform_entries_total": missing_host,
            "non_target_changed_versions_total": sum(version_churn),
            "non_target_changed_versions_mean": round(sum(version_churn) / len(version_churn), 4) if version_churn else None,
            "median_treatment_seconds": sorted(r["treatment"]["seconds"] for r in records)[n // 2] if n else None,
        }
    paired = []
    index = {}
    for r in observations:
        key = (r["source"], r["family"], r["condition"])
        index.setdefault(key, {})[r["strategy"]] = r
    for (source, family, condition), treatments in sorted(index.items()):
        base = treatments.get("unmodified")
        for strategy, outcome in sorted(treatments.items()):
            if strategy == "unmodified" or not base:
                continue
            paired.append({"family": family, "condition": condition, "source": source,
                           "strategy": strategy,
                           "native_success_delta": int(outcome["repaired_runtime_ok"]) - int(base["repaired_runtime_ok"]),
                           "churn_delta": (outcome["comparison"]["changed_non_target_versions"] -
                                           base["comparison"]["changed_non_target_versions"])
                           if outcome.get("comparison") and base.get("comparison") else None})
    return {"observational_unit": "package family x observed host x fault, paired across strategies",
            "source": "Real published npm packages; npm10 regenerated locks under node_modules (controlled, not historical incidents)",
            "platforms": environments, "n_source_files": len(environments),
            "n_observations": len(observations), "groups": rates,
            "paired_strategies_vs_unmodified": paired,
            "warnings": warnings,
            "caveats": ["Wilson CIs treat package-host cells as independent; package families share npm implementation, so uncertainty may be understated",
                        "An npm ci exit 0 with native execution failure is not a successful installation",
                        "This dataset alone cannot establish naturally occurring CI incidence, dollar savings, or industrial adoption",
                        "Refusal for non-leaf and corrupted existing entries is a method boundary, not successful repair"]}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("inputs", nargs="+", type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    data = summarize(args.inputs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"observations": data["n_observations"], "groups": data["groups"],
                      "warnings": data["warnings"]}, indent=2))


if __name__ == "__main__":
    main()
