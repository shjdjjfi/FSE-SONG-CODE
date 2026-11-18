#!/usr/bin/env python3
"""Recompute N21 figures strictly from measured trial JSONL logs.

This intentionally uses descriptive summaries rather than bogus binomial CIs:
perturbations and seeds in the same repository are not independent projects.
"""

from __future__ import annotations
import argparse
import csv
import json
import statistics as st
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXCLUDE_FAULTS = {"intact", "buildinfo_missing"}
ARMS = ["standard", "selective_path", "selective_hash", "guarded_hash", "invalidate_all", "clean_all", "force_all", "full_cache"]


def med(xs):
    return round(st.median(xs), 3) if xs else None


def pct(n, d):
    return f"{100*n/d:.1f}%" if d else "n/a"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", type=Path, default=HERE / "results")
    args = ap.parse_args()
    results = args.results.resolve()
    rows = []
    for path in results.rglob("trials.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    unique = {}
    for r in rows:
        key = (r["case"], r["project"], r["fault"], r["seed"], r["arm"])
        if key in unique:
            raise RuntimeError(f"Duplicate trial key; do not silently count twice: {key}")
        unique[key] = r
    rows = list(unique.values())
    if not rows:
        raise RuntimeError("No trials found")
    by_arm = defaultdict(list)
    by_case_arm = defaultdict(list)
    by_fault_arm = defaultdict(list)
    for r in rows:
        if r["fault"] not in EXCLUDE_FAULTS:
            by_arm[r["arm"]].append(r)
            by_case_arm[(r["case"], r["arm"])].append(r)
            by_fault_arm[(r["fault"], r["arm"])].append(r)
    pairs = defaultdict(dict)
    for r in rows:
        if r["fault"] in EXCLUDE_FAULTS:
            continue
        pairs[(r["case"], r["project"], r["fault"], r["seed"])][r["arm"]] = r
    comparisons = {}
    for method in ("selective_hash", "guarded_hash"):
      for comparator in ("force_all", "invalidate_all", "clean_all", "full_cache"):
        data = []
        for identity, row in pairs.items():
            a, b = row.get(method), row.get(comparator)
            if a and b and a["correct"] and b["correct"]:
                ua, ub = a["compiled_source_units_proxy"], b["compiled_source_units_proxy"]
                ta, tb = a["repair"]["work_seconds"], b["repair"]["work_seconds"]
                data.append({"case": identity[0], "project": identity[1], "fault": identity[2],
                             "seed": identity[3], "method_units": ua, "baseline_units": ub,
                             "saved_units": ub - ua, "unit_reduction": ((ub - ua)/ub) if ub else None,
                             "method_seconds": ta, "baseline_seconds": tb,
                             "time_saved_seconds": tb - ta})
        comparisons[f"{method}_vs_{comparator}"] = {"n": len(data),
          "median_saved_source_units": med([x["saved_units"] for x in data]),
          "median_unit_reduction": med([x["unit_reduction"] for x in data if x["unit_reduction"] is not None]),
          "median_time_saved_seconds": med([x["time_saved_seconds"] for x in data]),
          "mean_time_saved_seconds": round(st.mean(x["time_saved_seconds"] for x in data),3) if data else None,
          "projects": sorted(set((x["case"],x["project"]) for x in data))}
    summary = {
        "total_trials": len(rows), "workspace_cases": sorted(set(r["case"] for r in rows)),
        "distinct_projects": sorted(set((r["case"], r["project"]) for r in rows)),
        "fault_types": sorted(set(r["fault"] for r in rows)),
        "seeds": sorted(set(r["seed"] for r in rows)),
        "arm_summaries": {arm: {
            "n":len(by_arm[arm]), "correct":sum(r["correct"] for r in by_arm[arm]),
            "median_compile_units":med([r["compiled_source_units_proxy"] for r in by_arm[arm]]),
            "median_seconds":med([r["repair"]["work_seconds"] for r in by_arm[arm]])
          } for arm in ARMS if arm in by_arm},
        "case_arm": {f"{case}:{arm}": {"n":len(v), "correct":sum(x["correct"] for x in v),
              "median_units":med([x["compiled_source_units_proxy"] for x in v]),
              "median_seconds":med([x["repair"]["work_seconds"] for x in v])}
            for (case,arm),v in sorted(by_case_arm.items())},
        "fault_arm": {f"{fault}:{arm}": {"n":len(v), "correct":sum(x["correct"] for x in v)}
                       for (fault,arm),v in sorted(by_fault_arm.items())},
        "paired_comparisons": comparisons,
        "method_limitations": ["All observed faults were deliberately injected, not sampled from real CI failure logs.",
          "Repository-level dependence precludes treating every trial or random seed as an independent sample.",
          "full_cache is an idealized *available complete cache hit*; this baseline must be conditioned on availability.",
          "Units count project source files for projects reported as rebuilt; not instructions or CPU work."],
    }
    out = results / "analysis.json"
    out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    with (results / "all_trials.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["case","project","fault","seed","arm","correct",
                       "compiled_source_units_proxy","seconds","missing_before","altered_before","extra_before",
                       "missing_after","altered_after","extra_after","projects_compiled"])
        writer.writeheader()
        for x in sorted(rows, key=lambda a:(a["case"],a["project"],a["fault"],a["seed"],a["arm"])):
            writer.writerow({"case":x["case"],"project":x["project"],"fault":x["fault"],
                "seed":x["seed"],"arm":x["arm"],"correct":x["correct"],
                "compiled_source_units_proxy":x["compiled_source_units_proxy"],
                "seconds":x["repair"]["work_seconds"],"missing_before":x["before"]["missing"],
                "altered_before":x["before"]["altered"],"extra_before":x["before"]["extra"],
                "missing_after":x["after"]["missing"],"altered_after":x["after"]["altered"],
                "extra_after":x["after"]["extra"],
                "projects_compiled":",".join(x["repair"]["compiled_projects"])})
    headers = "| Strategy | Correct / injected cases | Median source units rebuilt | Median wall time |"
    lines = ["# N21: Measured Experiment Summary", "", "_Recomputed solely from archived trial records._", "",
             f"Analyzed {len(rows)} trials in {len(summary['workspace_cases'])} workspaces and "
             f"{len(summary['distinct_projects'])} distinct projects; seeds {summary['seeds']}.", "", headers,
             "|---|---:|---:|---:|"]
    for arm in ARMS:
        if arm not in by_arm:
            continue
        v = summary["arm_summaries"][arm]
        lines.append(f"| `{arm}` | {v['correct']}/{v['n']} | {v['median_compile_units']} | {v['median_seconds']} s |")
    lines.extend(["", "A full cache hit restores complete outputs without compilation and is therefore not the same operating condition as an unavailable/incomplete cache.",
                  "The comparisons are conditional on preexisting input/output identity. Exact manifests are generated from a trusted prior build.",
                  "", "## Separate workspaces", "", "| Workspace | Arm | Correct / cases | Median units | Median time |",
                  "|---|---|---:|---:|---:|"])
    for case in summary["workspace_cases"]:
        for arm in ARMS:
            key=f"{case}:{arm}"
            if key in summary["case_arm"]:
                v=summary["case_arm"][key]
                lines.append(f"| {case} | {arm} | {v['correct']}/{v['n']} | {v['median_units']} | {v['median_seconds']} s |")
    lines.extend(["", "## Main paired comparison (hash-manifest vs alternatives)", ""])
    for base, v in comparisons.items():
        lines.append(f"- `{base}`: {v['n']} pairs where **both** methods were correct; median "
            f"saved source-file proxy {v['median_saved_source_units']}, median reduction "
            f"{(str(round(v['median_unit_reduction']*100,1))+'%') if v['median_unit_reduction'] is not None else 'n/a'}, "
            f"median wall-time difference {v['median_time_saved_seconds']} seconds. "
            "These repeated faults are correlated within projects.")
    lines.extend(["", "## Scientific cautions", ""])
    lines.extend([f"- {s}" for s in summary["method_limitations"]])
    (results / "EXPERIMENT_REPORT.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    print(f"{len(rows)} trials; saved {out}, all_trials.csv and EXPERIMENT_REPORT.md")

if __name__ == "__main__":
    main()
