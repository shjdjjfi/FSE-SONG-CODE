"""Reject missing, inconsistent, or overclaimed experiment artifacts."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path


ROOT=Path(__file__).resolve().parents[1]


def read(name):
    return json.loads((ROOT/"results"/name).read_text(encoding="utf-8"))


def assert_equal(value,expected,description):
    if value!=expected:raise AssertionError(f"{description}: expected {expected!r}, got {value!r}")


def verify():
    h=read("ftw_histories.json")
    assert_equal(h["files"],330,"FTW input CSV count")
    assert_equal(len(h["summary"]),11,"FTW track count")
    assert_equal(sum(x["n_status_observations"] for x in h["summary"]),4654230,"FTW repeated test statuses")
    aligned=read("source_aligned.json")["evaluations"]
    assert_equal(len(aligned),11,"FTW tracks aligned to Git")
    assert_equal(sum(x["status"]=="aligned" for x in aligned.values()),11,"usable aligned tracks")
    assert_equal(sum(len(x["metadata"]["excluded_unreachable"]) for x in aligned.values()),0,"unreachable FTW revisions")

    d=read("idoft_migrations.json")
    assert_equal(len(d["cases"]),74,"IDoFT cases")
    assert_equal(len(d["events"]),15,"IDoFT event count")
    assert_equal(sum(x["many_old_to_one_method"] for x in d["cases"]),27,"method-group ambiguous cases")
    assert_equal(sum(x["idoft_status"]=="Deleted" for x in d["cases"]),9,"IDoFT deleted labels")
    results=read("idoft_evaluation.json")
    r={x["arm"]:x for x in results["summary"]}
    assert_equal(len(r),8,"compared strategies")
    guard=r["guarded_lineage"]
    for key,val in (("eligible_individual_positive",34),( "correct_individual_links",26),
                    ("false_inheritance_on_deleted",4),("deleted_negative",9),
                    ("uncontested_deleted_negative",5),
                    ("false_inheritance_on_uncontested_deleted",0),
                    ("unjustified_instance_links_on_groups",0)):
        assert_equal(guard[key],val,"guarded "+key)
    assert_equal(r["git_path_same_method"]["correct_individual_links"],14,"Git baseline recovery")
    assert_equal(r["name_and_context"]["correct_individual_links"],25,"strong context baseline recovery")
    assert_equal(r["ablation_no_group_guard"]["unjustified_instance_links_on_groups"],27,"group gate ablation")
    stat=read("statistical_audit.json")
    assert stat["calibration_target"]["meets_target_on_raw_IDoFT_deleted_labels"] is False
    assert stat["calibration_target"]["statistically_certifies_target_with_95_percent_confidence"] is False
    assert_equal(read("label_audit.json")["conflict_count"],4,"raw IDoFT deleted-label contradictions")

    source=read("source_gold_evaluation.json")
    assert_equal(source["summary"][0]["cases"],6,"human source-gold cases")
    assert_equal(sum(x["decision"]=="transfer" for x in
                     json.loads((ROOT/"evidence/source_events_gold.json").read_text())["labels"]),3,"human source-gold positives")
    policy=read("actual_history_policy.json")
    assert_equal(policy["summary"]["hypothetical_policy_decision_differences"],0,"real history hypothetical policy differences")
    assert policy["no_independent_quarantine_labels"]
    ci=read("real_ci_audit.json")["overall"]
    for key,val in (("unique_repository_run_attempts",62),("unique_failed_test_ids_per_repo_summed",212),
                    ("distinct_test_ids_with_mixed_replications_per_repo_summed",4),
                    ("runs_missing_quarantine_field",62)):
        assert_equal(ci[key],val,"real GitHub Actions "+key)
    junit=read("junit_parameter_migration.json")
    for key,val in (("old_test_instances_candidate_from_source",27),
                    ("new_matched_parameter_instances",27),
                    ("exact_identity_survivors",0),
                    ("total_measured_old_cases_across_runs",120),
                    ("total_measured_new_cases_across_runs",120)):
        assert_equal(junit["summary"][key],val,"JUnit actual test replay "+key)
    assert_equal(junit["summary"]["measured_new_statuses"],{"passed":119,"skipped":1},"post migration test statuses")
    assert junit["not_independent_oracle"] and junit["not_historical_CI"]
    pytest=read("pytest_cache_replay.json")
    assert_equal(len(pytest["experiments"]),3,"controlled variants")
    for t in pytest["experiments"]:
        assert_equal([t[x]["selected_count"] for x in ("baseline_same_id","stale_renamed","identity_migrated")],
                     [1,3,1],"controlled cache experiment")
    holdout=read("idoft_heldout_evaluation.json")
    assert_equal(holdout["summary"][5]["eligible_individual_positive"],0,"holdout lacks independent FQN positive oracle")
    for name in ("lineage_tradeoff","ftw_source_coverage","pytest_cache_mechanism","junit_parameter_instance_recovery"):
        for suffix in ("png","pdf"):
            path=ROOT/"figures"/(name+"."+suffix)
            if not path.is_file() or path.stat().st_size<1000:
                raise AssertionError(f"Missing/unrendered publication figure: {path}")
    provenance=ROOT/"results/provenance.json"
    if provenance.exists():
        data=json.loads(provenance.read_text())
        for relative,expected in data.get("bundle_sha256",{}).items():
            file=ROOT/relative
            if not file.exists():raise AssertionError(f"Missing integrity file: {relative}")
            sha=hashlib.sha256(file.read_bytes()).hexdigest()
            if sha!=expected:raise AssertionError(f"Changed since freeze: {relative}")
    return {"ftw_observations":4654230,"idoft_cases":74,"actual_java_results":240,
            "measured_real_ci_failure_runs":62,"quarantine_study_complete":False}


if __name__=="__main__":
    print("Integrity and non-overclaim checks passed:",json.dumps(verify(),sort_keys=True))
