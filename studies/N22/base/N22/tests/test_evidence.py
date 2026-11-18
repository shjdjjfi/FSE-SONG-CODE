import json
from pathlib import Path

import pytest


HERE = Path(__file__).resolve().parents[1]
RESULTS = HERE / "results"


def rows(name):
    return json.loads((RESULTS / name).read_text(encoding="utf-8"))


def test_openwebui_upstream_revision_and_real_difference():
    evidence = rows("openwebui/openwebui-observations.json")
    assert evidence["input"]["commit"] == "1a97751e376e00a1897bc3679215ae1c7bd8fd42"
    assert evidence["input"]["reference_patch_is_not_an_upstream_release"]
    lookup = {x["id"]: x for x in evidence["runs"]}
    broken = lookup["one_valid__upstream"]
    corrected = lookup["one_valid__reference_patch"]
    assert broken["success"] and corrected["success"]
    assert broken["same_schema_as_reference"] and broken["same_ledger_as_reference"]
    assert not broken["typed_pydantic_probe_success"]
    assert corrected["typed_pydantic_probe_success"]
    assert broken["generic_json_parse_success"]
    assert lookup["two_valid__upstream"]["success"] is False
    assert lookup["zero_users__upstream"]["typed_pydantic_probe_success"]


def test_drizzle_success_journal_and_links():
    evidence = rows("drizzle/drizzle-observations.json")
    lookup = {x["id"]: x for x in evidence["runs"]}
    c = lookup["cascade_three__upstream"]
    assert c["success"] and c["same_schema_as_reference"] and c["same_ledger_as_reference"]
    assert len(c["journal"]) == 1
    assert c["child"] == [] and c["grandchild"] == []
    assert c["integrity_check"][0]["integrity_check"] == "ok"
    s = lookup["set_null_three__upstream"]
    assert s["success"] and s["same_row_counts_as_reference"]
    assert not s["data_contract_preserved"]
    assert all(x["parent_id"] is None for x in s["child"])
    assert lookup["no_action_three__upstream"]["success"] is False
    assert lookup["cascade_user_edit__reference_fk_before_begin"]["data_contract_preserved"]


def test_django_true_negative_and_repro_boundary():
    evidence = rows("django/django-observations.json")
    sites = {x["scenario"]: x for x in evidence["builtin_sites"]["observations"]}
    custom = sites["staged-user-row"]
    assert custom["same_schema_as_fresh"]
    assert custom["same_ledger_as_fresh"]
    assert custom["same_rows_as_fresh"] is False
    assert custom["contract_valid"]
    petter = {x["scenario"]: x for x in evidence["petter"]["observations"]}
    assert not petter["direct"]["success"]
    assert petter["staged"]["success"]
    assert petter["checkpoint_direct"]["same_ledger_as_staged"]
    assert petter["checkpoint_direct"]["same_schema_as_staged"]
    # Historically-created extra can_smell row is not a required current permission.
    assert petter["checkpoint_direct"]["content"]["custom_permissions"] == [["can_hear"]]


def test_evaluation_truth_boundary():
    evidence = rows("evaluation.json")
    assert len(evidence["cases"]) == 13
    assert len([r for r in evidence["cases"] if r["label"] is None]) == 1
    assert len([r for r in evidence["cases"] if r["label"] == 1]) == 6
    assert len([r for r in evidence["cases"] if r["label"] == 0]) == 6
    methods = {r["method"]: r for r in evidence["methods"]}
    assert methods["simple_schema_ledger_alert"]["tp"] == 0
    assert methods["schema_ledger_rowcount_alert"]["tp"] == 3
    assert methods["raw_snapshot_diff_alert"]["fp"] == 2
    assert methods["contract_alert"]["tp"] == 6
    assert methods["contract_alert"]["fp"] == 0
    assert evidence["scope"]["preregistered_independent_validation"] is False
    assert evidence["scope"]["strict_holdout"] is False
