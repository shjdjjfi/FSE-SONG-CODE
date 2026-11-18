"""Run N06's CPU-only, pre-specified controlled benchmark and audit outputs.

This program MUST NOT label synthetic episodes as measured Kubernetes data.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import random
import statistics
import sys
import time

import yaml

from simulator import (FAMILIES, POLICIES, PROFILES, SECONDS_PER_TICK,
                       SEEDS, evaluate, make_episode)

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "sources"
PRIMARY = ("instance", "service", "targetdown10", "service_grace", "targetdown10_grace", "owner_no_gap", "owner_lookback",
           "owner_relink", "owner_relink_v2", "owner_no_probe", "probe_latch")


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def check_upstream() -> dict:
    """Require the two exact original open-source rule durations to be present."""
    kube = (SOURCES / "kube_prometheus_general.libsonnet").read_text(encoding="utf-8")
    ftw = yaml.safe_load((SOURCES / "ftw_kubernetes_workloads.rules.yml").read_text(encoding="utf-8"))
    original = {r["alert"]: r for g in ftw["groups"] for r in g["rules"]}
    assert "alert: 'TargetDown'" in kube and "'for': '10m'" in kube
    assert original["KubePodNotReady"]["for"] == "15m"
    assert "pod" in original["KubePodNotReady"]["expr"]
    evidence = {
        "kube_prometheus": {
            "repository": "prometheus-operator/kube-prometheus",
            "commit": "d88939bfbe7ffa368a62dcc1ff477b1c19fa9674",
            "file": "jsonnet/kube-prometheus/components/mixin/alerts/general.libsonnet",
            "alert": "TargetDown", "for_minutes": 10,
            "warning": "Original expression is >10% down grouped by cluster/job/namespace/service; modeled contract differs.",
        },
        "fractal_techware": {
            "repository": "Fractal-Techware/prometheus-alert-rules",
            "commit": "3e61642f0dbbcab5a4fae1c830962fe8cd009c29",
            "file": "rules/kubernetes-workloads.rules.yml",
            "alert": "KubePodNotReady", "for_minutes": 15,
            "warning": "Original expression targets individual pod readiness; modeled contract is owner/service outage.",
        },
    }
    evidence["local_sha256"] = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCES.iterdir() if p.is_file()
    }
    return evidence


def aggregate(rows: list[dict], *, key_name: str, key_value: str) -> list[dict]:
    results: list[dict] = []
    for name in POLICIES:
        records = [x for x in rows if x["policy"] == name]
        pos = [x for x in records if x["oracle_positive"]]
        neg = [x for x in records if not x["oracle_positive"]]
        delays = [x["delay_after_oracle_minutes"] for x in pos
                  if x["delay_after_oracle_minutes"] is not None]
        observed_minutes = sum(x["total_ticks"] * SECONDS_PER_TICK / 60 for x in records)
        results.append({
            key_name: key_value,
            "policy": name,
            "episodes": len(records),
            "positive": len(pos),
            "negative": len(neg),
            "recall": round(sum(x["any_correct_page"] for x in pos) / len(pos), 6) if pos else None,
            "miss_rate": round(sum(x["miss"] for x in pos) / len(pos), 6) if pos else None,
            "false_page_episode_rate_negative": round(sum(x["any_false_page"] for x in neg) / len(neg), 6) if neg else None,
            "false_pages_per_100h": round(sum(x["false_page_events"] for x in records) *
                                          (100 * 60) / observed_minutes, 5) if observed_minutes else None,
            "false_firing_minutes_per_100h": round(sum(x["false_firing_minutes"] for x in records) *
                                                  (100 * 60) / observed_minutes, 4) if observed_minutes else None,
            "median_delay_minutes_observed_TP": round(statistics.median(delays), 4) if delays else None,
            "mean_delay_minutes_observed_TP": round(statistics.mean(delays), 4) if delays else None,
        })
    return results


def compare_pairs(rows: list[dict], repetitions: int = 500) -> list[dict]:
    """Stratified paired MC CI; never interpretable as field-project CI."""
    by_episode: dict[str, dict[str, dict]] = defaultdict(dict)
    for row in rows:
        by_episode[row["episode_id"]][row["policy"]] = row
    rng = random.Random(9001)
    result: list[dict] = []
    for profile in ("all_profiles", *PROFILES):
        for baseline in ("service_grace", "targetdown10_grace", "owner_lookback", "probe_latch", "owner_no_gap"):
            strata: dict[tuple[str, int, str], list[dict]] = defaultdict(list)
            for record in by_episode.values():
                row = record["owner_relink"]
                if profile != "all_profiles" and row["profile"] != profile:
                    continue
                strata[(row["family"], row["seed"], row["profile"])].append(record)
            base_metrics = []
            for stratum in strata.values():
                for pair in stratum:
                    a, b = pair["owner_relink"], pair[baseline]
                    base_metrics.append((a, b))
            for metric, valid in (
                ("miss", lambda a: a["oracle_positive"]),
                ("any_false_page", lambda a: not a["oracle_positive"]),
                ("false_firing_minutes", lambda a: True),
            ):
                deltas = [float(a[metric]) - float(b[metric]) for a, b in base_metrics if valid(a)]
                samples: list[float] = []
                if not deltas:
                    continue
                for _ in range(repetitions):
                    values = []
                    for stratum in strata.values():
                        viable = [pair for pair in stratum if valid(pair["owner_relink"])]
                        if not viable:
                            continue
                        for _sample in range(len(viable)):
                            chosen = rng.choice(viable)
                            values.append(float(chosen["owner_relink"][metric]) -
                                          float(chosen[baseline][metric]))
                    samples.append(statistics.mean(values))
                samples.sort()
                result.append({
                    "profile": profile,
                    "method_minus": baseline,
                    "metric": metric,
                    "paired_n": len(deltas),
                    "point_estimate": round(statistics.mean(deltas), 5),
                    "mc_bootstrap_low_95": round(samples[round(0.025 * (repetitions - 1))], 5),
                    "mc_bootstrap_high_95": round(samples[round(0.975 * (repetitions - 1))], 5),
                    "inference_scope": "synthetic-scenario Monte Carlo conditional on family/seed (NOT field CI)",
                })
    return result


def make_figures(summary: list[dict], family: list[dict], directory: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        return
    directory.mkdir(parents=True, exist_ok=True)
    overall = [r for r in summary if r["profile"] == "all_profiles"]
    names = [r["policy"] for r in overall]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.3, 4.5), constrained_layout=True)
    ax1.barh(names[::-1], [r["recall"] for r in overall[::-1]], color="#247d93")
    ax1.set(xlabel="Detection recall across synthetic positive episodes", xlim=(0, 1.02))
    ax2.barh(names[::-1], [r["false_page_episode_rate_negative"] for r in overall[::-1]], color="#cc643b")
    ax2.set(xlabel="False-page episode rate across synthetic negatives", xlim=(0, 1.02))
    fig.suptitle("N06 controlled mechanism benchmark — NOT production measurements")
    fig.savefig(directory / "01_main_comparison.png", dpi=190)
    plt.close(fig)

    families = list(FAMILIES)
    choices = ("instance", "service_grace", "owner_lookback", "owner_relink", "owner_relink_v2", "probe_latch")
    matrix = np.full((len(choices), len(families)), np.nan)
    for a, name in enumerate(choices):
        for b, fam in enumerate(families):
            row = next((r for r in family if r["family"] == fam and r["policy"] == name), None)
            if row and row["recall"] is not None:
                matrix[a, b] = row["recall"]
    fig, ax = plt.subplots(figsize=(13.2, 3.8), constrained_layout=True)
    display = ax.imshow(matrix, aspect="auto", interpolation="nearest", vmin=0, vmax=1, cmap="viridis")
    fig.colorbar(display, ax=ax, label="Positive episode recall")
    ax.set(yticks=range(len(choices)), yticklabels=choices,
           xticks=range(len(families)), xticklabels=families)
    ax.tick_params(axis="x", labelrotation=48)
    fig.suptitle("Per-family sensitivity of alert continuity (non-positive families appear blank)")
    fig.savefig(directory / "02_family_recall.png", dpi=190)
    plt.close(fig)


def make_table(rows: list[dict], target: Path) -> None:
    with target.open("w", encoding="utf-8") as handle:
        handle.write("# Table 1. Controlled simulations; NOT measured field performance\n\n")
        handle.write("| Policy | Recall (positive) | False-page rate (negative) | False pages/100 simulated h | Delay among detected (min) |\n")
        handle.write("|---|---:|---:|---:|---:|\n")
        for r in rows:
            if r["profile"] != "all_profiles":
                continue
            delay = str(r["median_delay_minutes_observed_TP"]) if r["median_delay_minutes_observed_TP"] is not None else "—"
            handle.write(f"| {r['policy']} | {r['recall']:.3f} | {r['false_page_episode_rate_negative']:.3f} | "
                         f"{r['false_pages_per_100h']:.2f} | {delay} |\n")


def assess_gate(summary: list[dict], *, samples: int) -> dict:
    overall = {row["policy"]: row for row in summary if row["profile"] == "all_profiles"}
    candidate = overall["owner_relink"]
    baselines = (overall["service_grace"], overall["targetdown10_grace"], overall["owner_lookback"], overall["probe_latch"])
    dominated = []
    for b in baselines:
        if (b["recall"] >= candidate["recall"] and
                b["false_page_episode_rate_negative"] <= candidate["false_page_episode_rate_negative"] and
                (b["recall"] > candidate["recall"] or
                 b["false_page_episode_rate_negative"] < candidate["false_page_episode_rate_negative"])):
            dominated.append(b["policy"])
    tied = [b["policy"] for b in baselines
            if (b["recall"] == candidate["recall"] and
                b["false_page_episode_rate_negative"] == candidate["false_page_episode_rate_negative"])]
    # This is a fail-closed publication gate: no field data and no real promtool
    # evaluation means the hypothesis is NOT confirmed regardless of MC scores.
    return {
        "verdict": "NOT_SUBMISSION_READY",
        "reason": "No independent real rollout+probe trace; no executable native promtool evaluation.",
        "synthetic_candidate_pareto_dominated_by": dominated,
        "synthetic_candidate_tied_with": tied,
        "real_outage_trace_count": 0,
        "independent_real_system_count": 0,
        "upstream_rule_repositories": 2,
        "native_promtool_executions": 0,
        "synthetic_episodes": samples,
        "pre_registered_engineering_gate": {
            "heldout_first_page_improvement_at_least_minutes": 0.25,
            "healthy_rollout_false_pages_no_increase": True,
            "two_independent_systems": True,
            "status": "NOT_EVALUABLE_WITH_SYNTHETIC_DATA",
        },
    }


def run(replicates: int, *, output: Path, seeds: tuple[int, ...] = SEEDS) -> None:
    if not 1 <= replicates <= 500:
        raise ValueError("replicates must be 1..500")
    output.mkdir(parents=True, exist_ok=True)
    (output / "raw").mkdir(exist_ok=True)
    sources = check_upstream()
    began = time.perf_counter()
    rows: list[dict] = []
    episodes = 0
    trace_file = output / "raw" / "synthetic_traces.jsonl.gz"
    with gzip.open(trace_file, "wt", encoding="utf-8", compresslevel=6) as handle:
        for profile in PROFILES:
            for family in FAMILIES:
                for seed in seeds:
                    for replicate in range(replicates):
                        episode = make_episode(profile, family, seed, replicate)
                        handle.write(json.dumps(episode.to_record(), separators=(",", ":")) + "\n")
                        rows.extend(evaluate(episode))
                        episodes += 1

    write_csv(output / "raw" / "paired_policy_results.csv", rows)
    summary = []
    for profile in ("all_profiles", *PROFILES):
        selected = [r for r in rows if profile == "all_profiles" or r["profile"] == profile]
        summary.extend(aggregate(selected, key_name="profile", key_value=profile))
    family_rows = []
    for family in FAMILIES:
        family_rows.extend(aggregate([r for r in rows if r["family"] == family],
                                     key_name="family", key_value=family))
    seed_rows = []
    for seed in seeds:
        seed_rows.extend(aggregate([r for r in rows if r["seed"] == seed],
                                   key_name="seed", key_value=str(seed)))
    write_csv(output / "summary.csv", summary)
    write_csv(output / "family_results.csv", family_rows)
    write_csv(output / "seed_results.csv", seed_rows)
    pairs = compare_pairs(rows, repetitions=300 if replicates < 20 else 600)
    write_csv(output / "paired_mc_intervals.csv", pairs)

    # Frozen sensitivity: only 1/5 of each cell, same generation settings;
    # small-sample estimates are explicitly labeled in the output.
    sensitive: list[dict] = []
    for grace in (0, 2, 4, 6, 8, 12):
        sample: list[dict] = []
        for profile in PROFILES:
            for family in FAMILIES:
                for seed in seeds:
                    for rep in range(0, replicates, 5):
                        episode = make_episode(profile, family, seed, rep)
                        sample.extend(evaluate(episode, grace=grace,
                                               selected=("service_grace", "targetdown10_grace", "owner_lookback", "owner_relink", "owner_no_probe")))
        for name in ("service_grace", "targetdown10_grace", "owner_lookback", "owner_relink", "owner_no_probe"):
            sub = [x for x in sample if x["policy"] == name]
            pos = [x for x in sub if x["oracle_positive"]]
            neg = [x for x in sub if not x["oracle_positive"]]
            sensitive.append({
                "grace_ticks": grace,
                "grace_seconds": grace * SECONDS_PER_TICK,
                "policy": name,
                "episodes": len(sub),
                "positive_recall": round(sum(x["any_correct_page"] for x in pos) / len(pos), 5) if pos else None,
                "negative_false_page_rate": round(sum(x["any_false_page"] for x in neg) / len(neg), 5) if neg else None,
                "sampling": "every fifth synthetic replicate; not independent field data",
            })
    write_csv(output / "grace_sensitivity.csv", sensitive)

    (output / "source_evidence.json").write_text(json.dumps(sources, indent=2), encoding="utf-8")
    gate = assess_gate(summary, samples=episodes)
    (output / "submission_gate.json").write_text(json.dumps(gate, indent=2), encoding="utf-8")
    make_figures(summary, family_rows, output / "figures")
    make_table(summary, output / "TABLE_1.md")
    meta = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "benchmark_version": "N06-controlled-v1",
        "episodes": episodes,
        "paired_policy_episode_rows": len(rows),
        "seeds": list(seeds),
        "replicates_per_profile_family_seed": replicates,
        "families": list(FAMILIES),
        "profiles_hold_ticks": PROFILES,
        "policies": list(POLICIES),
        "seconds_per_tick": SECONDS_PER_TICK,
        "default_relink_grace_ticks": 6,
        "blackbox_probe_missing_rate": 0.12,
        "blackbox_probe_noise": 0.0,
        "data_origin": "entirely synthetic and algorithmically generated",
        "production_data_used": False,
        "native_prometheus_engine_used": False,
        "platform": sys.platform,
        "python_version": sys.version,
        "runtime_seconds": round(time.perf_counter() - began, 4),
    }
    (output / "run_manifest.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps({"episodes": episodes, "paired_rows": len(rows),
                      "candidate": next(x for x in summary if x["profile"] == "all_profiles" and
                                        x["policy"] == "owner_relink"),
                      "gate": gate["verdict"], "runtime_seconds": meta["runtime_seconds"]}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replicates", type=int, default=30)
    parser.add_argument("--output", type=Path, default=ROOT / "results")
    parser.add_argument("--seeds", default=",".join(str(x) for x in SEEDS),
                        help="Comma-separated seeds; do not tune after holdout evaluation")
    args = parser.parse_args()
    selected_seeds = tuple(int(x) for x in args.seeds.split(","))
    run(args.replicates, output=args.output.resolve(), seeds=selected_seeds)
