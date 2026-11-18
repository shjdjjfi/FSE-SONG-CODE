"""Generate paper-ready static figures from measured N04 results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def save(fig, base:Path):
    fig.savefig(base.with_suffix(".png"),dpi=350,bbox_inches="tight")
    fig.savefig(base.with_suffix(".pdf"),bbox_inches="tight")
    plt.close(fig)


def main(result_root:Path, dest:Path):
    dest.mkdir(parents=True,exist_ok=True)
    summary=json.loads((result_root/"migration_benchmark/results.json").read_text())
    history=json.loads((result_root/"history_replay/history_results.json").read_text())
    pytest=json.loads((result_root/"pytest_behavior/pytest_8.4.2.json").read_text())
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":9,
                         "axes.spines.top":False,"axes.spines.right":False,
                         "figure.facecolor":"white","savefig.facecolor":"white"})

    fig,ax=plt.subplots(figsize=(7.2,4.0))
    label_offsets={
        "exact_node_id":(6,6),"method_name":(8,19),
        "file_method":(10,-20),"hybrid_posthoc":(8,11),
        "semantic_anchor":(-87,-19),"source_similarity":(8,17),
        "ablate_context":(8,-19),"ablate_assertions":(8,8),
    }
    for method,entry in summary["summary"].items():
        key=method.replace("_"," ")
        is_simple=method=="method_name"
        is_proposed=method=="semantic_anchor"
        color="#147d64" if is_simple else ("#cc3d43" if is_proposed else "#6687aa")
        ax.scatter(entry["combined_false_transfer_rate"]*100,
                   entry["recovery_rate"]*100,
                   s=125 if is_simple or is_proposed else 70,
                   marker="D" if is_proposed else "o",c=color,
                   zorder=3)
        ax.annotate(key,(entry["combined_false_transfer_rate"]*100,
                         entry["recovery_rate"]*100),xytext=label_offsets[method],
                    textcoords="offset points",fontsize=8)
    ax.axvline(2.,ls="--",lw=1.2,c="#666666",label="2% calibration risk target")
    ax.set_xlabel("Observed wrong-transfer rate on held-out projects (%)")
    ax.set_ylabel("Correct identity recovery (%)")
    ax.set_xlim(-.4,max(4.8,ax.get_xlim()[1]))
    ax.set_ylim(0,105)
    ax.grid(alpha=.12)
    ax.legend(loc="lower left",frameon=False,fontsize=8)
    ax.set_title("Cross-project identity linking (842 pairs/seed; three seeds)",pad=10)
    save(fig,dest/"fig01_recovery_risk")

    attempts=history["summary"]["by_seed"]
    labels=[str(x["seed"]) for x in attempts]
    original=np.array([x["future_flaky_missed_preserved"] for x in attempts])
    reset=np.array([x["future_flaky_missed_reset"] for x in attempts])
    fig,ax=plt.subplots(figsize=(6.8,3.4))
    xx=np.arange(len(labels))
    w=.34
    a=ax.bar(xx-w/2,original,width=w,color="#147d64",label="Full 20-outcome history")
    b=ax.bar(xx+w/2,reset,width=w,color="#cc6b45",label="History reset to last 5")
    ax.bar_label(a,padding=2,fontsize=8)
    ax.bar_label(b,padding=2,fontsize=8)
    ax.set_xticks(xx,labels)
    ax.set_xlabel("Outcome-permutation seed")
    ax.set_ylabel("Future flaky cases missed")
    ax.set_ylim(0,max(reset)*1.45)
    ax.set_title("Counterfactual reset on genuine repeated test outcomes")
    ax.legend(frameon=False,loc="upper left",fontsize=8)
    fig.subplots_adjust(bottom=.26)
    fig.text(.5,.02,"Identity reset is simulated; CI quarantine actions were not observed.",
             ha="center",fontsize=7,color="#555555")
    save(fig,dest/"fig02_real_history_replay")

    examples=pytest["scenarios"]
    names=[x["scenario"].replace("_"," ") for x in examples]
    before=[x["same_identity_selection"]["collected_count"] for x in examples]
    broken=[x["after_edit_selection"]["collected_count"] for x in examples]
    bridge=[x["after_bridge_selection"]["collected_count"] for x in examples]
    fig,ax=plt.subplots(figsize=(7.4,3.6))
    xx=np.arange(len(names))
    w=.25
    ax.bar(xx-w,before,width=w,color="#7694ad",label="Before identity change")
    ax.bar(xx,broken,width=w,color="#cc6b45",label="Native pytest after change")
    ax.bar(xx+w,bridge,width=w,color="#147d64",label="Strict cache bridge")
    ax.set_xticks(xx,names,rotation=15,ha="right")
    ax.set_ylabel("Tests selected by --lf --lfnf none")
    ax.set_ylim(0,5.5)
    ax.set_title("Real pytest 8.4.2 executions of controlled test changes")
    ax.legend(frameon=False,fontsize=8,loc="upper left")
    save(fig,dest/"fig03_pytest_cache_behavior")

    paired_file=result_root/"java_before_after/before_after_results.json"
    if paired_file.exists():
        paired=json.loads(paired_file.read_text())
        keys=["Issue256Test","Issue580Test"]
        values=[paired["summaries"][k] for k in keys]
        xx=np.arange(2);w=.32
        fig,ax=plt.subplots(figsize=(5.8,3.5))
        a=ax.bar(xx-w/2,[v["pre_nonpass"] for v in values],width=w,
                 color="#7694ad",label="Parent commit")
        b=ax.bar(xx+w/2,[v["post_nonpass"] for v in values],width=w,
                 color="#d06d4b",label="Parameterized commit")
        ax.bar_label(a,padding=4)
        ax.bar_label(b,padding=4)
        ax.set_xticks(xx,keys)
        ax.set_ylabel("Observed failures or errors")
        ax.set_ylim(0,14)
        ax.set_title("One real JUnit refactoring: 30 runs per revision")
        ax.legend(frameon=False,loc="upper right",fontsize=8)
        fig.subplots_adjust(bottom=.20)
        fig.text(.5,.025,"Execution order and environment are not randomized; differences are descriptive.",
                 ha="center",fontsize=7,color="#555555")
        save(fig,dest/"fig04_java_before_after")
    print("Generated",list(sorted(str(x.name) for x in dest.glob("*.png"))))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--results",type=Path,default=Path("results"))
    p.add_argument("--out",type=Path,default=Path("figures"))
    a=p.parse_args()
    main(a.results,a.out)
