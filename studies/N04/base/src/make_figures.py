"""Publication-resolution exploratory figures from measured JSON results."""

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def draw(data_dir: Path, output_dir: Path):
    output_dir.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({"figure.dpi":130,"savefig.dpi":220,"font.size":10,
                         "axes.spines.top":False,"axes.spines.right":False})
    data=json.loads((data_dir/"idoft_evaluation.json").read_text())
    summary=data["summary"]
    labels={"exact_node_id":"Exact ID", "git_path_same_method":"Path + name",
            "name_similarity":"Name only","exact_body":"Body hash",
            "name_and_context":"Name + path",
            "guarded_lineage":"Guarded","ablation_no_body":"No-body",
            "ablation_no_group_guard":"No group gate"}
    xs=np.arange(len(summary))
    recalls=np.array([100*x["positive_recall"] if x["positive_recall"] is not None else 0 for x in summary])
    fprs=np.array([100*x["deleted_false_rate"] if x["deleted_false_rate"] is not None else 0 for x in summary])
    clean=np.array([100*x["uncontested_deleted_false_rate"] if x["uncontested_deleted_false_rate"] is not None else 0 for x in summary])
    fig,ax=plt.subplots(figsize=(11.3,5.2))
    wd=.26
    ax.bar(xs-wd,recalls,width=wd,color="#276a8a",label="Recovered individual links (%)")
    ax.bar(xs,fprs,width=wd,color="#ba6e50",label="Deleted-label transfer (%)")
    ax.bar(xs+wd,clean,width=wd,color="#9cb482",label="Uncontested deleted transfer (%)")
    ax.set_xticks(xs,[labels.get(x["arm"],x["arm"]) for x in summary],rotation=27,ha="right")
    ax.set_ylim(0,108)
    ax.set_ylabel("Rate (%)")
    ax.set_title("Exploratory test-lineage replay: accuracy–safety trade-off")
    ax.grid(axis="y",alpha=.2)
    ax.legend(loc="upper left",fontsize=9)
    fig.text(.01,.01,"Source-derived successor FQNs; four deleted labels conflict with a same-body/path-move rule. No live CI outcomes.",fontsize=8,color="#555")
    fig.tight_layout(rect=(0,.05,1,1))
    for ext in ("png","pdf"):
        fig.savefig(output_dir/f"lineage_tradeoff.{ext}",bbox_inches="tight")
    plt.close(fig)

    history=json.loads((data_dir/"ftw_histories.json").read_text())
    tracks=history["summary"]
    fig,axs=plt.subplots(1,2,figsize=(12,5),gridspec_kw={"width_ratios":[2,1]})
    order=sorted(tracks,key=lambda x:-x["n_status_observations"])
    y=np.arange(len(order))
    axs[0].barh(y,[x["n_status_observations"]/1_000_000 for x in order],color="#4684a5")
    axs[0].set_yticks(y,[x["project"] for x in order])
    axs[0].invert_yaxis()
    axs[0].set_xlabel("Repeated test outcomes (millions)")
    axs[0].set_title("Measured regression-history dataset")
    axs[1].barh(y,[x["n_flaky_test_ids"] for x in order],color="#b87755")
    axs[1].set_yticks(y,["" for _ in order])
    axs[1].invert_yaxis()
    axs[1].set_xlabel("Test IDs with mixed pass/fail at a commit")
    axs[1].set_title("Observed within-commit flakiness")
    for ax in axs: ax.grid(axis="x",alpha=.16)
    fig.text(.01,.005,"FTW 2024 offline repeated execution, not recorded production CI; duplicated histories share repositories.",fontsize=8,color="#555")
    fig.tight_layout(rect=(0,.04,1,1))
    for ext in ("png","pdf"):
        fig.savefig(output_dir/f"ftw_source_coverage.{ext}",bbox_inches="tight")
    plt.close(fig)

    replay=json.loads((data_dir/"pytest_cache_replay.json").read_text())
    experiments=replay["experiments"]
    fig,ax=plt.subplots(figsize=(7.8,4.5))
    phases=("baseline_same_id","stale_renamed","identity_migrated")
    phase_names=("Original ID exists","Stale ID after rename","Migrated ID")
    vals=[np.mean([x[p]["selected_count"] for x in experiments]) for p in phases]
    bars=ax.bar(phase_names,vals,color=["#4f9275","#bd744b","#4f9275"],width=.52)
    for b,v in zip(bars,vals):ax.text(b.get_x()+b.get_width()/2,v+.06,f"{v:g}",ha="center")
    ax.set_ylim(0,3.6)
    ax.set_yticks([0,1,2,3])
    ax.set_ylabel("Tests selected (real pytest 8.4.2)")
    ax.set_title("Controlled lastfailed cache replay (3 name variants)")
    ax.grid(axis="y",alpha=.18)
    fig.tight_layout()
    for ext in ("png","pdf"):
        fig.savefig(output_dir/f"pytest_cache_mechanism.{ext}",bbox_inches="tight")
    plt.close(fig)

    parameter=json.loads((data_dir/"junit_parameter_migration.json").read_text())
    series=parameter["mapping_strategies"]
    fig,ax=plt.subplots(figsize=(9,4.5))
    labels={"exact_runtime_id":"Exact runtime ID","method_level_name_only":"Method-level name",
            "guarded_abstain_on_group":"Abstain on N-to-1","source_family_plus_parameter_index":"Source + param ID"}
    names=[labels[x["strategy"]] for x in series]
    recovered=[x["candidate_instance_links"] for x in series]
    merged=[x["unsafe_collapsed_groups"] for x in series]
    x=np.arange(len(series))
    a=ax.bar(x-.19,recovered,.35,color="#398270",label="Unique candidate instance links")
    b=ax.bar(x+.19,merged,.35,color="#bd7155",label="Ambiguous method-level merges")
    for bars in (a,b):
        for bar in bars:
            if bar.get_height():ax.annotate(str(int(bar.get_height())),
                                            (bar.get_x()+bar.get_width()/2,bar.get_height()+.6),ha="center")
    ax.set_xticks(x,names)
    ax.set_ylim(0,31)
    ax.set_ylabel("Labeled IDoFT instances (n = 27)")
    ax.legend()
    ax.set_title("Actual JUnit 4 parameterization: 27 candidate instance identities")
    ax.grid(axis="y",alpha=.15)
    fig.text(.01,.015,"Source-and-runtime candidate matches, not independent identity adjudication or historical CI. Test outcomes: 120 before, 120 after.",fontsize=8,color="#555")
    fig.tight_layout(rect=(0,.05,1,1))
    for ext in ("png","pdf"):
        fig.savefig(output_dir/f"junit_parameter_instance_recovery.{ext}",bbox_inches="tight")
    plt.close(fig)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--results",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    draw(a.results,a.output)
    print("Saved 4 figures in PNG/PDF")


if __name__=="__main__":
    main()
