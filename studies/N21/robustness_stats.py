#!/usr/bin/env python3
"""Paired project/workspace sensitivity checks, with no independence claims."""
from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
from statistics import median

from run_n21 import HERE


def compact(values: list[float]) -> float:
    return round(median(values), 4)


def main() -> None:
    trials: dict[tuple, dict] = {}
    for file in (HERE / "results").rglob("trials.jsonl"):
        for line in file.read_text(encoding="utf-8").splitlines():
            if not line:
                continue
            item = json.loads(line)
            key = (item["case"], item["project"], item["fault"], item["seed"], item["arm"])
            if key in trials:
                raise RuntimeError(f"Duplicate observation: {key}")
            trials[key] = item
    paired = []
    for key, guarded in trials.items():
        case, project, fault, seed, arm = key
        if (seed != 17 or arm != "guarded_hash" or not sum(guarded["before"].values()) or
                (case, project, fault, seed, "selective_hash") not in trials):
            continue
        clean = trials.get((case, project, fault, seed, "clean_all"))
        if clean is None:
            raise RuntimeError(f"Missing clean comparator for {key}")
        if not guarded["correct"] or not clean["correct"]:
            raise RuntimeError(f"Inexact paired outputs at {key}")
        g, c = guarded["compiled_source_units_proxy"], clean["compiled_source_units_proxy"]
        paired.append({"workspace": case, "project": project, "fault": fault,
                       "saved_source_units": c - g,
                       "saved_fraction": (c - g) / c if c else 0,
                       "saved_seconds": round(clean["repair"]["work_seconds"]
                                              - guarded["repair"]["work_seconds"], 4)})
    if len(paired) != 77:
        raise AssertionError(f"Expected paired 77 primary settings, got {len(paired)}")
    by_project = defaultdict(list)
    by_workspace = defaultdict(list)
    for row in paired:
        by_project[(row["workspace"], row["project"])].append(row)
        by_workspace[row["workspace"]].append(row)

    def describe(rows):
        return {"settings": len(rows),
                "median_saved_source_units": compact([r["saved_source_units"] for r in rows]),
                "median_saved_fraction": compact([r["saved_fraction"] for r in rows]),
                "median_saved_seconds": compact([r["saved_seconds"] for r in rows]),
                "settings_with_fewer_units": sum(r["saved_source_units"] > 0 for r in rows),
                "settings_faster": sum(r["saved_seconds"] > 0 for r in rows)}

    project_summary = {f"{case}/{project}": describe(rows)
                       for (case, project), rows in sorted(by_project.items())}
    workspace_summary = {case: describe(rows) for case, rows in sorted(by_workspace.items())}
    loo = {excluded: describe([r for r in paired if r["workspace"] != excluded])
           for excluded in sorted(by_workspace)}
    report = {"design": "paired main seed-17 faults; descriptive only",
              "n_settings": len(paired), "n_projects": len(by_project),
              "n_workspaces": len(by_workspace), "overall": describe(paired),
              "by_workspace": workspace_summary, "by_project": project_summary,
              "leave_one_workspace_out": loo,
              "statistics_warning": "Four clusters, non-random faults, and shared fixtures: no CI or p-value about production populations is justified."}
    out = HERE / "results" / "robustness.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = ["# Paired robustness and sensitivity", "",
             "Same 77 seed-17 settings, input-guarded SHA against clean build; all 77 paired outputs exact.",
             "This is descriptive research-fixture data, **not an inferential independent sample**.", "",
             "| Subset | Paired settings | Median fewer source units | Median fraction fewer | Median local seconds saved | Settings faster |",
             "|---|---:|---:|---:|---:|---:|"]
    for label, stats in [("Overall", report["overall"])] + list(workspace_summary.items()):
        lines.append(f"| {label} | {stats['settings']} | {stats['median_saved_source_units']:.1f} | "
                     f"{stats['median_saved_fraction']:.1%} | {stats['median_saved_seconds']:+.2f} | "
                     f"{stats['settings_faster']}/{stats['settings']} |")
    lines.extend(["", "## Leave one workspace out (sensitivity, not confidence intervals)", "",
                  "| Workspace omitted | Settings retained | Median fraction fewer source units | Median local seconds saved |",
                  "|---|---:|---:|---:|"])
    for label, stats in loo.items():
        lines.append(f"| {label} | {stats['settings']} | "
                     f"{stats['median_saved_fraction']:.1%} | {stats['median_saved_seconds']:+.2f} |")
    lines.extend(["", "## Per-project descriptive medians", "",
                  "| Project | Settings | Median fewer units | Median seconds saved | Settings faster |",
                  "|---|---:|---:|---:|---:|"])
    for label, stats in project_summary.items():
        lines.append(f"| {label} | {stats['settings']} | {stats['median_saved_source_units']:.1f} | "
                     f"{stats['median_saved_seconds']:+.2f} | {stats['settings_faster']}/{stats['settings']} |")
    lines.extend(["", "The unit metric is compiler-logged rebuilt-project source-file counts, not CPU instructions.",
                  "Do not treat faults, seeds, or project units from the same repository as independent industrial incidents.", ""])
    (HERE / "results" / "ROBUSTNESS.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Paired {len(paired)} settings / {len(by_project)} projects / {len(by_workspace)} workspaces")
    print(json.dumps(report["overall"], ensure_ascii=False))


if __name__ == "__main__":
    main()
