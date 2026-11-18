#!/usr/bin/env python3
"""Audit actual GitHub-hosted Attest cache runs and produce descriptive results.

Faults are controlled injections, never naturally occurring industrial CI events.
Excludes the pilot with an invalid input fingerprint. No industrial ROI inferred.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
PILOT = "44237397496"
EXPECT = {
    ("complete", "none", "attest_only"): True,
    ("complete", "none", "guarded_sha"): True,
    ("partial", "none", "attest_only"): False,
    ("partial", "none", "guarded_sha"): True,
    ("partial", "none", "clean_all"): True,
    ("partial", "none", "force_all"): True,
    ("complete", "corrupt_dts", "attest_only"): False,
    ("complete", "corrupt_dts", "guarded_sha"): True,
    ("complete", "corrupt_dts", "clean_all"): True,
    ("complete", "extra_stale", "attest_only"): False,
    ("complete", "extra_stale", "guarded_sha"): True,
    ("complete", "extra_stale", "force_all"): False,
    ("miss", "none", "attest_only"): True,
    ("miss", "none", "guarded_sha"): True,
}


def data(path):
    return json.loads(path.read_text(encoding="utf-8"))


def assert_ok(ok, message):
    if not ok:
        raise AssertionError(message)


def step_seconds(step):
    start = datetime.fromisoformat(step["started_at"].replace("Z", "+00:00"))
    finish = datetime.fromisoformat(step["completed_at"].replace("Z", "+00:00"))
    return (finish - start).total_seconds()


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(folder):
    run_id = folder.name.removeprefix("github_actions_run_")
    run = data(folder / "run_api.json")
    jobs = data(folder / "jobs_api.json")["jobs"]
    artifact_metadata = data(folder / "artifacts_api.json")
    assert_ok(str(run["id"]) == run_id and run["status"] == "completed"
              and run["conclusion"] == "success", f"{run_id}: run not successful")
    assert_ok(len(jobs) == 15 and all(j["conclusion"] == "success" for j in jobs),
              f"{run_id}: expected 15 successful runner jobs")
    assert_ok(artifact_metadata["total_count"] == 15
              and len(list((folder / "artifacts").glob("*.zip"))) == 15
              and len(list((folder / "logs").glob("*.log"))) == 15,
              f"{run_id}: 15 raw ZIPs and 15 full logs must be archived")
    oracle = data(folder / "unpacked" / "n21-trusted-oracle" / "expected.json")
    assert_ok(oracle["typescript"] == "5.9.3" and oracle["cold_build"]["exit"] == 0,
              f"{run_id}: bad independent compiler reference")
    assert_ok(sum(map(len, oracle["expected"].values())) == 4,
              f"{run_id}: wrong number of expected emitted files")
    job_by_name = {j["name"]: j for j in jobs}
    assert_ok(len(job_by_name) == 15, f"{run_id}: repeated job name")
    warm = job_by_name["Generate trusted outputs and two caches"]
    warm_log = (folder / "logs" / f"{warm['id']}.log").read_text(encoding="utf-8-sig")
    for state in ("complete", "partial"):
        assert_ok(f"Cache saved with key: n21-{run_id}-{state}" in warm_log,
                  f"{run_id}: no real Attest cache save for {state}")
    records = []
    for key, expected_correct in sorted(EXPECT.items()):
        state, fault, strategy = key
        stem = f"n21-result-{state}-{fault}-{strategy}"
        artifact = folder / "unpacked" / stem / "result.json"
        zip_path = folder / "artifacts" / f"{stem}.zip"
        assert_ok(artifact.is_file() and zip_path.is_file(),
                  f"{run_id} {key}: missing artifact or original ZIP")
        row = data(artifact)
        assert_ok((row["cache_state"], row["fault"], row["strategy"]) == key
                  and row["observed_in_github_actions"] is True
                  and str(row["github_run_id"]) == run_id
                  and row["runner_os"] == "Linux"
                  and row["build"]["exit"] == 0,
                  f"{run_id} {key}: invalid measurement identity")
        assert_ok(row["input_rejected"] is False,
                  f"{run_id} {key}: false input-drift rejection (pilot problem)")
        assert_ok(row["correct_against_trusted_oracle"] is expected_correct
                  and (not any(row["after"].values())) is expected_correct,
                  f"{run_id} {key}: full output SHA truth mismatch")
        expected_before = {"missing": 0, "altered": 0, "extra": 0}
        if state == "partial":
            expected_before["missing"] = 1
        elif state == "miss":
            expected_before["missing"] = 4
        if fault == "corrupt_dts":
            expected_before["altered"] = 1
        elif fault == "extra_stale":
            expected_before["extra"] = 1
        assert_ok(row["before"] == expected_before,
                  f"{run_id} {key}: control or injection not observed")
        if strategy == "guarded_sha" and state != "miss":
            assert_ok(row["output_sha_scanned_bytes"] > 0,
                      f"{run_id} {key}: SHA scan unexpectedly absent")
        job = job_by_name[" / ".join(key)]
        assert_ok(job["runner_name"] == row["runner_name"],
                  f"{run_id} {key}: runner name mismatch")
        log_path = folder / "logs" / f"{job['id']}.log"
        log = log_path.read_text(encoding="utf-8-sig")
        assert_ok("Attest/typescript-cache-action@7227052c996c38afb0aece6e05d185b2d45a28a5" in log,
                  f"{run_id} {key}: actual Attest action not verified")
        if state == "miss":
            assert_ok("Cache not found for input keys:" in log,
                      f"{run_id} {key}: expected real miss")
        else:
            assert_ok(f"Cache restored from key: n21-{run_id}-{state}" in log,
                      f"{run_id} {key}: expected actual cache hit")
        size = re.search(r"Cache Size: ~\d+ MB \((\d+) B\)", log)
        if state != "miss":
            assert_ok(size is not None, f"{run_id} {key}: missing transfer byte size")
        internal = re.search(
            r"##\[end-action id=__Attest_typescript-cache-action\.tsc-build-cache;[^\n]*duration_ms=(\d+)\]", log)
        assert_ok(internal is not None, f"{run_id} {key}: missing cache restore timer")
        steps = {s["name"]: s for s in job["steps"]}
        restore = steps["Restore with actual Attest composite action"]
        execute = steps["Execute repair strategy and independent SHA oracle"]
        assert_ok(restore["conclusion"] == execute["conclusion"] == "success",
                  f"{run_id} {key}: job failed restore or measurement")
        records.append({
            "run_id": run_id, "head_sha": run["head_sha"], "cache_state": state,
            "fault": fault, "strategy": strategy, "correct": expected_correct,
            "job_id": job["id"], "job_url": job["html_url"],
            "runner_name": row["runner_name"], "work_seconds": row["work_seconds"],
            "cpu_child_user_seconds": row["build_child_cpu_user_seconds"],
            "cpu_child_system_seconds": row["build_child_cpu_system_seconds"],
            "scan_bytes": row["output_sha_scanned_bytes"],
            "rebuilt_projects": ",".join(row["detected_projects"]),
            "cache_hit": state != "miss",
            "cache_transfer_compressed_bytes": int(size.group(1)) if size else 0,
            "cache_internal_restore_seconds": int(internal.group(1)) / 1000,
            "composite_restore_step_seconds_coarse": step_seconds(restore),
            "strategy_step_seconds_coarse": step_seconds(execute),
            "job_seconds_coarse": step_seconds(job),
            "raw_log_sha256": sha256(log_path),
            "artifact_zip_sha256": sha256(zip_path),
        })
    assert_ok(len(records) == 14 and len({(r["cache_state"], r["fault"], r["strategy"])
                                        for r in records}) == 14, f"{run_id}: bad matrix")
    return {"run_id": run_id, "url": run["html_url"], "head_sha": run["head_sha"],
            "typescript": "5.9.3", "runner_image": "ubuntu-22.04",
            "fixture_source_hash": oracle["source_hash"],
            "cold_build_seconds": oracle["cold_build"]["seconds"],
            "sum_hosted_job_elapsed_seconds_coarse": round(sum(step_seconds(j) for j in jobs), 2),
            "warm_job_elapsed_seconds_coarse": step_seconds(warm),
            "job_count": 15, "test_count": 14,
            "correct_tests": sum(r["correct"] for r in records),
            "records": records}


def med(nums):
    return round(statistics.median(nums), 5)


def main():
    folders = sorted(p for p in RESULTS.glob("github_actions_run_*")
                     if p.is_dir() and p.name != f"github_actions_run_{PILOT}"
                     and (p / "run_api.json").exists())
    assert_ok(folders, "No corrected run archives available")
    audits = [audit(folder) for folder in folders]
    assert_ok(len({a["fixture_source_hash"] for a in audits}) == 1,
              "Runner repetitions differed in fixture inputs")
    rows = [r for a in audits for r in a["records"]]
    groups = defaultdict(list)
    for row in rows:
        groups[(row["cache_state"], row["fault"], row["strategy"])].append(row)
    summary = []
    for (state, fault, strategy), trial in sorted(groups.items()):
        assert_ok(len(trial) == len(audits), "Incomplete replicate series")
        work = [r["work_seconds"] for r in trial]
        summary.append({
            "cache_state": state, "fault": fault, "strategy": strategy,
            "n": len(trial), "correct": sum(r["correct"] for r in trial),
            "work_median_seconds": med(work), "work_min_seconds": min(work),
            "work_max_seconds": max(work),
            "cache_internal_restore_median_seconds": med([r["cache_internal_restore_seconds"] for r in trial]),
            "attest_composite_coarse_median_seconds": med([r["composite_restore_step_seconds_coarse"] for r in trial]),
            "cache_compressed_bytes_median": med([r["cache_transfer_compressed_bytes"] for r in trial]),
            "scan_bytes_median": med([r["scan_bytes"] for r in trial]),
            "cpu_child_user_median_seconds": med([r["cpu_child_user_seconds"] for r in trial]),
            "cpu_child_system_median_seconds": med([r["cpu_child_system_seconds"] for r in trial]),
        })
    ix = {(s["cache_state"], s["fault"], s["strategy"]): s for s in summary}
    overhead = (ix["complete", "none", "guarded_sha"]["work_median_seconds"]
                - ix["complete", "none", "attest_only"]["work_median_seconds"])
    partial_gain = (ix["partial", "none", "clean_all"]["work_median_seconds"]
                    - ix["partial", "none", "guarded_sha"]["work_median_seconds"])
    corrupt_gain = (ix["complete", "corrupt_dts", "clean_all"]["work_median_seconds"]
                    - ix["complete", "corrupt_dts", "guarded_sha"]["work_median_seconds"])
    def threshold(gain):
        return round(overhead / (overhead + gain), 5) if overhead >= 0 and gain > 0 else None
    out = {
        "classification": "GitHub-hosted real action, deliberately injected faults only",
        "repository": "shjdjjfi/FSE-EXP-1",
        "included_runs": [a["run_id"] for a in audits], "excluded_pilot_run": PILOT,
        "run_count": len(audits), "actual_runner_jobs": len(audits) * 15,
        "sum_hosted_job_elapsed_seconds_coarse": round(
            sum(a["sum_hosted_job_elapsed_seconds_coarse"] for a in audits), 2),
        "verified_strategy_records": len(rows),
        "correct_cases": sum(r["correct"] for r in rows),
        "natural_ci_incidents_with_full_logs": 0,
        "valid_n21_incidence_denominator": None, "industrial_roi_measured": False,
        "actual_cache_transfer_byte_sizes": sorted({r["cache_transfer_compressed_bytes"] for r in rows}),
        "fixture_only_cost_sensitivity": {
            "intact_guard_overhead_median_seconds": round(overhead, 5),
            "partial_guard_saving_vs_clean_median_seconds": round(partial_gain, 5),
            "corrupt_guard_saving_vs_clean_median_seconds": round(corrupt_gain, 5),
            "conditional_partial_break_even_fraction": threshold(partial_gain),
            "conditional_corrupt_break_even_fraction": threshold(corrupt_gain),
            "warning": "Sensitivity algebra only: compares guarded repair against an idealized baseline with free knowledge of which runs are intact (attest_only) versus damaged (clean_all). Such perfect damage awareness is not implementable at zero cost. NOT production ROI or incidence"},
        "runs": [{k: v for k, v in a.items() if k != "records"} for a in audits],
        "summary": summary, "rows": rows,
    }
    (RESULTS / "github_actions_aggregate.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with (RESULTS / "github_actions_aggregate.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    lines = [
        "# N21: verified GitHub-hosted Attest/typescript-cache-action results",
        "",
        f"Corrected runs: {len(audits)}; actual Ubuntu-22.04 hosted jobs: {len(audits)*15}; "
        f"individual measurements: {len(rows)}.",
        "**All faults deliberately injected; none is a natural production CI incident. "
        "No valid incidence denominator or industrial ROI.**",
        "",
        "## Direct raw-run links",
        "",
    ]
    for run in audits:
        lines.append(f"- [Run {run['run_id']}]({run['url']}) — commit "
                     f"{run['head_sha']}; 15/15 jobs; 14/14 case artifacts; "
                     f"sum of job elapsed times {run['sum_hosted_job_elapsed_seconds_coarse']:.0f} s (coarse).")
    lines += [
        "",
        f"Pilot [run {PILOT}](https://github.com/shjdjjfi/FSE-EXP-1/actions/runs/{PILOT}) "
        "excluded from timing: generated declarations erroneously entered the input fingerprint.",
        "",
        "## Runner observations (median and range, not statistically generalizable)",
        "",
        "| Cache | Fault | Strategy | SHA correct | Strategy wall s median [min,max] | "
        "Internal cache restore s | Compressed cache B | SHA scan B |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for s in summary:
        lines.append(
            f"| {s['cache_state']} | {s['fault']} | {s['strategy']} | {s['correct']}/{s['n']} | "
            f"{s['work_median_seconds']:.3f} [{s['work_min_seconds']:.3f},"
            f"{s['work_max_seconds']:.3f}] | {s['cache_internal_restore_median_seconds']:.3f} | "
            f"{s['cache_compressed_bytes_median']:.0f} | {s['scan_bytes_median']:.0f} |")
    lines += [
        "", "Strategy wall time includes detection/hash/repair; excludes checkout, npm install "
        "and Attest restoration. Internal cache restore timer comes from raw job logs "
        "(millisecond precision). GitHub REST composite duration is seconds precision. "
        "Separate strategies run on different ephemeral runners, not the same machine.",
        "",
        "## Bounded engineering-economics calculation (not production ROI)", "",
        f"Intact-hit guard extra work median: {overhead:+.3f} seconds. "
        f"Against clean_all, guard saves {partial_gain:+.3f} seconds for artificial partial "
        f"and {corrupt_gain:+.3f} seconds for artificial corrupted declaration.",
        f"Toy two-state break-even input fault proportions (assuming stable costs, "
        f"only one damaged state and an idealized baseline that somehow knows "
        f"which runs need clean_all at zero detection cost): partial={threshold(partial_gain)}, "
        f"corrupt={threshold(corrupt_gain)}. These are modeled thresholds, "
        "NOT measured event rates, deployment financial ROI or engineering effort.",
        "", "## Reproducibility", "",
        "Each included results/github_actions_run_<id> folder contains REST run/jobs/artifact "
        "metadata, all 15 original ZIPs, all 15 complete logs and 15 JSON payloads. "
        "Per-job evidence hashes, actual transfer bytes, cache action timer, CPU and "
        "strategy timing are included in github_actions_aggregate.json and CSV. "
        "Total runner-job elapsed seconds summed across parallel jobs: "
        f"{out['sum_hosted_job_elapsed_seconds_coarse']:.0f} s, a usage proxy "
        "NOT GitHub billed time or a dollar charge. Release ZIP contains SHA-256 manifest.",
        "",
    ]
    (RESULTS / "github_actions_aggregate.md").write_text(
        "\n".join(lines), encoding="utf-8")
    latex = [
        r"\begin{table}[t]", r"\centering", r"\footnotesize",
        r"\begin{tabular}{lllrrr}", r"\toprule",
        r"Cache & Fault & Strategy & Exact & Work (s) & Cache (s) \\",
        r"\midrule",
    ]
    for s in summary:
        state, fault, strategy = [s[k].replace("_", r"\_") for k in
                                  ("cache_state", "fault", "strategy")]
        latex.append(
            f"{state} & {fault} & {strategy} & {s['correct']}/{s['n']} & "
            f"{s['work_median_seconds']:.3f} & "
            f"{s['cache_internal_restore_median_seconds']:.3f}" + r" \\")
    latex += [
        r"\bottomrule", r"\end{tabular}",
        r"\caption{Actual GitHub-hosted Attest cache restoration: medians "
        r"over three independently provisioned runs per controlled case. "
        r"The exactness oracle checks all emitted paths and SHA-256 values. "
        r"Faults are injected, not naturally observed; no industry incidence "
        r"or deployment ROI is inferred. Work excludes cache restoration.}",
        r"\label{tab:n21-gha-attest}", r"\end{table}", "",
    ]
    (RESULTS / "GHA_TABLE.tex").write_text("\n".join(latex), encoding="utf-8")
    print(json.dumps({
        "included_runs": out["included_runs"], "jobs": out["actual_runner_jobs"],
        "cases": out["verified_strategy_records"], "correct": out["correct_cases"],
        "cache_transfer_bytes": out["actual_cache_transfer_byte_sizes"],
        "fixture_cost_model": out["fixture_only_cost_sensitivity"],
    }, indent=2))


if __name__ == "__main__":
    main()
