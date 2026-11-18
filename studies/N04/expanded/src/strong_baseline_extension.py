"""Exploratory risk-calibrated conservative baselines for the frozen N04 corpus.

IMPORTANT: These rules were created after the original benchmark's results
were inspected. They are exploratory development comparisons, even with
leave-one-project-out calibration. No prospective superiority claim follows.
"""

from __future__ import annotations

import argparse
import collections
import csv
import difflib
import json
import math
from pathlib import Path

import n04_benchmark as b

METHODS = ("method_name", "name_body_tiebreak", "name_case_body_tiebreak",
           "guarded_fallback", "strict_guarded_fallback")


def candidate_score(old: b.Snippet, new: b.Snippet, method: str) -> float:
    if method == "method_name":
        return b.score(old, new, "method_name")
    seq = b.score(old, new, "source_similarity")
    oa, na = set(old.tokens), set(new.tokens)
    jac = len(oa & na) / len(oa | na) if oa | na else 0
    same = old.name == new.name
    canonical = bool(b.norm_name(old.name)) and b.norm_name(old.name) == b.norm_name(new.name)
    if method == "name_body_tiebreak":
        return 0.90 + .10 * seq if same else 0.0
    if method == "name_case_body_tiebreak":
        if same:
            return .90 + .10 * seq
        return .76 + .13 * seq if canonical else 0
    if method == "guarded_fallback":
        if same:
            return .89 + .10 * seq if seq >= .18 or jac >= .25 else .45 * seq
        if canonical and seq >= .45:
            return .79 + .16 * seq
        if seq >= .82 and jac >= .65:
            return .70 + .22 * seq
        return 0.0
    if method == "strict_guarded_fallback":
        if same:
            return .92 + .08 * seq if seq >= .38 or jac >= .4 else .35 * seq
        if canonical and seq >= .75 and jac >= .6:
            return .82 + .16 * seq
        if seq >= .91 and jac >= .83:
            return .73 + .19 * seq
        return 0.0
    raise ValueError(method)


def score_top(old: b.Snippet, candidates: list[b.Snippet], method: str):
    scored = sorted(((candidate_score(old, c, method), c.uid) for c in candidates), reverse=True)
    if not scored:
        return (0, 0, "")
    first = scored[0]
    second = scored[1][0] if len(scored) > 1 else 0.0
    return first[0], first[0] - second, first[1]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", type=Path, default=Path("data/TestMigrationsInPy/projects"))
    p.add_argument("--out", type=Path, default=Path("results/strong_baselines"))
    p.add_argument("--seeds", nargs="+", type=int, default=[17, 29, 43])
    a = p.parse_args()
    pairs, audit = b.load_pairs(a.dataset)
    allrows, thresholds = [], []
    for seed in a.seeds:
        examples = b.choose_candidates(pairs, seed, 12)
        predictions = {}
        for q in examples:
            old = q["old"]
            predictions[q["uid"]] = {m:{
                "present": score_top(old, q["present_candidates"], m),
                "absent": score_top(old, q["absent_candidates"], m)} for m in METHODS}
        for method in METHODS:
            rows, t = b.leave_one_project_out(examples, predictions, method)
            allrows.extend({"seed":seed, **row} for row in rows)
            thresholds.extend({"seed":seed, **row} for row in t)
        print("seed",seed,"completed",len(examples),"queries",flush=True)
    a.out.mkdir(parents=True, exist_ok=True)
    b.write_csv(a.out / "predictions.csv", allrows)
    b.write_csv(a.out / "thresholds.csv", thresholds)
    summary={}
    for method in METHODS:
        vals = [r for r in allrows if r["method"] == method]
        s=b.test_statistics(vals)
        s["by_project"] = {p: b.test_statistics([r for r in vals if r["project"] == p])
                            for p in sorted(set(r["project"] for r in vals))}
        summary[method]=s
    baseline="method_name"
    differences={m:b.bootstrap_project_difference(allrows,m,baseline) for m in METHODS if m!=baseline}
    out={"status":"exploratory, not prespecified or independent confirmation",
         "dataset_audit":audit["counts"],"seeds":a.seeds,"summary":summary,
         "paired_project_cluster_bootstrap_vs_name":differences,
         "limitations":["Rules developed after original N04 benchmark aggregate/project errors were inspected.",
                        "Calibration uses other projects, but retroactively chosen model families are still exploratory.",
                        "Target-absent candidate scenarios are controlled deletions, not observed CI outcomes.",
                        "This is neither published TestRefactoringMiner nor a direct comparison with its true implementation."]}
    (a.out/"results.json").write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps({k:{"recall":round(v["recovery_rate"],5),
                          "false":round(v["combined_false_transfer_rate"],5)}
                      for k,v in summary.items()},indent=2))


if __name__ == "__main__":
    main()
