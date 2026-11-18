#!/usr/bin/env python3
"""Publication figures from measured independent results and sensitivity data."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figures"


def main():
    FIG.mkdir(exist_ok=True)
    obj = json.loads((ROOT / "prospective/results/consumer_sensitivity.json").read_text())
    sets = [obj["full_preregistered_cohort"], obj["after_excluding_explicit_test_fixture_import"]]
    labels = ["Full preregistered\n24 cases / 9 repos", "After excluding hidden test fixture\n18 cases / 8 repos (post-hoc)"]
    methods = [
        ("Guided v1", "guided_success_at_8", "#246a9c"),
        ("Random (3 seeds)", "random_success_at_8", "#f49a35"),
        ("Native compiler hints", "diagnostic_success_at_8", "#697984"),
        ("Source-path v2", "pathaware_success_at_8", "#4b9c78"),
    ]
    fig, ax = plt.subplots(figsize=(10, 4.6))
    x = np.arange(2)
    width = .19
    for j,(label,key,color) in enumerate(methods):
        vals = [100*r[key] for r in sets]
        xs = x + (j-1.5)*width
        bars = ax.bar(xs, vals, width=width-.015, label=label, color=color)
        for b,val in zip(bars,vals):
            ax.text(b.get_x()+b.get_width()/2, min(100,val)+1.5, f"{val:.1f}",
                    ha="center",va="bottom",fontsize=9)
    ax.set_ylim(0, 112)
    ax.set_ylabel("Search success @ 8 extra Cargo checks (%)")
    ax.set_xticks(x,labels)
    ax.grid(axis="y",alpha=.18)
    ax.spines[["right","top"]].set_visible(False)
    ax.legend(loc="lower left",ncol=2,frameon=False,fontsize=9)
    fig.suptitle("Independent releases: reported gain vs consumer-relevant sensitivity",fontweight="bold",y=.99)
    fig.tight_layout()
    fig.savefig(FIG/"n05_independent_robustness.png",dpi=230,bbox_inches="tight")
    plt.close(fig)

    budget = json.loads((ROOT / "paper/BUDGET_CURVE_EXPLORATORY.json").read_text())["prospective"]["exploratory_budget_curve"]
    fig, ax = plt.subplots(figsize=(9.3, 4.7))
    for name,key,color,style in [
        ("Guided v1","guided_success","#246a9c","-"),
        ("Random (3 seeds)","random_success","#f49a35","--"),
        ("Native rustc diagnostic","diagnostic_success","#697984",":"),
        ("Source-path v2","pathaware_success","#4b9c78","-."),
    ]:
        vals = [r[key]*100 for r in budget]
        if any(r[key] is None for r in budget):
            continue
        ax.plot([r["budget"] for r in budget],vals,marker="o",markersize=4.2,
                linewidth=2.1,linestyle=style,label=name,color=color)
    ax.set(xlim=(.75,8.25),ylim=(0,105),xticks=list(range(1,9)),
           xlabel="Maximum additional Cargo checks (k)",ylabel="Success @ k (%)")
    ax.set_title("Exploratory budget curve — all 24 positive independent-release cases")
    ax.grid(alpha=.22)
    ax.spines[["top","right"]].set_visible(False)
    ax.legend(frameon=False,loc="lower right")
    fig.tight_layout()
    fig.savefig(FIG/"n05_budget_curve_exploratory.png",dpi=230,bbox_inches="tight")
    plt.close(fig)
    print("Wrote independent-release figures to figures/")


if __name__ == "__main__":
    main()
