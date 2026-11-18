"""Verify the GitLab remedial-code change between real quarantine transitions.

GitLab !162803 (2024-08-19) introduced quarantine for a concrete RSpec;
!163832 (2024-08-24) addressed a fixture/Sidekiq false-positive cause;
!164022 (2024-08-27) removed the same quarantine annotation.
These are merge/source effects, not observed per-test subsequent run counts.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ci_event_audit import BASE_GITLAB, request_json


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--ledger",type=Path,default=Path("results/real_ci_events/public_event_ledger.json"))
    p.add_argument("--out",type=Path,default=Path("results/real_ci_events/gitlab_fix_action_chain.json"))
    a=p.parse_args()
    ledger=json.loads(a.ledger.read_text())
    original={x["iid"]:x for x in ledger["gitlab"]["merge_requests"]}
    for iid in (162803,164022):
        if original[iid]["state"]!="merged":
            raise RuntimeError(f"Expected merged MR !{iid}")
    fix_url=f"{BASE_GITLAB}/merge_requests/163832"
    fix,fix_proof=request_json(fix_url)
    changes,changes_proof=request_json(fix_url+"/changes")
    if fix is None or changes is None:
        raise RuntimeError("Public merge/fix evidence unavailable; stop rather than infer")
    if fix.get("state")!="merged":
        raise RuntimeError("The linked remediation was not merged")
    file_rows=[]
    for row in changes.get("changes",[]):
        file_rows.append({"path":row.get("new_path"),"diff_sha256":__import__("hashlib").sha256(
            (row.get("diff") or "").encode()).hexdigest(),
            "added_lines":sum(x.startswith("+") and not x.startswith("+++") for x in row.get("diff","").splitlines()),
            "removed_lines":sum(x.startswith("-") and not x.startswith("---") for x in row.get("diff","").splitlines())})
    result={
        "study":"GitLab quarantine / intervening cause remediation / release",
        "events":[
            {"type":"quarantine_added", "iid":162803,
             "merged_at":original[162803]["merged_at"],
             "url":original[162803]["web_url"],
             "quarantine_annotations_added":original[162803]["quarantine_additions"]},
            {"type":"developer_remediation", "iid":163832,
             "merged_at":fix.get("merged_at"),"url":fix.get("web_url"),
             "merge_commit_sha":fix.get("merge_commit_sha"),
             "title":fix.get("title"),"changed_files":file_rows,
             "metadata_provenance":fix_proof,"diff_provenance":changes_proof},
            {"type":"quarantine_removed", "iid":164022,
             "merged_at":original[164022]["merged_at"],
             "url":original[164022]["web_url"],
             "quarantine_annotations_removed":original[164022]["quarantine_removals"]}],
        "test":"spec/features/merge_request/user_reverts_merge_request_spec.rb / reverts a merge request in a new merge request",
        "observable_after_effect":"Quarantine marker removed in merged GitLab source; CI test reliability after removal not independently observed",
        "not_observed":["CI rerun count/outcome for this one RSpec after removal",
                        "per-test quarantine action timestamps inside CI server",
                        "causal reduction in flaky alerts/build failures"],
    }
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"events":[(x["iid"],x["type"],x["merged_at"]) for x in result["events"]]},indent=2))


if __name__=="__main__":
    main()
