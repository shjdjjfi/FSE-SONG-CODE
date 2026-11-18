"""Independent Git similarity evidence for four disputed IDoFT `Deleted` rows.

This is a *source* validation of file moves, not human adjudication of whether
the flaky-test execution history and its quarantine policy should migrate.
"""

from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          text=True, capture_output=True).stdout.strip()


def main(repo: Path, audit: Path, output: Path):
    label_data=json.loads(audit.read_text())
    sha=git(repo,"rev-parse","cef45a1e325b^{commit}")
    parent=git(repo,"rev-parse",sha+"^1")
    changed=git(repo,"diff","--find-renames=50%","--name-status",parent,sha,
                "--","riptide-spring-boot-starter/src/test",
                "riptide-spring-boot-autoconfigure/src/test")
    matches=[]
    for case in label_data["conflicts"]:
        old=case["old_id"].rsplit(".",1)[0]
        new=case["target_identical_method"].rsplit(".",1)[0]
        o=old.replace(".","/")+".java"
        n=new.replace(".","/")+".java"
        hits=[]
        for line in changed.splitlines():
            bits=line.split("\t")
            if len(bits)==3 and bits[0].startswith("R") and bits[1].endswith(o) and bits[2].endswith(n):
                hits.append({"rename_status":bits[0],"old_path":bits[1],"new_path":bits[2],
                             "similarity_percent":int(bits[0][1:])})
        matches.append({"old_id":case["old_id"],"new_id":case["target_identical_method"],
                        "original_idoft_status":case["original_status"],"git_rename_matches":hits,
                        "unique_rename":len(hits)==1})
    result={"repository":"https://github.com/zalando/riptide",
            "migration_commit":sha,"migration_parent":parent,
            "maintainer_commit_subject":git(repo,"show","-s","--format=%s",sha),
            "evidence_kind":"Git file similarity in release migration + existing equal method bodies; NOT independently human-adjudicated flaky-history identity",
            "original_deleted_labels_kept":True,
            "rename_confirmed":sum(m["unique_rename"] for m in matches),
            "total_disputed":len(matches),"cases":matches}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps({"rename_confirmed":result["rename_confirmed"],
                      "total_disputed":result["total_disputed"]},indent=2))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--repo",type=Path,required=True)
    p.add_argument("--label-audit",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    main(a.repo,a.label_audit,a.output)
