#!/usr/bin/env python3
"""Offline regression/integrity check for the frozen N02 experiment bundle."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT=Path(__file__).resolve().parent.parent
RESULTS=ROOT/"results"


def load(name: str):
    return json.loads((RESULTS/name).read_text())


def main() -> None:
    rows=[json.loads(x) for x in (RESULTS/"case_results.jsonl").read_text().splitlines()]
    assert len(rows)==27
    positives=[r for r in rows if r["label"]=="positive"]
    negatives=[r for r in rows if r["label"]=="negative"]
    assert len(positives)==8 and len(negatives)==19
    assert len({r["family"] for r in rows})==5
    assert all(r["contract"] and
               r["contract"]["old_ok"] and
               not r["contract"]["reset_then_reuse_ok"] and
               r["contract"]["migrated_ok"] for r in positives)
    assert all(r["render"]["old"]["ok"] and
               r["render"]["reset_then_reuse"]["ok"] and
               r["render"]["migrated"]["ok"] for r in rows)
    assert all(r["score_counterfactual"]>=5 for r in positives)
    assert all(r["score_counterfactual"]<5 for r in negatives)
    assert sum(bool(r["documented_actionable_migration"]) for r in positives)==7

    source=load("toolchain_and_sources.json")
    assert len(source["chart_artifacts"])==10
    for record in source["chart_artifacts"].values():
        chart=ROOT/"charts"/record["filename"]
        assert chart.is_file()
        assert hashlib.sha256(chart.read_bytes()).hexdigest()==record["sha256"]

    summary=load("analysis_summary.json")
    assert summary["cases"]==27 and summary["positives"]==8 and summary["negatives"]==19
    byname={x["method"]:x for x in summary["threshold_scores"]}
    assert (byname["counterfactual"]["tp"],byname["counterfactual"]["fp"])==(8,0)
    assert (byname["missing_new_default"]["tp"],byname["missing_new_default"]["fp"])==(8,3)
    assert (byname["migration_docs"]["tp"],byname["migration_docs"]["fp"])==(7,0)
    with (RESULTS/"rankings_seeded.csv").open(newline="") as stream:
        saved=list(csv.DictReader(stream))
    assert len(saved)==7*4*3*27

    lint=load("lint_and_known_failure.json")
    assert len(lint["helm_chart_lint"])==10
    assert all(x["success"] for x in lint["helm_chart_lint"])
    assert not lint["known_hard_failure_control"]["result"]["ok"]
    assert "nil pointer" in lint["known_hard_failure_control"]["result"]["error"]

    parsed=load("promtool_parser_audit.json")
    assert len(parsed["configurations"])==4
    assert all(x["promtool_exit_code"]==0 for x in parsed["configurations"])
    configs={x["arm"]:x for x in parsed["configurations"]}
    assert configs["new_reset_then_reuse_emulated"]["job_count"]==11
    assert configs["new_manually_migrated"]["job_count"]==1

    runtime=load("prometheus_runtime_probe.json")
    probes={x["arm"]:x for x in runtime["results"]}
    assert len(probes)==2
    assert all(not x["original_exact_config"]["started"] for x in probes.values())
    assert all(x["adapted_probe"]["started"] and
               x["adapted_probe"]["readiness_http_status"]==200
               for x in probes.values())
    assert probes["new_reset_then_reuse_emulated"]["adapted_probe"]["job_count"]==11
    assert probes["new_manually_migrated"]["adapted_probe"]["job_count"]==1

    twin=load("provenance_twins.json")
    assert len(twin["cases"])==3
    assert all(x["old_same_manifest_with_explicit_old_default"] and
               x["new_reset_then_reuse_differs_from_implicit"] for x in twin["cases"])
    assert len(twin["chart_families"])==5
    assert all((ROOT/"figures"/name).is_file() for name in (
        "figure1_budgeted_selection.png","figure2_effect_loss.png"
    ))

    print("PASS: 5 chart families / 10 immutable chart archives; "
          "27 real-Helm cases (8 migration contracts + 19 controls)")
    print("PASS: 8/8 manifest contracts lost and repaired; 8/8 detected, "
          "0/19 controls flagged in curated cohort")
    print("PASS: 2,268 seeded rankings; 10/10 lint; 4/4 promtool parser; "
          "2/2 adapted localhost Prometheus probes")
    print("PASS: 3 source-provenance twin divergences; "
          "all recorded artifact hashes match")


if __name__=="__main__":
    main()
