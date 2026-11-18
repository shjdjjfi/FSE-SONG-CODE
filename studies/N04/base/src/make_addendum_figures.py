"""Publication-style figures strictly from frozen independent results."""

from __future__ import annotations
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def holdout(stats,out):
    per=stats["per_repository"]
    names=[r["repository"].split("/")[-1] for r in per]
    guard=[100*r["guarded_recovered"]/r["n_tp"] for r in per]
    simple=[100*r["name_only_recovered"]/r["n_tp"] for r in per]
    ns=[r["n_tp"] for r in per]
    x=np.arange(len(per));bar=0.32
    fig,ax=plt.subplots(figsize=(8.4,4.5),constrained_layout=True)
    ax.bar(x-bar/2,simple,width=bar,color="#71839A",label="Unique method name")
    ax.bar(x+bar/2,guard,width=bar,color="#167D82",label="Guarded lineage")
    ax.set_xticks(x,[f"{n}\n(n={total})" for n,total in zip(names,ns)])
    ax.set_ylim(0,110)
    ax.set_yticks([0,20,40,60,80,100])
    ax.set_ylabel("Independent refactoring-target recall (%)")
    ax.set_title("Cross-project source successor discovery (no given new ID)",fontsize=11)
    ax.legend(loc="upper right")
    ax.grid(axis="y",alpha=.23)
    ax.set_axisbelow(True)
    fig.text(.01,-.03,"54 refactoring edges in 4 repositories; one 1-to-2 split. Not a quarantine-safety oracle.",fontsize=8)
    for suffix in ("png","pdf"):
        fig.savefig(out/("independent_holdout_recall."+suffix),dpi=180,bbox_inches="tight")
    plt.close(fig)


def quarantine(case,ci,out):
    import matplotlib.patches as patches
    fig,ax=plt.subplots(figsize=(9.4,3.5),constrained_layout=True)
    provenance=case["decision_provenance"]
    counts=case["source_declared_test_counts"]
    assert (provenance["actual_before_excluded"] and provenance["actual_after_new_excluded"]
            and provenance["actual_after_old_not_excluded"])
    states=[[2,1],[0,2]]  # before: quarantined old, absent new; after: old regular, new quarantined
    # rows in display: old parent, new extracted test file
    cmap={0:("Not present","#E8EBEE"),1:("Default CI","#B9E8D7"),2:("Quarantined","#F6C7A2")}
    for row in range(2):
        for col in range(2):
            val=states[row][col]
            label,color=cmap[val]
            ax.add_patch(patches.FancyBboxPatch((col+.03,1-row+.1),.94,.78,
                                               boxstyle="round,pad=0.02,rounding_size=0.04",
                                               facecolor=color,edgecolor="white",lw=2))
            ax.text(col+.5,1-row+.49,label,ha="center",va="center",fontsize=10,weight="bold")
    ax.set_xlim(0,2);ax.set_ylim(0,3)
    ax.set_xticks([.5,1.5],["Before split","After split"])
    ax.set_yticks([1.5,.5],[f"extension.test.ts\n{counts['old_file_before']} → {counts['old_file_after']} it()",
                               f"extension-dist-barrel.test.ts\n0 → {counts['new_file_after']} it()"])
    ax.tick_params(axis="both",length=0,pad=8)
    for spine in ax.spines.values():spine.set_visible(False)
    ax.set_title("Observed Fusion quarantine transfer, commit b545083",fontsize=12)
    before,after=ci["runs"]
    fig.text(.02,-.05,f"Both ledgers cite Actions run #{before['id']}. Later Full Suite also failed "
             f"({before['overall_update_elapsed_seconds']:.0f} s → {after['overall_update_elapsed_seconds']:.0f} s); no causal cost claim.",fontsize=8)
    for suffix in ("png","pdf"):
        fig.savefig(out/("fusion_quarantine_split."+suffix),dpi=180,bbox_inches="tight")
    plt.close(fig)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--results",type=Path,default=Path("results"))
    p.add_argument("--output",type=Path,default=Path("figures"))
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    get=lambda filename:json.loads((a.results/filename).read_text())
    holdout(get("independent_generalization_statistics.json"),a.output)
    quarantine(get("fusion_identity_linked_quarantine.json"),get("fusion_real_ci_runs.json"),a.output)
    print("Two independent-evidence figures generated in PNG and PDF")
