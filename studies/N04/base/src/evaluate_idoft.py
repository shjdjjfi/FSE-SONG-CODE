"""Named baselines, ablations, and grouped inference on the IDoFT snapshot.

Important: source-derived successor FQNs are not independent human labels.
The independent IDoFT status *MovedOrRenamed vs Deleted* is analyzed on its
own; we report mapping-to-FQN results only on the well-supported subset.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import random
import statistics


ARMS = (
    "exact_node_id", "git_path_same_method", "name_similarity",
    "exact_body", "name_and_context", "guarded_lineage",
    "ablation_no_body", "ablation_no_group_guard",
)


def method_name(full: str) -> str:
    return full.rsplit(".", 1)[-1]


def select_one(case: dict, arm: str) -> str | None:
    c = case["candidates"]
    old_name = method_name(case["old_id"])
    if arm == "exact_node_id":
        # All extracted cases have lost their original fully qualified ID.
        return next((x["target"] for x in c if x["target"] == case["old_id"]), None)
    if arm == "git_path_same_method":
        candidates = [x for x in c if x["file_rename"] and
                      method_name(x["target"]) == old_name]
        return candidates[0]["target"] if len(candidates) == 1 else None
    if arm == "exact_body":
        candidates = [x for x in c if x["body_equal"]]
        return candidates[0]["target"] if len(candidates) == 1 else None
    if arm in ("name_similarity", "ablation_no_body"):
        # Name-based baseline intentionally has no semantic-change guard.
        candidates = sorted(c, key=lambda x:(-x["name_similarity"],x["target"]))
        return candidates[0]["target"] if candidates and candidates[0]["name_similarity"] >= .65 else None
    if arm == "name_and_context":
        candidates = [x for x in c if method_name(x["target"]) == old_name and
                      (x["file_rename"] or x["body_similarity"] >= .30)]
        return candidates[0]["target"] if len(candidates) == 1 else None
    if arm in ("guarded_lineage", "ablation_no_group_guard"):
        exact = [x for x in c if x["body_equal"]]
        if len(exact) == 1:
            return exact[0]["target"]
        exact_name = [x for x in c if method_name(x["target"]) == old_name
                      and x["body_similarity"] >= .30 and
                      (x["file_rename"] or x["assertion_similarity"] >= .0)]
        if len(exact_name) == 1:
            return exact_name[0]["target"]
        # Abstain on high-scoring but unconfirmed semantic rewrites.  In
        # particular never treat a same-class body rewrite as a rename.
        return None
    raise ValueError(arm)


def evaluate(dataset: dict, *, seeds=(17,29,43), bootstrap=3000) -> dict:
    cases = dataset["cases"]
    rows = []
    for arm in ARMS:
        predictions = [select_one(x, arm) for x in cases]
        if arm == "guarded_lineage":
            # Graph constraint: old histories can never be attached to the
            # same *single instance* through multiple distinct old node IDs.
            grouped = Counter((x["event_id"],p) for x,p in zip(cases,predictions) if p)
            predictions = [None if p and grouped[(x["event_id"],p)] > 1 else p
                           for x,p in zip(cases,predictions)]
        for case, prediction in zip(cases, predictions):
            truth = case["target"]
            label = case["idoft_status"]
            is_group = case["many_old_to_one_method"]
            source_guideline_conflict = bool(label == "Deleted" and any(
                c["body_equal"] and c["file_rename"] and
                method_name(c["target"]) == method_name(case["old_id"])
                for c in case["candidates"]))
            rows.append({"arm":arm,"event_id":case["event_id"],
                         "repository":case["repository"],
                         "status":label,"target_certainty":case["target_certainty"],
                         "case_id":case["old_id"],"gold_target":truth,
                         "group_ambiguous":is_group,"predicted_target":prediction,
                         "source_guideline_conflict":source_guideline_conflict,
                         "correct_single_target":bool(label=="MovedOrRenamed" and
                              truth and not is_group and prediction == truth),
                         "wrong_on_known_target":bool(label=="MovedOrRenamed" and
                              truth and not is_group and prediction and prediction != truth),
                         "unsafe_deleted_transfer":bool(label=="Deleted" and prediction),
                         "unsafe_group_transfer":bool(is_group and prediction),
                        })
    summary = []
    for arm in ARMS:
        arm_rows = [x for x in rows if x["arm"] == arm]
        eligible = [x for x in arm_rows if x["status"] == "MovedOrRenamed" and
                    x["gold_target"] and not x["group_ambiguous"]]
        negative = [x for x in arm_rows if x["status"] == "Deleted"]
        clean_negative = [x for x in negative if not x["source_guideline_conflict"]]
        group = [x for x in arm_rows if x["group_ambiguous"]]
        good = sum(x["correct_single_target"] for x in eligible)
        bad = sum(x["wrong_on_known_target"] for x in eligible)
        neg_bad = sum(x["unsafe_deleted_transfer"] for x in negative)
        clean_bad = sum(x["unsafe_deleted_transfer"] for x in clean_negative)
        group_bad = sum(x["unsafe_group_transfer"] for x in group)
        summary.append({"arm":arm,
                        "eligible_individual_positive":len(eligible),
                        "correct_individual_links":good,
                        "wrong_individual_links":bad,
                        "deleted_negative":len(negative),
                        "false_inheritance_on_deleted":neg_bad,
                        "source_guideline_conflicts":len(negative)-len(clean_negative),
                        "uncontested_deleted_negative":len(clean_negative),
                        "false_inheritance_on_uncontested_deleted":clean_bad,
                        "group_only_positive":len(group),
                        "unjustified_instance_links_on_groups":group_bad,
                        "positive_recall":round(good / len(eligible),4) if eligible else None,
                        "deleted_false_rate":round(neg_bad / len(negative),4) if negative else None,
                        "uncontested_deleted_false_rate":round(clean_bad/len(clean_negative),4)
                        if clean_negative else None,
                        "accepted":sum(bool(x["predicted_target"]) for x in arm_rows)})

    # Resample migrations, not individual test rows.  This prevents one
    # parameterization change with 27 tests from counting as 27 replications.
    intervals = {}
    by_arm = {arm:[r for r in rows if r["arm"]==arm] for arm in ARMS}
    for arm in ARMS:
        arm_rows = by_arm[arm]
        events = sorted(set(x["event_id"] for x in arm_rows))
        by_event = {key:[x for x in arm_rows if x["event_id"] == key] for key in events}
        if not events:
            continue
        sampled_recalls, sampled_false_rates = [], []
        for seed in seeds:
            rng = random.Random(seed)
            for _ in range(bootstrap):
                selection = [rng.choice(events) for _ in events]
                sample = [x for event in selection for x in by_event[event]]
                eligible = [x for x in sample if x["status"] == "MovedOrRenamed"
                            and x["gold_target"] and not x["group_ambiguous"]]
                negatives = [x for x in sample if x["status"] == "Deleted"]
                if eligible:
                    sampled_recalls.append(sum(x["correct_single_target"] for x in eligible) / len(eligible))
                if negatives:
                    sampled_false_rates.append(sum(x["unsafe_deleted_transfer"] for x in negatives) / len(negatives))
        def percentile(values, alpha):
            if not values:
                return None
            s = sorted(values)
            return round(s[min(len(s)-1,int((len(s)-1)*alpha))],4)
        intervals[arm] = {"recall_95_event_bootstrap":[percentile(sampled_recalls,.025),percentile(sampled_recalls,.975)],
                          "deleted_fpr_95_event_bootstrap":[percentile(sampled_false_rates,.025),percentile(sampled_false_rates,.975)],
                          "clusters":len(events),"bootstrap_seeds":list(seeds),
                          "draws_per_seed":bootstrap}

    return {"provenance":dataset["benchmark"],
            "caution":dataset["labeling_caution"],
            "statistics_unit":"unique migration/deletion commit (cluster bootstrap)",
            "summary":summary,"intervals":intervals,"predictions":rows}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--bootstrap",type=int,default=500)
    args=p.parse_args()
    d=evaluate(json.loads(args.input.read_text()),bootstrap=args.bootstrap)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(d,indent=2),encoding="utf-8")
    for row in d["summary"]:
        print(row)


if __name__=="__main__":
    main()
