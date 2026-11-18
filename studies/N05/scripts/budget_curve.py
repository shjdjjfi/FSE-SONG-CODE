#!/usr/bin/env python3
"""Transparent exploratory early-budget search performance curves."""
import collections
import json
from pathlib import Path
import random
import statistics

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []


def bootstrap(rows, metric, n=10000):
    by = collections.defaultdict(list)
    for r in rows:
        by[r["group"]].append(r)
    units = list(by)
    if len(units) < 2:
        return None
    rng = random.Random(20271112)
    scores = []
    for _ in range(n):
        cur = [r for u in (rng.choice(units) for _ in units) for r in by[u]]
        scores.append(statistics.mean(r[metric] for r in cur))
    scores.sort()
    return [round(scores[int(.025*n)],4), round(scores[int(.975*n)-1],4)]


def main():
    reports = {}
    independent_repos = None
    p = ROOT / "prospective/results/independent_validation.json"
    if p.exists():
        independent_repos = json.loads(p.read_text())["source_repository_by_crate"]
    for cohort in (".", "holdout", "prospective"):
        d = ROOT / cohort
        original = load(d / "results/search.jsonl")
        v2 = {x["id"]: x["pathaware"] for x in load(d / "results/pathaware.jsonl")}
        diagnostics = {x["id"]: x["strong_baseline"] for x in load(d / "results/diagnostic.jsonl")}
        rows = []
        for r in original:
            record = {"id": r["id"], "crate": r["crate"],
                      "group": independent_repos.get(r["crate"], r["crate"]) if cohort == "prospective" and independent_repos else r["crate"]}
            for k in range(1, 9):
                g = float(r["guided"]["pass"] and r["guided"]["attempts"] <= k)
                rd = statistics.mean(float(x["pass"] and x["attempts"] <= k) for x in r["random"])
                record[f"gain_{k}"] = g-rd
                record[f"guided_{k}"] = g
                record[f"random_{k}"] = rd
                if r["id"] in v2:
                    z = v2[r["id"]]
                    record[f"pathaware_{k}"] = float(z["pass"] and z["attempts"] <= k)
                if r["id"] in diagnostics:
                    z = diagnostics[r["id"]]
                    record[f"diagnostic_{k}"] = float(z["pass"] and z["attempts"] <= k)
            record["auc_gain_1_to_8"] = statistics.mean(record[f"gain_{k}"] for k in range(1,9))
            rows.append(record)
        plot = []
        for k in range(1,9):
            if rows:
                plot.append({"budget": k,
                             "guided_success": round(statistics.mean(r[f"guided_{k}"] for r in rows),4),
                             "random_success": round(statistics.mean(r[f"random_{k}"] for r in rows),4),
                             "gain": round(statistics.mean(r[f"gain_{k}"] for r in rows),4),
                             "gain_project_cluster_ci": bootstrap(rows,f"gain_{k}"),
                             "pathaware_success": round(statistics.mean(r[f"pathaware_{k}"] for r in rows),4)
                             if all(f"pathaware_{k}" in r for r in rows) else None,
                             "diagnostic_success": round(statistics.mean(r[f"diagnostic_{k}"] for r in rows),4)
                             if all(f"diagnostic_{k}" in r for r in rows) else None})
        reports[cohort] = {"n_searched":len(rows),"n_clusters":len({x["group"] for x in rows}),
                           "preregistered_primary":False,"exploratory_budget_curve":plot,
                           "mean_auc_guided_minus_random": round(statistics.mean(r["auc_gain_1_to_8"] for r in rows),4) if rows else None,
                           "auc_cluster_ci":bootstrap(rows,"auc_gain_1_to_8")}
    dest = ROOT / "paper/BUDGET_CURVE_EXPLORATORY.json"
    dest.write_text(json.dumps(reports,indent=2)+"\n")
    for name, data in reports.items():
        print(name, data["n_searched"], [(x["budget"],x["guided_success"],x["random_success"]) for x in data["exploratory_budget_curve"]])


if __name__ == "__main__":
    main()
