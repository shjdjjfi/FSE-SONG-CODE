"""Hard fail if the expanded evidence is missing or overstated.

The third-party 'FP' labels are *refactoring claim* rejections, not unsafe
flaky-history transfer labels. A real file-level split is not proof of a
generalized N04 production win.
"""

from __future__ import annotations
import json
from pathlib import Path


ROOT=Path(__file__).resolve().parents[1]


def read(name):
    path=ROOT/"results"/name
    if not path.is_file():raise AssertionError(f"Missing actual results: {path}")
    return json.loads(path.read_text())


def check():
    original=read("idoft_evaluation.json")
    guard=next(r for r in original["summary"] if r["arm"]=="guarded_lineage")
    assert (guard["false_inheritance_on_deleted"],guard["deleted_negative"])==(4,9)
    assert (guard["false_inheritance_on_uncontested_deleted"],guard["uncontested_deleted_negative"])==(0,5)
    labels=read("riptide_git_rename_audit.json")
    assert labels["rename_confirmed"]==4 and labels["total_disputed"]==4
    assert all(case["unique_rename"] and 90<=case["git_rename_matches"][0]["similarity_percent"]<=100
               for case in labels["cases"])

    oracle=read("independent_refactoring_oracle.json")
    assert oracle["summary"]=={"candidate_pairs":142,"TP":81,"FP":61,
                               "independent_projects":22,"independent_commits":30}
    assert oracle["not_a_quarantine_decision_oracle"]
    src=read("independent_source_validation.json")
    assert src["excluded"].get("repository_not_fetched")==37
    assert len(src["rows"])==105
    assert sum(x["oracle_label"]=="TP" for x in src["rows"])==54
    assert sum(x["oracle_label"]=="FP" for x in src["rows"])==51
    e2e=read("independent_end_to_end_discovery.json")
    assert e2e["no_target_or_label_in_prediction"] and e2e["not_quarantine_oracle"]
    assert len(e2e["records"])==105
    summary={x["arm"]:x for x in e2e["summary"]}
    for name,positive_count in (("exact_id",0),("unique_name",39),("unique_body",17),
                                ("guarded_with_group_guard",40)):
        row=summary[name]
        assert row["independently_confirmed_refactoring_pairs"]==54
        assert row["independent_target_recovered"]==positive_count
        assert row["refactoring_proposals_labeled_FP"]==51
    assert "NOT unsafe quarantine" in summary["guarded_with_group_guard"]["warning"]
    for row in e2e["records"]:
        for name,value in row["predicted_targets"].items():
            assert row["oracle_target_matched"][name]==(value==row["third_party_proposed_target"])
    stats=read("independent_generalization_statistics.json")
    assert (stats["n_repositories"],stats["n_positive_commits"])==(4,6)
    assert (stats["positive_pairs"],stats["distinct_old_test_ids"],
            stats["one_to_many_split_old_ids"],stats["unique_target_only_cases"])==(54,53,1,52)
    assert (stats["recovered_guarded"],stats["recovered_strong_name_baseline"])==(40,39)
    assert stats["event_bootstrap"]["clusters"]==6
    assert stats["repository_bootstrap"]["clusters"]==4
    assert stats["guarded_minus_name_percentage_points"]<15

    ledger=read("fusion_quarantine_ledger.json")
    s=ledger["summary"]
    for k,v in (("ledger_revisions",145),("add_decisions",264),
                ("remove_decisions_unresolved",261),("distinct_identifiers_ever_added",215),
                ("added_entries_with_action_links",104),("possible_rename_with_same_evidence",1),
                ("parse_errors",2)):
        assert s[k]==v,(k,s[k],v)
    assert read("trycua_quarantine_ledger.json")["summary"]["add_decisions"]==3
    linked=read("fusion_identity_linked_quarantine.json")
    c=linked["decision_provenance"]
    assert all([c["same_action_run_in_reasons"],c["actual_before_excluded"],
                c["actual_after_new_excluded"],c["actual_after_old_not_excluded"]])
    assert c["linked_actions_run"].endswith("/28697507894")
    n=linked["source_declared_test_counts"]
    assert (n["old_file_before"],n["old_file_after"],n["new_file_after"])==(155,154,1)
    assert linked["identity_confirmation"]["assertion_statement_lines"]==13
    assert linked["identity_confirmation"]["source_assertion_lines_equal"]
    assert linked["scope_limit"]

    runs=read("fusion_real_ci_runs.json")
    before,after=runs["runs"]
    assert [before["id"],after["id"]]==[28697507894,28720367126]
    assert before["conclusion"]==after["conclusion"]=="failure"
    assert [before["overall_update_elapsed_seconds"],after["overall_update_elapsed_seconds"]]==[522,529]
    assert [before["job_walltimes_sum_seconds"],after["job_walltimes_sum_seconds"]]==[1609,1706]
    assert [before["job_count"],after["job_count"]]==[7,7]
    assert runs["post_run_head_descends_from_study_commit"]
    assert runs["observational_warning"]
    for name in ("independent_holdout_recall","fusion_quarantine_split"):
        for suffix in ("png","pdf"):
            fig=ROOT/"figures"/(name+"."+suffix)
            assert fig.is_file() and fig.stat().st_size>1000,f"Missing new figure {fig}"
    return {"original_raw_errors":"4/9","independent_edges":54,"external_projects":4,
            "end_to_end_recovery":"40/54","name_baseline":"39/54",
            "verified_real_quarantine_split":1,"actual_ci_cost_saving_proven":False,
            "certified_false_inheritance_below_2pct":False,
            "ready_to_claim_fse_industry_benefit":False}


if __name__=="__main__":
    print("Addendum empirical checks passed:",json.dumps(check(),sort_keys=True))
