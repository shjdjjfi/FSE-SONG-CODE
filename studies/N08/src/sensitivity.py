#!/usr/bin/env python3
"""Pre-specified breadth, reviewer-budget and temporal sensitivity checks."""

import collections
import json
import statistics

from analyze import ROOT, DATA, METHODS, clustered_summary, observe, pr_data, read_json, save_json, parse_time


def method_values(rows):
    summary = clustered_summary(rows, "recall", n_boot=1200)
    return {"n_pr": len(rows), "n_events": len(set(r["event"] for r in rows)),
            "macro_recall": {m: round(summary[m]["event_macro_mean"], 5) for m in METHODS if m in summary},
            "window_minus_path": round(summary.get("windowed_handoff", {}).get("comparison_vs_current_path", {}).get("event_macro_delta", 0), 5),
            "window_minus_git_follow": round(summary.get("windowed_handoff", {}).get("comparison_vs_git_follow", {}).get("event_macro_delta", 0), 5)}


def main():
    events = [read_json(path) for path in sorted((DATA / "events").glob("*.json"))]
    outputs = {"budget": [], "code_touching": [], "focused_code": [], "grace_windows": [],
               "time_slices": {}, "by_repository": {}, "latency": {}}
    for k in [1, 2, 3, 5]:
        for kind in ["budget", "code_touching", "focused_code"]:
            rows, _ = observe(events, k, max_train=12, max_test=20,
                              code_only=(kind == "code_touching"), focused_only=(kind == "focused_code"))
            item = {"k": k, "sample_kind": kind, **method_values(rows)}
            outputs[kind].append(item)
    for window in [0, 30, 90, 180, 365]:
        r, _ = observe(events, k=2, max_train=12, max_test=20, grace_days=window)
        outputs['grace_windows'].append({'window_days': window, **method_values(r)})
    rows, _ = observe(events, k=2, max_train=12, max_test=20)
    for tag, sub in [("early_le_90_days", [r for r in rows if r["days_after_handoff"] <= 90]),
                     ("late_gt_90_days", [r for r in rows if r["days_after_handoff"] > 90])]:
        outputs["time_slices"][tag] = method_values(sub)
    for repo in sorted(set(r["repo"] for r in rows)):
        sub = [r for r in rows if r["repo"] == repo]
        outputs["by_repository"][repo] = method_values(sub)
    # Observed review latency is descriptive: cannot be attributed to policies.
    durations = []
    for row in rows:
        pr = pr_data(row["repo"], row["pr"])
        opened, merged = parse_time(pr["opened_at"]), parse_time(pr["merged_at"])
        candidates = [parse_time(r["submitted_at"]) for r in pr["reviews"]
                      if r["state"] in ("APPROVED", "CHANGES_REQUESTED") and parse_time(r["submitted_at"]) <= merged]
        if candidates and opened:
            days = (min(candidates) - opened).total_seconds() / 86400
            if days >= 0:
                durations.append(days)
    outputs["latency"] = {"n": len(durations), "first_human_review_median_days": statistics.median(durations) if durations else None,
                          "first_human_review_mean_days": statistics.mean(durations) if durations else None,
                          "not_causal": True}
    save_json("robustness.json", outputs)
    md = ["# Sensitivity analyses (all observational)", "",
          "All values below are event-macro Recall@K against observed human review participants; *not* independently verified experts.", "",
          "## Recommendation budget", "",
          "| Code-edit filter | K | Reviewed PRs | Events | Current path | Git-follow | 180-day handoff | Δ vs current (pp) | Δ vs git-follow (pp) |",
          "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for row in outputs["budget"] + outputs["code_touching"] + outputs["focused_code"]:
        v = row["macro_recall"]
        label = {"budget":"all path-touching", "code_touching":"code-touching", "focused_code":"focused code (post-hoc)"}[row['sample_kind']]
        md.append(f"| {label} | {row['k']} | {row['n_pr']} | {row['n_events']} | {v.get('current_path', 0):.3f} | {v.get('git_follow', 0):.3f} | {v.get('windowed_handoff', 0):.3f} | {100*row['window_minus_path']:+.1f} | {100*row['window_minus_git_follow']:+.1f} |")
    md += ['', '## Handoff-duration ablation (exploratory)', '',
           '| Grace window | Handoff Recall@2 | Δ vs current (pp) | Δ vs permanent lineage (pp) |',
           '|---|---:|---:|---:|']
    for w in outputs['grace_windows']:
        md.append(f"| {w['window_days']} days | {w['macro_recall']['windowed_handoff']:.3f} | {100*w['window_minus_path']:+.1f} | {100*w['window_minus_git_follow']:+.1f} |")
    md += ["", "## Time since migration and repository", "",
           "| Stratum | Reviewed PRs | Events | Current path Recall@2 | Handoff Recall@2 | Δ (pp) |",
           "|---|---:|---:|---:|---:|---:|"]
    for key, v in {**outputs["time_slices"], **outputs["by_repository"]}.items():
        md.append(f"| {key} | {v['n_pr']} | {v['n_events']} | {v['macro_recall'].get('current_path',0):.3f} | {v['macro_recall'].get('windowed_handoff',0):.3f} | {100*v['window_minus_path']:+.1f} |")
    md += ["", "## Descriptive latency", "",
           f"First *observed* decision review: median {outputs['latency']['first_human_review_median_days']:.2f} days (n={outputs['latency']['n']}). No treatment was deployed; no causal latency effect is estimated.",
           "", "The code-touching filter is mechanical, not a semantic gold label. The 'focused code' filter was added after seeing the initial results (>=10% of changed files within the migrated subtree and <=100 files per PR), so it is exploratory and must not be treated as pre-registered confirmation. The grace-window sweep also explores test outcomes after the initial 180-day specification; do not select the highest-scoring window on this same test cohort. The same events can contribute to both time strata; project-level inference is not valid with so few independent projects.", ""]
    (ROOT / "results" / "ROBUSTNESS_TABLES.md").write_text("\n".join(md), encoding="utf-8")
    print("Generated K and code-touching sensitivity tables for", len(rows), "reviewed PRs")


if __name__ == "__main__":
    main()
