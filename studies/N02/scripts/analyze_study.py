#!/usr/bin/env python3
"""Paired, seed-controlled CPU-only evaluation of N02 exploratory detectors."""
from __future__ import annotations

from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path
import random
import statistics

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent.parent
SEEDS = (17, 29, 43)
BUDGETS = (1, 2, 3, 4)
METHODS = (
    "random", "manifest_diff", "missing_new_default", "effect_without_literals",
    "literal_only", "counterfactual", "migration_docs",
)


def stable_tie(seed: int, family: str, case_id: str) -> float:
    data = f"{seed}/{family}/{case_id}".encode()
    return int.from_bytes(hashlib.sha256(data).digest()[:8], "big") / 2**64


def score(row: dict, method: str) -> float:
    if method == "random":
        return 1.0
    if method == "manifest_diff":
        return float(row["score_manifest_diff"])
    if method == "missing_new_default":
        return float(row["score_missing_in_new_defaults"])
    if method == "effect_without_literals":
        return max(0.0, float(row["score_counterfactual"])
                   - 60.0 * bool(row["vanished_operator_literals"]))
    if method == "literal_only":
        return float(60.0 * bool(row["vanished_operator_literals"]))
    if method == "counterfactual":
        return float(row["score_counterfactual"])
    if method == "migration_docs":
        # This uses MANUALLY ANNOTATED official release-note matches.  It is
        # not an independently implemented helm-diff+documentation tool, and
        # its decisions receive human migration knowledge as additional input.
        return float(row["documented_actionable_migration"])
    raise ValueError(method)


def cutoff(method: str) -> float:
    if method in ("counterfactual", "effect_without_literals"):
        return 5.0
    if method in ("missing_new_default", "literal_only", "migration_docs"):
        return 0.5
    return 0.0


def decide(rows: list[dict], seed: int, budget: int, method: str) -> list[dict]:
    ordered = sorted(
        rows, key=lambda r: (-score(r, method), stable_tie(seed, r["family"], r["id"]))
    )
    return [r for r in ordered if score(r, method) >= cutoff(method)
            and (method not in ("random", "manifest_diff") or score(r,method)>0)][:budget]


def bootstrap_interval(family_stats: list[dict], method: str, budget: int,
                       *, resamples: int = 5000) -> list[float]:
    rng = random.Random(20261115 + 10*budget + METHODS.index(method))
    positives = []
    negatives = []
    family_stats = [r for r in family_stats if r["method"] == method and r["budget"] == budget]
    for _ in range(resamples):
        sample = [family_stats[rng.randrange(len(family_stats))]
                  for _ in family_stats]
        denom_p = sum(r["npositive"] for r in sample)
        denom_n = sum(r["nnegative"] for r in sample)
        if denom_p:
            positives.append(sum(r["tp"] for r in sample)/denom_p)
        if denom_n:
            negatives.append(sum(r["fp"] for r in sample)/denom_n)
    return [
        round(float(np.percentile(positives, 2.5)), 5) if positives else None,
        round(float(np.percentile(positives, 97.5)), 5) if positives else None,
        round(float(np.percentile(negatives, 2.5)), 5) if negatives else None,
        round(float(np.percentile(negatives, 97.5)), 5) if negatives else None,
    ]


def paired_delta_interval(fam_aggs: list[dict], budget: int, alternative: str,
                          reps: int=5000) -> list[float]:
    target = {x["family"]:x for x in fam_aggs
              if x["method"]=="counterfactual" and x["budget"]==budget}
    comparator = {x["family"]:x for x in fam_aggs
                  if x["method"]==alternative and x["budget"]==budget}
    families=sorted(target)
    rng=random.Random(7171+budget+METHODS.index(alternative))
    results=[]
    for _ in range(reps):
        sample=[families[rng.randrange(len(families))] for _ in families]
        positives=sum(target[f]["npositive"] for f in sample)
        if not positives:
            continue
        delta=sum(target[f]["tp"]-comparator[f]["tp"] for f in sample)/positives
        results.append(100*delta)
    return [round(float(np.percentile(results,q)),3) for q in (2.5,97.5)]


def main() -> None:
    rows = [json.loads(line) for line in
            (ROOT/"results/case_results.jsonl").read_text().splitlines() if line.strip()]
    families = sorted({r["family"] for r in rows})
    byfamily = {family: [r for r in rows if r["family"] == family] for family in families}
    positives = sum(r["label"]=="positive" for r in rows)
    negatives = len(rows)-positives
    assert len(rows)==27 and positives==8 and negatives==19
    assert len(families)==5
    raw = []
    fam_aggs = []
    overall = []
    for method in METHODS:
        for budget in BUDGETS:
            for family in families:
                examples = byfamily[family]
                np_ = sum(r["label"]=="positive" for r in examples)
                nn_ = len(examples)-np_
                chosen_records = []
                for seed in SEEDS:
                    chosen = decide(examples, seed, budget, method)
                    chosen_ids = {r["id"] for r in chosen}
                    chosen_records.append({
                        "tp": sum(r["label"]=="positive" for r in chosen),
                        "fp": sum(r["label"]=="negative" for r in chosen),
                    })
                    for r in examples:
                        raw.append({
                            "method": method, "budget": budget, "seed": seed,
                            "family": family, "id": r["id"],
                            "positive": int(r["label"]=="positive"),
                            "score": round(score(r,method), 7),
                            "selected": int(r["id"] in chosen_ids),
                        })
                fam_aggs.append({
                    "method": method, "budget": budget, "family": family,
                    "npositive": np_, "nnegative": nn_,
                    "tp": statistics.mean(q["tp"] for q in chosen_records),
                    "fp": statistics.mean(q["fp"] for q in chosen_records),
                })
            data = [r for r in fam_aggs if r["method"]==method and r["budget"]==budget]
            tp = sum(r["tp"] for r in data)
            fp = sum(r["fp"] for r in data)
            ci=bootstrap_interval(fam_aggs, method, budget)
            overall.append({
                "method": method, "budget": budget, "true_positives": round(tp, 4),
                "false_positives": round(fp, 4),
                "recall": round(tp/positives, 6),
                "false_positive_rate": round(fp/negatives, 6),
                "recall_cluster_bootstrap_95": ci[:2],
                "fpr_cluster_bootstrap_95": ci[2:],
                "unit": "human-reviewed chart-value scenario",
                "seeds": list(SEEDS),
            })
    with (ROOT/"results/rankings_seeded.csv").open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(raw[0]))
        writer.writeheader()
        writer.writerows(raw)

    thresholds=[]
    for method in METHODS:
        if method in ("random","manifest_diff"):
            continue
        selected=[r for r in rows if score(r,method) >= cutoff(method)]
        tp=sum(r["label"]=="positive" for r in selected)
        fp=sum(r["label"]=="negative" for r in selected)
        thresholds.append({
            "method":method,"selected":len(selected),
            "tp":tp,"fn":positives-tp,"fp":fp,"tn":negatives-fp,
            "recall":tp/positives,"fpr":fp/negatives,
            "threshold":cutoff(method)
        })
    def entry(method: str, budget: int) -> dict:
        return next(x for x in overall if x["method"]==method and x["budget"]==budget)
    improvement = [{
        "budget":budget,
        "counterfactual_minus_missing_default_recall_pp":
            round(100*(entry("counterfactual",budget)["recall"]-
                       entry("missing_new_default",budget)["recall"]),3),
        "vs_missing_default_cluster_bootstrap_delta_ci_pp":
            paired_delta_interval(fam_aggs,budget,"missing_new_default"),
        "counterfactual_minus_documentation_annotated_recall_pp":
            round(100*(entry("counterfactual",budget)["recall"]-
                       entry("migration_docs",budget)["recall"]),3),
        "vs_documentation_cluster_bootstrap_delta_ci_pp":
            paired_delta_interval(fam_aggs,budget,"migration_docs"),
        "counterfactual_minus_manifest_diff_recall_pp":
            round(100*(entry("counterfactual",budget)["recall"]-
                       entry("manifest_diff",budget)["recall"]),3),
    } for budget in BUDGETS]
    report = {
        "design": "exploratory, known migration case study; not independent deployment evidence",
        "family_count":len(families),"cases":len(rows),"positives":positives,
        "negatives":negatives,"seeds":list(SEEDS),"budget_per_family":list(BUDGETS),
        "bootstrap_clusters":"5 chart families, 5000 resamples; degenerate intervals reflect curated data only",
        "threshold_scores":thresholds,"rankings":overall,"contrasts":improvement,
        "limitations":[
            "labels selected and constructed from official upgrade documentation",
            "documentation-baseline annotation uses independent human source evidence; not a fully automated helm-diff tool",
            "budget is scenarios for human review, not real reviewer minutes",
            "same chart-family cases and tie-breaking seeds are not independent samples",
            "all primary effects are manifest/application-parser-level, not observed Kubernetes runtime failures",
            "no independently held-out chart family was available for a confirmatory conclusion"
        ],
    }
    (ROOT/"results/analysis_summary.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2)
    )
    print("THRESHOLDS")
    for r in thresholds:
        print(f"{r['method']:<27} TP {r['tp']}/8 FP {r['fp']}/19",flush=True)
    print("K=2 FAMILY REVIEW BUDGET")
    for m in METHODS:
        r=entry(m,2)
        print(f"{m:<27} recall={100*r['recall']:.2f}% fpr={100*r['false_positive_rate']:.2f}%",flush=True)

    # A compact set of paper-ready figures without suggesting population CIs.
    plt.rcParams.update({"font.size": 11, "font.family": "DejaVu Sans"})
    colors={"random":"#9AA3B2","manifest_diff":"#DC9957","missing_new_default":"#B66CC7",
            "counterfactual":"#247AB2","migration_docs":"#459B70"}
    labels={"random":"Random","manifest_diff":"Manifest diff magnitude",
            "missing_new_default":"Missing key in new values.yaml",
            "counterfactual":"Counterfactual intent detector",
            "migration_docs":"Explicit migration-note annotation"}
    fig,axes=plt.subplots(1,2,figsize=(13.5,5.5))
    for m in colors:
        points=[entry(m,k) for k in BUDGETS]
        axes[0].plot(BUDGETS,[100*x["recall"] for x in points],marker="o",
                     linewidth=2.2,label=labels[m],color=colors[m])
        axes[1].plot(BUDGETS,[100*x["false_positive_rate"] for x in points],
                     marker="o",linewidth=2.2,label=labels[m],color=colors[m])
    axes[0].set(title="Verified migration contract recall",ylabel="Recall (%)",
                xlabel="Review budget: up to K scenarios / family",ylim=(-2,102),xticks=BUDGETS)
    axes[1].set(title="Non-migration controls selected",ylabel="Selected false positives / 19 (%)",
                xlabel="Review budget: up to K scenarios / family",ylim=(-2,102),xticks=BUDGETS)
    for ax in axes:
        ax.grid(True,alpha=.25)
        ax.spines[["top","right"]].set_visible(False)
    legend_handles,legend_labels=axes[0].get_legend_handles_labels()
    fig.legend(legend_handles,legend_labels,loc="lower center",ncol=3,frameon=False,
               bbox_to_anchor=(.5,.005),fontsize=10)
    fig.suptitle("Curated Helm upgrade scenarios (n=27; not production outcomes)",
                 fontsize=13,y=.98)
    fig.tight_layout(rect=(0,.23,1,.91))
    fig.savefig(ROOT/"figures/figure1_budgeted_selection.png",dpi=180,bbox_inches="tight")
    plt.close(fig)

    positive_rows=[r for r in rows if r["label"]=="positive"]
    names=[r["id"] for r in positive_rows]
    vals=np.array([[
        r["lost_effect_positions"]/max(r["old_effect_positions"],1),
        float(bool(r["vanished_operator_literals"])),
        float(r["documented_actionable_migration"]),
    ] for r in positive_rows])
    fig,ax=plt.subplots(figsize=(9.5,5.0))
    im=ax.imshow(vals,cmap="YlOrBr",vmin=0,vmax=1,aspect="auto")
    ax.set_xticks(range(3),labels=[
        "Old effect lost", "Operator value lost", "Explicit migration note"
    ])
    ax.set_yticks(range(len(names)),labels=names)
    for i in range(len(names)):
        for j in range(3):
            shown=(f"{100*vals[i,j]:.0f}%" if j==0 else
                   ("Yes" if vals[i,j] else "No"))
            ax.text(j,i,shown,ha="center",va="center",fontsize=11,
                    color="white" if vals[i,j]>.63 else "#29323A",weight="medium")
    ax.set_title("Why eight observable configuration contracts were lost",
                 fontsize=13,pad=14)
    ax.tick_params(axis="both",length=0)
    fig.colorbar(im,ax=ax,label="Normalized evidence",shrink=.75)
    fig.tight_layout()
    fig.savefig(ROOT/"figures/figure2_effect_loss.png",dpi=180,bbox_inches="tight")
    plt.close(fig)
    print("ANALYSIS COMPLETE",flush=True)


if __name__=="__main__":
    main()
