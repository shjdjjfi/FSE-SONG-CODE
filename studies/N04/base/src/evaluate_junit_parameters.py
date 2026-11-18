"""Adjacent real Java migration: recover parameter *instance* IDs.

This is a source-and-runtime-evidence matching study, not an independent
maintainer-confirmed identity oracle and not production CI.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re


OLD = re.compile(r"^(runReconnectBlockingScenario|runReconnectScenario|runNoCloseBlockingTestScenario)(\d+)$")
NEW = {"runReconnectBlockingScenario":"runReconnectCloseBlocking",
       "runReconnectScenario":"runReconnectSocketClose",
       "runNoCloseBlockingTestScenario":"runNoCloseBlockingTestScenario"}


def evaluate(data: dict, replays: list[dict]) -> dict:
    assert {x["maven_test"] for x in replays} == {"Issue256Test", "Issue580Test"}
    outcomes=[x for replay in replays for x in replay["outcomes"]]
    def observations(records):
        return [t for r in records for suite in r["test_executions"] for t in suite["tests"]]
    revisions = replays[0]["revisions"]
    assert all(replay["revisions"]==revisions for replay in replays), "All tests must share same pinned Git revisions"
    assert len(revisions)==2, "Expected two adjacent Java revisions"
    pre = [r for r in outcomes if r["git_sha"]==revisions[0]]
    post = [r for r in outcomes if r["git_sha"]==revisions[1]]
    assert pre and post and len(pre)==len(post)
    assert all(r["returncode"]==0 for r in outcomes), "Build/test failure is not a flakiness label"
    before, after = observations(pre), observations(post)
    a_names = {x["name"] for x in after}
    b_names = {x["name"] for x in before}
    old_names = {x["old_id"].rsplit(".",1)[-1]
                 for x in data["cases"] if x["repository"]=="TooTallNate/Java-WebSocket"
                 and x["old_present_immediate_parent"]}
    rows=[]
    for old in sorted(old_names):
        match=OLD.fullmatch(old)
        if not match or old not in b_names:
            continue
        suffix = f"{NEW[match.group(1)]}[{int(match.group(2))}]"
        new_matches = [n for n in a_names if n == suffix]
        rows.append({"old_runtime_method":old,"predicted_runtime_method":suffix,
                     "instance_runtime_match":len(new_matches)==1,
                     "original_node_id_after_exists":old in a_names,
                     "old_outcome_counts":dict(Counter(x["status"] for x in before if x["name"]==old)),
                     "new_outcome_counts":dict(Counter(x["status"] for x in after if x["name"]==suffix))})
    unique = {r["predicted_runtime_method"] for r in rows}
    assert len(unique)==len(rows), "N-to-1 history merge forbidden at instance level"
    assert all(NEW[match.group(1)] in {x["name"].split("[")[0] for x in after}
               for old in old_names if (match:=OLD.fullmatch(old))), "Missing new parameter family"
    summary = {
        "git_migration_commit":next(c["after_sha"] for c in data["cases"]
                                    if c["repository"]=="TooTallNate/Java-WebSocket"),
        "old_test_instances_candidate_from_source":len(rows),
        "new_matched_parameter_instances":sum(r["instance_runtime_match"] for r in rows),
        "exact_identity_survivors":sum(r["original_node_id_after_exists"] for r in rows),
        "unique_post_parameter_instances":len(unique),
        "total_measured_old_cases_across_runs":len(before),
        "total_measured_new_cases_across_runs":len(after),
        "measured_old_statuses":dict(Counter(x["status"] for x in before)),
        "measured_new_statuses":dict(Counter(x["status"] for x in after)),
        "n_local_repeats_each_revision_per_test_class":replays[0]["repeats"],
        "test_classes":[x["maven_test"] for x in replays],
        "n_revisions":2,
    }
    mapping_strategies=[
       {"strategy":"exact_runtime_id","candidate_instance_links":sum(x["original_node_id_after_exists"] for x in rows),"unsafe_collapsed_groups":0},
       {"strategy":"method_level_name_only","candidate_instance_links":0,"unsafe_collapsed_groups":len(rows)},
       {"strategy":"guarded_abstain_on_group","candidate_instance_links":0,"unsafe_collapsed_groups":0},
       {"strategy":"source_family_plus_parameter_index","candidate_instance_links":sum(x["instance_runtime_match"] for x in rows),"unsafe_collapsed_groups":0},
    ]
    return {
        "evaluation_type":"unmodified test source; temporary JDK21 compatibility adaptations in Maven build (see maven_replay)",
        "test_identity_evidence":"name suffix + JUnit runtime parameter index + two revisions of actual execution",
        "not_independent_oracle":True,"not_historical_CI":True,
        "further_caveat":"A matched ID is a candidate lineage, not proof of identical test intent or quarantine state",
        "summary":summary,"mappings":rows,"mapping_strategies":mapping_strategies,
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--migration",type=Path,required=True)
    p.add_argument("--maven",type=Path,required=True,action="append")
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    out=evaluate(json.loads(args.migration.read_text()),[json.loads(x.read_text()) for x in args.maven])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(out,indent=2),encoding="utf-8")
    print(json.dumps(out["summary"],indent=2))


if __name__=="__main__":main()
