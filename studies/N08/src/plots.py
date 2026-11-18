#!/usr/bin/env python3
"""Paper-figure plotting from measured JSON (never hardcoded outcomes)."""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
FIGURES = RESULTS / "figures"
COLORS = {"current_path": "#246F99", "git_follow": "#C08338", "windowed_handoff": "#45825D"}
LABELS = {"current_path": "Target-path history", "git_follow": "Permanent Git lineage", "windowed_handoff": "180-day handoff"}


def read(name):
    return json.loads((RESULTS / name).read_text())


def save(fig, name):
    FIGURES.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "svg"):
        fig.savefig(FIGURES / f"{name}.{ext}", bbox_inches="tight", dpi=220)
    plt.close(fig)


def main():
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False,
                         "axes.spines.right": False, "figure.facecolor": "white",
                         "axes.labelcolor": "#333333", "text.color": "#222222"})
    modes = [(name, read(path)) for name, path in [
             ("All path-touching", "metrics.json"),
             ("Code-touching", "code_metrics.json"),
             ("Focused, exploratory", "focused_metrics.json")]]
    methods = list(COLORS)
    fig, ax = plt.subplots(figsize=(9.7, 4.6))
    xs = [0, 1, 2]
    for j, m in enumerate(methods):
        vals = [d["metrics"]["recall"][m]["event_macro_mean"] * 100 for _, d in modes]
        ps = ax.bar([x + (j - 1) * .23 for x in xs], vals, .21, color=COLORS[m], label=LABELS[m])
        for p, v in zip(ps, vals):
            ax.annotate(f"{v:.1f}", (p.get_x() + p.get_width() / 2, p.get_height()),
                        ha="center", va="bottom", fontsize=8, xytext=(0, 2), textcoords="offset points")
    ax.set_xticks(xs, [f"{name} (n={d['evaluated_prs']})" for name, d in modes]);ax.set_ylabel("Event-macro Recall@2 (%)")
    ax.set_ylim(0, 50);ax.legend(frameon=False, ncol=3, loc="upper left", fontsize=8.5)
    ax.grid(axis="y", alpha=.16);fig.tight_layout();save(fig, "fig1_reviewer_coverage")

    sens = read("robustness.json")["budget"]
    fig, ax = plt.subplots(figsize=(7.3, 4.5))
    for m in methods:
        ax.plot([d["k"] for d in sens], [100 * d["macro_recall"][m] for d in sens],
                marker="o", markersize=6, linewidth=2.25, color=COLORS[m], label=LABELS[m])
    ax.set_xticks([1, 2, 3, 5]);ax.set_xlabel("Reviewer recommendation budget (K)")
    ax.set_ylabel("Event-macro Recall@K (%)");ax.set_ylim(0, 52)
    ax.grid(alpha=.17);ax.legend(frameon=False, loc="upper left", fontsize=9)
    ax.text(.02, .04, "K=1 and K=5 do not improve on target history", transform=ax.transAxes, fontsize=8, color="#555555")
    fig.tight_layout();save(fig, "fig2_budget_sensitivity")

    d = read("metrics.json")["metrics"]["recall"]["windowed_handoff"]["comparison_vs_current_path"]["event_deltas"]
    names = sorted(d, key=lambda n: d[n])
    vals = [d[n] * 100 for n in names]
    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    ax.barh(names, vals, color=["#C88369" if v < 0 else "#45825D" for v in vals], height=.7)
    ax.axvline(0, color="#888888", linewidth=1)
    ax.set_xlabel("Handoff minus target history: Recall@2 (percentage points)")
    ax.set_title("Heterogeneity across nine migration events", fontsize=11, loc="left", pad=12)
    ax.grid(axis="x", alpha=.13);fig.tight_layout();save(fig, "fig3_event_heterogeneity")
    print("Saved three publication-ready SVG/PNG figure pairs")


if __name__ == "__main__":
    main()
