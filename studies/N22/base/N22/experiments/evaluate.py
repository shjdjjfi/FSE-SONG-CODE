"""Conservative, issue-guided scoring and repeated local check timings.

The labels are explicitly enumerated and frozen in this file. The sample unit
is a REPLAY SCENARIO, not a distinct industrial defect or a random population
sample. Rates are DESCRIPTIVE only, because scenarios are clustered by project.
"""

from __future__ import annotations

import argparse
import json
import math
import platform
import sqlite3
import statistics
import time
from pathlib import Path

from pydantic import BaseModel, ValidationError


class Profile(BaseModel):
    id: str
    info: dict | None
    settings: dict | None


LABELS = {
    # label 1: source-proven defect behavior / meaningful application break;
    # label 0: legitimate safe difference or no data at risk;
    # label None: source semantics ambiguous and thus not silently relabeled.
    "openwebui:zero_users": 0,
    "openwebui:one_valid": 1,
    "openwebui:one_custom": 1,
    "openwebui:one_null": 0,
    "openwebui:one_empty": None,
    "drizzle:cascade_three": 1,
    "drizzle:cascade_one": 1,
    "drizzle:cascade_user_edit": 1,
    "drizzle:set_null_three": 1,
    "drizzle:cascade_zero": 0,
    "django:sites_staged": 0,
    "django:sites_staged_user": 0,
    "django:petter_checkpoint": 0,
}


def wilson(k: int, n: int, z: float = 1.959963984540054) -> list[float]:
    if n == 0:
        return [float("nan"), float("nan")]
    p = k / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    span = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [round(max(0, mid - span), 4), round(min(1, mid + span), 4)]


def trial_case(project: str, name: str, label: int | None, outcomes: dict) -> dict:
    if not outcomes["schema_and_ledger_equal"]:
        raise ValueError(f"Not a converged migration path: {project}:{name}")
    return {
        "id": f"{project}:{name}",
        "project": project,
        "label": label,
        "label_scope": (
            "ambiguous_not_scored" if label is None
            else "observed_issue_mechanism_or_legitimate_control"
        ),
        **outcomes,
    }


def assemble(results: Path) -> list[dict]:
    ow = json.loads((results / "openwebui/openwebui-observations.json").read_text())
    dr = json.loads((results / "drizzle/drizzle-observations.json").read_text())
    dj = json.loads((results / "django/django-observations.json").read_text())
    cases: list[dict] = []
    ow_rows = {x["id"]: x for x in ow["runs"]}
    for scenario in ("zero_users", "one_valid", "one_custom", "one_null", "one_empty"):
        bad = ow_rows[f"{scenario}__upstream"]
        good = ow_rows[f"{scenario}__reference_patch"]
        assert bad["success"] and good["success"]
        cases.append(trial_case(
            "openwebui", scenario, LABELS[f"openwebui:{scenario}"],
            {
                "schema_and_ledger_equal": (
                    bad["same_schema_as_reference"] and bad["same_ledger_as_reference"]
                ),
                "simple_schema_ledger_alert": False,
                "schema_ledger_rowcount_alert": not bad["same_row_count_as_reference"],
                "untyped_json_alert": not bad["generic_json_parse_success"],
                "raw_snapshot_diff_alert": bad["raw_users"] != good["raw_users"],
                "contract_alert": not bad["typed_pydantic_probe_success"],
                "source_file": f"openwebui/{bad['sqlite_file']}",
                "migrator_success": bad["success"],
            },
        ))
    dr_rows = {x["id"]: x for x in dr["runs"]}
    for scenario in (
        "cascade_three", "cascade_one", "cascade_user_edit",
        "set_null_three", "cascade_zero",
    ):
        bad = dr_rows[f"{scenario}__upstream"]
        good = dr_rows[f"{scenario}__reference_fk_before_begin"]
        assert bad["success"] and good["success"]
        cases.append(trial_case(
            "drizzle", scenario, LABELS[f"drizzle:{scenario}"],
            {
                "schema_and_ledger_equal": (
                    bad["same_schema_as_reference"] and bad["same_ledger_as_reference"]
                ),
                "simple_schema_ledger_alert": False,
                "schema_ledger_rowcount_alert": not bad["same_row_counts_as_reference"],
                "untyped_json_alert": False,
                "raw_snapshot_diff_alert": (
                    bad["child"] != good["child"] or bad["grandchild"] != good["grandchild"]
                ),
                "contract_alert": not bad["data_contract_preserved"],
                "source_file": f"drizzle/{bad['sqlite_file']}",
                "migrator_success": bad["success"],
            },
        ))
    sites = {x["scenario"]: x for x in dj["builtin_sites"]["observations"]}
    for scenario, label_id in (
        ("staged", "sites_staged"),
        ("staged-user-row", "sites_staged_user"),
    ):
        actual = sites[scenario]
        cases.append(trial_case(
            "django", label_id, LABELS[f"django:{label_id}"],
            {
                "schema_and_ledger_equal": (
                    actual["same_schema_as_fresh"] and actual["same_ledger_as_fresh"]
                ),
                "simple_schema_ledger_alert": False,
                "schema_ledger_rowcount_alert": False,
                "untyped_json_alert": False,
                "raw_snapshot_diff_alert": not actual["same_rows_as_fresh"],
                "contract_alert": not actual["contract_valid"],
                "source_file": f"django/{actual['database']}",
                "migrator_success": actual["success"],
            },
        ))
    petter = {x["scenario"]: x for x in dj["petter"]["observations"]}
    actual = petter["checkpoint_direct"]
    reference = petter["checkpoint_staged"]
    # The historical 'can_smell' permission is an extra row from a staged
    # intermediate migration. Current MyModel requires 'can_hear' instead.
    required_present = ["can_hear"] in actual["content"]["custom_permissions"]
    cases.append(trial_case(
        "django", "petter_checkpoint", LABELS["django:petter_checkpoint"],
        {
            "schema_and_ledger_equal": (
                actual["same_schema_as_staged"] and actual["same_ledger_as_staged"]
            ),
            "simple_schema_ledger_alert": False,
            "schema_ledger_rowcount_alert": (
                len(actual["content"]["custom_permissions"])
                != len(reference["content"]["custom_permissions"])
            ),
            "untyped_json_alert": False,
            "raw_snapshot_diff_alert": actual["content"] != reference["content"],
            "contract_alert": not required_present,
            "source_file": f"django/{actual['database']}",
            "migrator_success": actual["success"],
        },
    ))
    return cases


def stats(cases: list[dict], key: str) -> dict:
    scored = [x for x in cases if x["label"] is not None]
    pos = [x for x in scored if x["label"] == 1]
    neg = [x for x in scored if x["label"] == 0]
    tp = sum(bool(x[key]) for x in pos)
    fp = sum(bool(x[key]) for x in neg)
    return {
        "method": key,
        "tp": tp, "fn": len(pos) - tp, "fp": fp, "tn": len(neg) - fp,
        "recall": round(tp / len(pos), 4),
        "false_positive_rate": round(fp / len(neg), 4),
        "wilson95_recall_descriptive": wilson(tp, len(pos)),
        "wilson95_fpr_descriptive": wilson(fp, len(neg)),
    }


def elapsed_samples(db_path: Path, sql_statement: str, iterations: int = 200) -> dict:
    durations = []
    with sqlite3.connect(db_path) as connection:
        for _ in range(20):
            connection.execute(sql_statement).fetchall()
        for _ in range(iterations):
            before = time.perf_counter_ns()
            connection.execute(sql_statement).fetchall()
            durations.append((time.perf_counter_ns() - before) / 1e6)
    return {
        "iterations": iterations,
        "median_ms": round(statistics.median(durations), 5),
        "p95_ms": round(sorted(durations)[int(iterations * 0.95)], 5),
        "max_ms": round(max(durations), 5),
    }


def benchmark(results: Path) -> dict:
    targets = {
        "openwebui_one_valid": (
            results / "openwebui/one_valid__upstream.sqlite",
            "SELECT id, info, settings FROM user",
        ),
        "drizzle_set_null": (
            results / "drizzle/set_null_three__upstream.sqlite",
            "SELECT c.id,c.parent_id,p.id FROM child c LEFT JOIN parent p ON p.id=c.parent_id",
        ),
        "django_user_site": (
            results / "django/django-sites-staged-user-row.sqlite",
            "SELECT id,domain,name FROM django_site",
        ),
    }
    return {
        k: elapsed_samples(path, sql_statement) for k, (path, sql_statement) in targets.items()
    }


def evaluate(results: Path, output: Path) -> dict:
    cases = assemble(results)
    methods = [
        "simple_schema_ledger_alert",
        "schema_ledger_rowcount_alert",
        "untyped_json_alert",
        "raw_snapshot_diff_alert",
        "contract_alert",
    ]
    report = {
        "scope": {
            "unit": "controlled replay scenario; NOT an independent industrial incident",
            "projects_total": 3,
            "projects_with_same_schema_ledger_semantic_failures": 2,
            "preregistered_independent_validation": False,
            "strict_holdout": False,
            "source_django_direct_failure_not_scored_as_silent_success": True,
            "empty_json_none_semantics_excluded_as_undecidable": True,
            "contract_alert_is_not_better_than_full_correct_application_tests": True,
            "not_a_random_industrial_sample": True,
        },
        "cases": cases,
        "methods": [stats(cases, m) for m in methods],
        "read_query_benchmark": benchmark(results),
        "environment": {"python": platform.python_version(), "sqlite": sqlite3.sqlite_version},
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "evaluation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    evaluation = evaluate(args.results.resolve(), args.output.resolve())
    print("Cases:", len(evaluation["cases"]))
    for method in evaluation["methods"]:
        print(method["method"], "recall=", method["recall"], "fpr=", method["false_positive_rate"],
              "TP/FP=", method["tp"], method["fp"])
