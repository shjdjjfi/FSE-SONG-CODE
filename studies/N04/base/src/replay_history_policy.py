"""Replays a *hypothetical* fixed-threshold policy on real repeated test outcomes.

This experiment does not contain real quarantine actions or historical CI logs.
The policy is defined before inspection: >=5% failed outcomes across the last
five observed source revisions (inclusive of the source 'before' revision)
causes a quarantine suggestion.  It is deliberately not tuned on the outcomes.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path


def counts(value):
    if not value:
        return {"passed": 0, "failed": 0, "errored": 0, "skipped": 0}
    passed = sum(n for key, n in value.items() if key in ("passed", "pass", "success"))
    failed = sum(n for key, n in value.items() if key in ("failed", "failure", "error", "errored"))
    return {"passed": passed, "failed": failed,
            "errored": value.get("errored", 0), "skipped": value.get("skipped", 0)}


def replay(histories: dict, aligned: dict, gold: dict, *, lookback=5, threshold=.05):
    records = []
    for record in gold["labels"]:
        matched = []
        for key, project in histories["projects"].items():
            if project["repository"] != record["repository"]:
                continue
            view = aligned["evaluations"].get(key, {})
            if view.get("status") != "aligned":
                continue
            order = view["commits"]
            if record["before"] not in order or record["after"] not in order:
                continue
            old_i = order.index(record["before"])
            new_i = order.index(record["after"])
            if old_i >= new_i:
                continue
            by_sha = {x["hash"]: x for x in project["commits"]}
            history_ids = order[max(0, old_i - lookback + 1):old_i + 1]
            prior = [counts(by_sha[x]["tests"].get(record["old"])) for x in history_ids]
            total_prior = sum(x["passed"] + x["failed"] for x in prior)
            fail_prior = sum(x["failed"] for x in prior)
            observed_old_at_before = counts(by_sha[record["before"]]["tests"].get(record["old"]))
            post = counts(by_sha[record["after"]]["tests"].get(record["new"])) if record["new"] else None
            candidate = {
                "track":key,"independent_track":False,
                "n_history_source_revisions":len(history_ids),
                "pre_old_test_at_boundary":observed_old_at_before,
                "pre_history_failures":fail_prior,
                "pre_history_observations":total_prior,
                "old_history_flake_signal":bool(fail_prior > 0 and total_prior > fail_prior),
                "hypothetical_quarantine_from_old_history":bool(total_prior and fail_prior / total_prior >= threshold),
                "hypothetical_quarantine_from_exact_new_id":False,
                "new_test_at_boundary":post,
                "new_test_measured":bool(post and (post["passed"] + post["failed"])),
            }
            matched.append(candidate)
        for i, item in enumerate(matched):
            item["independent_track"] = i == 0
        records.append({"label":record,"observations":matched})
    unique = [item for r in records for item in r["observations"] if item["independent_track"]]
    positive = [r for r in records if r["label"]["decision"] == "transfer"]
    summary = {
        "gold_source_events":len(records),
        "gold_transfer_events":len(positive),
        "source_events_with_actual_pre_post_outcomes":sum(bool(r["observations"]) for r in records),
        "unique_evaluated_source_events":len(unique),
        "observed_old_flaky_before_boundary":sum(x["old_history_flake_signal"] for x in unique),
        "hypothetical_policy_decision_differences":sum(x["hypothetical_quarantine_from_old_history"] != x["hypothetical_quarantine_from_exact_new_id"] for x in unique),
        "unique_new_test_outcomes_observed":sum(x["new_test_measured"] for x in unique),
        "duplicate_track_records_excluded":sum(len(r["observations"]) for r in records)-len(unique),
    }
    return {
        "interpretation":"Offline replay of measured FTW test outcomes at manually audited source-identity boundaries; NOT real CI/quarantine policy evidence",
        "hypothetical_policy":{"lookback_source_revisions":lookback,"quarantine_failure_fraction_threshold":threshold,"threshold_pre_registered_here":True},
        "no_independent_quarantine_labels":True,
        "summary":summary,"records":records,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--histories",type=Path,required=True)
    p.add_argument("--aligned",type=Path,required=True)
    p.add_argument("--gold",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args = p.parse_args()
    d=replay(json.loads(args.histories.read_text()),json.loads(args.aligned.read_text()),json.loads(args.gold.read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(d,indent=2),encoding="utf-8")
    print(json.dumps(d["summary"],indent=2))
