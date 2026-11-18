#!/usr/bin/env python3
"""Create publication-resolution figures from the same audited JSONL inputs."""
import collections
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
FIGS = ROOT / "figures"


def rows(path):
    return [json.loads(l) for l in path.read_text().splitlines()] if path.exists() else []


def main():
    FIGS.mkdir(parents=True, exist_ok=True)
    screened = rows(RESULTS / "screen.jsonl")
    counts = collections.defaultdict(collections.Counter)
    for r in screened:
        counts[r["crate"]][r["label"]] += 1
    names = sorted(counts)
    categories = [
        ("eligible_mismatch", "Feature gap", "#e69f00"),
        ("default_compiles", "Default works", "#009e73"),
        ("invalid_doc_sample", "Non-standalone", "#b8bcc6"),
        ("cfg_dependent", "Docs cfg", "#56b4e9"),
        ("infrastructure", "Infrastructure", "#cc79a7"),
    ]
    fig, ax = plt.subplots(figsize=(11, 6))
    left = np.zeros(len(names))
    for key, label, color in categories:
        vals = np.array([counts[n][key] for n in names])
        if not vals.any():
            continue
        ax.barh(names, vals, left=left, label=label, color=color, height=.72)
        left += vals
    ax.set_xlabel("Independently compiled consumer snippets")
    ax.set_title("Consumer replay results across fixed crate releases", loc="left", weight="bold", pad=48)
    ax.invert_yaxis()
    ax.set_xlim(0, max(left) + .8)
    ax.legend(loc="lower center", bbox_to_anchor=(.5, 1.01), ncol=5, frameon=False, fontsize=8)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.grid(axis="x", color="#dddddd", alpha=.45)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(FIGS / "consumer_replay_by_project.png", dpi=220)
    plt.close(fig)

    searched = rows(RESULTS / "search.jsonl")
    if not searched:
        print("Search not yet available; project figure only")
        return
    measurements = [
        ("Guided", np.mean([int(s["guided"]["pass"]) for s in searched]), "#0072b2"),
        ("Text-only hint", np.mean([int(s["explicit"]["pass"]) for s in searched]), "#009e73"),
        ("Random (3 seeds)", np.mean([np.mean([int(r["pass"]) for r in s["random"]]) for s in searched]), "#e69f00"),
        ("Docs config (label oracle)", 1.0, "#777777"),
    ]
    fig, ax = plt.subplots(figsize=(8.5, 4.1))
    nms = [m[0] for m in measurements]
    vals = [m[1] * 100 for m in measurements]
    bars = ax.barh(nms, vals, color=[m[2] for m in measurements], height=.62)
    for bar, val in zip(bars, vals):
        ax.text(val + 1, bar.get_y() + bar.get_height() / 2, f"{val:.1f}%", va="center", size=10)
    ax.set_xlim(0, 112)
    ax.set_xlabel("Fix found within ≤8 additional Cargo checks (%)")
    ax.set_title(f"Feature-fix search on {len(searched)} compiler-confirmed gap witnesses", loc="left", weight="bold", pad=12)
    ax.invert_yaxis()
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.set_axisbelow(True)
    ax.grid(axis="x", alpha=.3)
    fig.tight_layout()
    fig.savefig(FIGS / "feature_search_success.png", dpi=220)
    plt.close(fig)
    print(f"Saved two PNG figures; {len(searched)} search results")


if __name__ == "__main__":
    main()
