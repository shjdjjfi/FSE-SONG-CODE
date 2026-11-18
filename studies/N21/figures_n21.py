#!/usr/bin/env python3
"""Paper-ready SVG figures from audited JSON, with no manually entered data."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from run_n21 import HERE


LABELS = {
    "standard": "Unforced tsc -b",
    "selective_path": "Path manifest",
    "selective_hash": "Output SHA manifest",
    "guarded_hash": "Input-guarded SHA",
    "invalidate_all": "Invalidate all buildinfo",
    "clean_all": "Clean build",
    "force_all": "Force solution",
    "full_cache": "Complete cache hit*",
}


def main() -> None:
    data = json.loads((HERE / "results" / "paper_main_table.json").read_text())
    robustness = json.loads((HERE / "results" / "robustness.json").read_text())
    # Guard against unintentional graphic/data divergence.
    records = data["by_arm"]
    figdir = HERE / "figures"
    figdir.mkdir(exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "svg.fonttype": "none", "axes.spines.top": False,
                         "axes.spines.right": False, "figure.facecolor": "white"})

    keys = list(LABELS)
    yy = list(range(len(keys)))
    correct = [records[key]["correct"] for key in keys]
    n = [records[key]["total"] for key in keys]
    colors = ["#4b5563", "#8b5cf6", "#0d9488", "#0f766e",
              "#fb923c", "#2563eb", "#f97316", "#1d4ed8"]
    fig, ax = plt.subplots(figsize=(8.5, 4.9), constrained_layout=True)
    ax.barh(yy, [100 * x / y for x, y in zip(correct, n)],
            color=colors, height=0.66, edgecolor="none")
    ax.set_yticks(yy, [LABELS[key] for key in keys])
    ax.invert_yaxis()
    ax.set_xlim(0, 116)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xlabel("Agreement with independent clean output (%)")
    ax.grid(axis="x", alpha=0.15)
    ax.set_axisbelow(True)
    for i, (a, b) in enumerate(zip(correct, n)):
        ax.text(100 * a / b + 1.5, i, f"{a}/{b}", va="center", fontsize=9)
    fig.suptitle("Recovery correctness under 77 controlled fault settings", weight="semibold")
    ax.text(0, 1.02, "*Only when a complete, valid local cache entry is available",
            transform=ax.transAxes, va="bottom", fontsize=8, color="#52525b")
    fig.savefig(figdir / "figure_1_correctness.svg", bbox_inches="tight")
    plt.close(fig)

    projects = sorted(robustness["by_project"],
                      key=lambda k: (k.split("/")[0], k.split("/")[1]))
    values = [robustness["by_project"][k]["median_saved_fraction"] * 100 for k in projects]
    # Endpoints are project-level medians over repeated fault injections.
    fig, ax = plt.subplots(figsize=(8.5, 6.2), constrained_layout=True)
    ax.barh(range(len(projects)), values, color=["#0f766e" if v > 0 else "#94a3b8" for v in values],
            height=0.7)
    ax.set_yticks(range(len(projects)), projects)
    ax.invert_yaxis()
    ax.set_xlim(0, 103)
    ax.set_xlabel("Median fraction of source units not recompiled versus clean build (%)")
    ax.grid(axis="x", alpha=0.15)
    ax.set_axisbelow(True)
    fig.suptitle("Repair savings differ substantially by reference graph", weight="semibold")
    ax.text(0, 1.01, "Project-group medians; 77 paired injection settings, no industrial incidence weighting",
            transform=ax.transAxes, fontsize=8, color="#52525b")
    fig.savefig(figdir / "figure_2_project_heterogeneity.svg", bbox_inches="tight")
    plt.close(fig)
    print("Wrote two vector SVG figures")


if __name__ == "__main__":
    main()
