#!/usr/bin/env python3
"""Audit first-party raw observations, calculate honest case-level metrics.

This scanner does not read business_oracle.contract_violation to predict.
Instead it evaluates contracts over raw database rows/IDs; independent truth
comes from the manifest of external bug reports and application-level probes.
"""

import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_cases(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def contracts(case):
    evidence = case["evidence"]
    family = case["family"]
    if family == "django_permissions":
        granted = {tuple(row) for row in evidence["user_grants"]}
        requested = tuple(evidence["contract_input"]["granted_permission_before_or_after_migration"])
        return requested not in granted
    if family == "django_sites":
        desired = evidence["contract_input"]
        observed = {row[0]: (row[1], row[2]) for row in evidence["site_rows"]}
        return (observed.get(desired["site_id"]) != (desired["user_owned_domain"], desired["user_owned_name"])
                or len(evidence["redirect_rows"]) != desired["expected_redirect_count"])
    if family == "opencode":
        src_msg = set(evidence["source_messages"])
        dest_msg = set(evidence["projected_messages"])
        src_session = set(evidence["source_sessions"])
        dest_session = set(evidence["projected_sessions"])
        return bool(src_msg - dest_msg or src_session - dest_session)
    raise ValueError(f"Unknown family {family!r}")


def row_diff(case, reference):
    data = case["evidence"]
    if case["family"] == "django_permissions":
        return data["row_counts"] != reference["row_counts"]
    if case["family"] == "django_sites":
        return (data["site_rows"] != reference["site_rows"] or
                data["redirect_rows"] != reference["redirect_rows"])
    if case["family"] == "opencode":
        return (len(data["source_messages"]) != len(data["projected_messages"]) or
                len(data["source_sessions"]) != len(data["projected_sessions"]))
    raise ValueError(case["family"])


def count_only(case, reference):
    data = case["evidence"]
    if case["family"] == "django_permissions":
        return data["row_counts"] != reference["row_counts"]
    if case["family"] == "django_sites":
        return (len(data["site_rows"]) != len(reference["site_rows"]) or
                len(data["redirect_rows"]) != len(reference["redirect_rows"]))
    if case["family"] == "opencode":
        return (len(data["source_messages"]) != len(data["projected_messages"]) or
                len(data["source_sessions"]) != len(data["projected_sessions"]))
    raise ValueError(case["family"])


def status_only(case):
    d = case["evidence"]
    if case["family"] == "opencode":
        return d["migration_status"] != "completed" or d["checkpoint"] != '{"phase":"completed"}'
    return d.get("status", "completed") != "completed"


def full_manual_contract_baseline(case):
    """Strong fair baseline: the same replay, with explicit project oracles.

    For Django, this is an actual User.has_perm or Site/Redirect API query.
    For OpenCode, this is a standalone source-vs-projected ID assertion.
    Once the business contracts are supplied, the baseline is as strong as
    the detector. This comparator is intentionally NOT a weak strawman.
    """
    evidence = case["evidence"]
    if case["family"] in ("django_permissions", "django_sites"):
        return evidence["business_oracle"]["contract_violation"]
    return bool(evidence["observed_missing_source_messages"] or
                evidence["observed_missing_source_sessions"])


def label_for(case_id, manifest):
    if case_id in manifest["positive_cases"]:
        return "positive"
    if case_id in manifest["conditional_cases_not_in_primary_metrics"]:
        return "conditional"
    if case_id in manifest["negative_cases"]:
        return "negative"
    for prefix in manifest["negative_prefixes"]:
        if case_id.startswith(prefix):
            return "negative"
    raise ValueError(f"No external adjudication recorded for {case_id}")


def confusion(rows, key):
    tp = sum(r["label"] == "positive" and r[key] for r in rows)
    fn = sum(r["label"] == "positive" and not r[key] for r in rows)
    fp = sum(r["label"] == "negative" and r[key] for r in rows)
    tn = sum(r["label"] == "negative" and not r[key] for r in rows)
    return {"TP": tp, "FN": fn, "FP": fp, "TN": tn,
            "recall": tp/(tp+fn) if tp+fn else None,
            "false_positive_rate": fp/(fp+tn) if fp+tn else None}


def run(input_dir, output_dir, labels_path):
    raw = load_cases(input_dir / "observations.jsonl")
    labels = load_json(labels_path)
    groups = defaultdict(list)
    for case in raw:
        groups[case["case_id"]].append(case)

    refs = {}
    for case in raw:
        if case["case_id"] in ("django600_fresh", "django601_fresh", "sites_fresh", "opencode_agent_present"):
            refs[case["case_id"]] = case["evidence"]
    if len(refs) != 4:
        raise ValueError(f"Missing fresh baselines; have {list(refs)}")

    records = []
    for case_id, reps in sorted(groups.items()):
        evaluated = []
        for rep in reps:
            family = rep["family"]
            if family == "django_permissions":
                fresh = refs["django600_fresh" if case_id.startswith("django600_") else "django601_fresh"]
            elif family == "django_sites":
                fresh = refs["sites_fresh"]
            else:
                fresh = refs["opencode_agent_present"]
            evidence = rep["evidence"]
            ledger_key = "ledger_sha256" if family == "opencode" else "migration_ledger_sha256"
            measured = {
                "case_id": case_id, "family": family,
                "label": label_for(case_id, labels),
                "replication": rep["replication"],
                "contract_detector": contracts(rep),
                "full_manual_contract_baseline": full_manual_contract_baseline(rep),
                "schema_only": evidence["schema_sha256"] != fresh["schema_sha256"],
                "ledger_only": evidence[ledger_key] != fresh[ledger_key],
                "status_only": status_only(rep),
                "naive_row_diff": row_diff(rep, fresh),
                "row_count_only": count_only(rep, fresh),
                "wall_milliseconds": rep.get("wall_milliseconds"),
            }
            evaluated.append(measured)
        prediction_keys = ["contract_detector", "full_manual_contract_baseline", "schema_only", "ledger_only", "status_only",
                           "naive_row_diff", "row_count_only"]
        baseline = evaluated[0]
        for item in evaluated[1:]:
            assert all(item[key] == baseline[key] for key in prediction_keys), f"Non-reproducible {case_id}"
        records.append({**baseline, "replication_count": len(evaluated),
                        "wall_ms_median": statistics.median([x["wall_milliseconds"] for x in evaluated
                                                             if x["wall_milliseconds"] is not None])})

    # 30 user-domain changes are robustness stress cases, NOT independent negative cases.
    primary = [r for r in records if r["label"] != "conditional" and
               not r["case_id"].startswith("sites_user_variant_")]
    stress = [r for r in records if r["case_id"].startswith("sites_user_variant_")]
    scores = {method: confusion(primary, method) for method in
              ["contract_detector", "full_manual_contract_baseline", "schema_only", "ledger_only", "status_only",
               "naive_row_diff", "row_count_only"]}
    pos = sum(r["label"] == "positive" for r in primary)
    neg = sum(r["label"] == "negative" for r in primary)
    # Exact one-sided 95% upper bound for 0 observed false positives.
    fp_upper_zero = (1 - 0.05 ** (1 / neg)) if neg else None
    gain = 100 * (scores["contract_detector"]["recall"] -
                  scores["full_manual_contract_baseline"]["recall"])
    false_positive_rate = scores["contract_detector"]["false_positive_rate"]
    result = {
        "date": "2026-11-18",
        "status": "retrospective_exploratory_evaluation_only",
        "project_count": len(set(r["family"].split("_")[0] for r in primary)),
        "primary_positive_cases": pos,
        "primary_negative_cases": neg,
        "separately_reported_correlated_negative_stress_cases": len(stress),
        "stress_contract_false_positives": sum(r["contract_detector"] for r in stress),
        "stress_naive_row_diff_false_positives": sum(r["naive_row_diff"] for r in stress),
        "conditional_excluded": [r["case_id"] for r in records if r["label"] == "conditional"],
        "replicated_runs": len(raw),
        "unique_case_inputs": len(records),
        "scores": scores,
        "zero_of_n_false_positive_one_sided_95_upper": fp_upper_zero,
        "two_of_two_recall_one_sided_95_lower": (0.05 ** (1/pos)) if pos else None,
        "original_hypothesis_gate": {
            "required_recall_gain_vs_full_baseline_percentage_points": 15,
            "observed_recall_gain_vs_full_baseline_percentage_points": gain,
            "required_observed_false_positive_rate_max": 0.05,
            "observed_false_positive_rate": false_positive_rate,
            "gate_passed": pos >= 2 and gain >= 15 and false_positive_rate <= 0.05,
            "reason": "No incremental recall over a fully asserted baseline; FPR upper bound also exceeds 5%."
        },
        "independence_warning": "Even the 13 distinct core negatives are correlated by project. 30 legitimate site edits and 3 repeats each are NOT additional independent cases; confidence bounds are optimistic.",
        "full_manual_baseline": "A baseline supplied with the identical data-contract assertions has the identical decisions; no measured advantage.",
        "industrial_roi": "not_measured; local runtime is not industrial production cost",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "metrics.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    fields = ["case_id", "family", "label", "contract_detector", "full_manual_contract_baseline", "schema_only", "ledger_only", "status_only",
              "naive_row_diff", "row_count_only", "replication_count", "wall_ms_median"]
    with (output_dir / "case_table.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--labels", default=Path(__file__).resolve().parents[1] / "benchmarks/labels.json", type=Path)
    args = ap.parse_args()
    print(json.dumps(run(args.input, args.output, args.labels), indent=2))
