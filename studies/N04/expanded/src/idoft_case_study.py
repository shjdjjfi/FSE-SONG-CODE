"""Audit public IDoFT moved/renamed labels and an independently witnessed case.

Link 27 curated Java-WebSocket identity changes to pre-upgrade actual 30-run
test outcomes from the FTW 2024 histories dataset. Post-upgrade outcomes are
NOT in the history corpus: no claim of observed deployment benefit is made.
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import re
from pathlib import Path


def read(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))


def after_name(old: str) -> str | None:
    class_name, method = old.rsplit(".",1)
    m = re.fullmatch(r"runReconnectBlockingScenario(\d+)",method)
    if m:
        return class_name + ".runReconnectCloseBlocking[" + m.group(1) + "]"
    m = re.fullmatch(r"runReconnectScenario(\d+)",method)
    if m:
        return class_name + ".runReconnectSocketClose[" + m.group(1) + "]"
    m = re.fullmatch(r"runNoCloseBlockingTestScenario(\d+)",method)
    if m:
        return class_name + ".runNoCloseBlockingTestScenario[" + m.group(1) + "]"
    return None


def run(raw: Path, replay: Path, out: Path, post_repo: Path | None):
    all_rows = {}
    stats = {}
    for name, filename in (("maven", "idoft_maven.csv"),
                           ("gradle", "idoft_gradle.csv"),
                           ("pytest", "idoft_py.csv")):
        path = raw / filename
        r = read(path)
        moved = [x for x in r if x.get("Status","").strip()=="MovedOrRenamed"]
        all_rows[name] = moved
        stats[name] = {"all_flaky_test_records":len(r),"labeled_moved_or_renamed":len(moved),
                       "repos_with_moved":len(set(x["Project URL"] for x in moved)),
                       "annotated_fix_links":sum(bool(re.search(r"/commit/[0-9a-f]{7,40}",x.get("Notes", ""))) for x in moved),
                       "csv_sha256":hashlib.sha256(path.read_bytes()).hexdigest()}
    old = [r for r in all_rows["maven"] if "TooTallNate/Java-WebSocket" in r["Project URL"]]
    renamed_ids = {r["Fully-Qualified Test Name (packageName.ClassName.methodName)"]:r for r in old}
    matched = collections.defaultdict(list)
    for r in read(replay):
        if r.get("seed")!="17":
            continue
        fq = r["test_suite"] + "." + r["test_name"]
        if fq in renamed_ids and "Java-WebSocket" in r["project"]:
            matched[fq].append(r)
    table = []
    for old_id, row in sorted(renamed_ids.items()):
        found = matched[old_id]
        if not found:
            continue
        table.append({"old_test":old_id,"new_parameterized_test":after_name(old_id),
                      "old_detected_sha":row["SHA Detected"],
                      "refactoring_commit":"2ce6e6149d0ef44f4919e75326265c64c144a00f",
                      "historical_commits":len(found),
                      "commits_pass_fail_flaky_30":sum(r["globally_flaky_30"]=="True" for r in found),
                      "commits_quarantine_from_20":sum(r["preserved_quarantine"]=="True" for r in found),
                      "commits_quarantine_from_last5":sum(r["reset_quarantine"]=="True" for r in found)})
    validation = {}
    if post_repo and post_repo.is_dir():
        for klass in ("Issue256Test", "Issue580Test"):
            p = post_repo / "src/test/java/org/java_websocket/issues" / f"{klass}.java"
            src = p.read_text(encoding="utf-8")
            validation[klass] = {"parameterized": "@RunWith(Parameterized.class)" in src,
                                 "range_10": "NUMBER_OF_TESTS = 10" in src,
                                 "methods":re.findall(r"public\s+void\s+(\w+)\s*\(",src)}
        assert all(v["parameterized"] and v["range_10"] for v in validation.values())
        for item in table:
            method = item["new_parameterized_test"].split(".")[-1].split("[")[0]
            klass = item["old_test"].split(".")[-2]
            assert method in validation[klass]["methods"], (item, validation)
    out.mkdir(parents=True, exist_ok=True)
    if table:
        with (out / "java_websocket_migration_history.csv").open("w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f,fieldnames=list(table[0]))
            w.writeheader()
            w.writerows(table)
    report = {"idoft":stats,"java_websocket":{
        "old_ids_annotated":len(old),"old_ids_with_actual_historical_outcomes":len(table),
        "test_commit_observations_before_refactoring":sum(x["historical_commits"] for x in table),
        "historical_commit_test_observations_with_flakiness":sum(x["commits_pass_fail_flaky_30"] for x in table),
        "refactoring_commit":"https://github.com/TooTallNate/Java-WebSocket/commit/2ce6e6149d0ef44f4919e75326265c64c144a00f",
        "after_source_validation":validation,
        "caveat":"Post-refactor JUnit executions were NOT observed in the historical FTW dataset; parameter mapping derives from this one source commit."}}
    (out / "idoft_results.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))


if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--raw",type=Path,default=Path("data/raw"))
    p.add_argument("--replay",type=Path,default=Path("results/history_replay/real_history_decisions.csv"))
    p.add_argument("--post-repo",type=Path,default=Path("data/javawebsocket_post"))
    p.add_argument("--out",type=Path,default=Path("results/idoft"))
    a=p.parse_args()
    run(a.raw,a.replay,a.out,a.post_repo)
