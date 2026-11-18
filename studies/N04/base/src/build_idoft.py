"""Build a public-source-grounded migration benchmark from IDoFT labels.

IDoFT's `MovedOrRenamed` is an independent label that the *old flaky test*
has a successor. IDoFT generally does not specify the successor FQN. A unique
successor found by unchanged method name on a Git-tracked renamed file is
reported separately from a successor inferred from an exact code body; this
is important to prevent circular ground-truth claims.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from difflib import SequenceMatcher
import json
from pathlib import Path
import re

from java_source import file_path_for_name, java_test_diff, methods_at, run_git


COMMIT_RE = re.compile(r"/commit/([0-9a-f]{7,40})")
TEST_COL = "Fully-Qualified Test Name (packageName.ClassName.methodName)"


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def candidate_score(old, new, *, file_rename=False) -> dict:
    exact = old.body_hash == new.body_hash
    name_score = similarity(old.name, new.name)
    assertions = len(set(old.calls) & set(new.calls)) / max(1, len(set(old.calls) | set(new.calls)))
    prefix = old.body[:1200] == new.body[:1200]
    # Avoid quadratic comparison for long bodies.  The score alone is not
    # evidence that two tests have unchanged assertion semantics.
    body_score = 1.0 if exact else (similarity(old.body[:2400], new.body[:2400])
                                    if (len(old.body) < 2800 and len(new.body) < 2800
                                        and (file_rename or name_score >= .48 or assertions >= .5))
                                    else 0.0)
    score = .55 * body_score + .20 * name_score + .15 * assertions + .10 * float(file_rename)
    return {"body_equal": exact, "body_similarity": round(body_score, 4),
            "name_similarity": round(name_score, 4),
            "assertion_similarity": round(assertions, 4),
            "file_rename": bool(file_rename), "score": round(score, 4),
            "prefix_equal": prefix}


def load_cases(files: list[Path], available: dict) -> dict:
    groups = defaultdict(list)
    excluded = Counter()
    for f in files:
        with f.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                if row.get("Status") not in ("MovedOrRenamed", "Deleted"):
                    continue
                slug = row["Project URL"].rstrip("/").split("github.com/")[-1]
                if slug not in available:
                    excluded["repo_not_selected"] += 1
                    continue
                link = COMMIT_RE.search(row.get("Notes", ""))
                if not link:
                    excluded["no_migration_commit_in_notes"] += 1
                    continue
                groups[slug, link.group(1)].append(row)
    return groups, excluded


def construct(csv_files: list[Path], available: dict) -> dict:
    cases_by_commit, excluded = load_cases(csv_files, available)
    output = []
    cases = []
    for (slug, sha), rows in sorted(cases_by_commit.items()):
        repo = str(available[slug].resolve())
        try:
            full_sha = run_git(repo, "rev-parse", sha + "^{commit}").strip()
            parent = run_git(repo, "rev-parse", full_sha + "^1").strip()
        except RuntimeError:
            excluded["commit_not_in_clone"] += len(rows)
            continue
        entries, old_paths, new_paths = java_test_diff(repo, parent, full_sha)
        if not new_paths:
            excluded["no_java_test_change"] += len(rows)
            continue
        # Avoid fetching every blob after a massive Java package migration.
        # Scope candidate source to the recorded IDoFT classes first.
        old_paths_by_case = {}
        for row in rows:
            old_name = row.get(TEST_COL, "")
            old_paths_by_case[old_name] = file_path_for_name(old_name, old_paths,
                                                              row.get("Module Path", ""))
        selected_new_paths = set()
        for old_name, p in old_paths_by_case.items():
            if not p:
                continue
            base = p.rsplit("/", 1)[-1]
            direct = [x for x in new_paths if x == p or x.endswith("/" + base)]
            selected_new_paths.update(direct)
        if len(new_paths) <= 18:
            selected_new_paths.update(new_paths)
        if not selected_new_paths:
            excluded["unresolved_destination_files"] += len(rows)
            continue
        new_methods = {m.fqn: m for p in sorted(selected_new_paths)
                       for m in methods_at(repo, full_sha, p) if m.is_test}
        # A source-path move with the same Java classname can be identified
        # without relying on Git's content-based -M heuristic.
        rename = {}
        for oldp in old_paths:
            same = [p for p in new_paths if p != oldp and
                    p.rsplit("/", 1)[-1] == oldp.rsplit("/", 1)[-1]]
            if len(same) == 1:
                rename[oldp] = same[0]
        event_id = f"{slug}@{full_sha[:12]}"
        event_cases = []
        for row in rows:
            old_fqn = row.get(TEST_COL, "")
            old_path = old_paths_by_case.get(old_fqn)
            if old_path is None:
                excluded["labeled_test_source_not_changed"] += 1
                continue
            # The IDoFT status labels the test on SHA Detected, often months
            # before the migration commit.  Using migration^ as the old test
            # revision creates false label disagreements when the test has
            # changed in between.  Always retrieve the published old SHA.
            detected = row.get("SHA Detected", "")
            if not detected:
                excluded["missing_detected_sha"] += 1
                continue
            try:
                original_sha = run_git(repo, "rev-parse", detected + "^{commit}").strip()
            except RuntimeError:
                excluded["detected_commit_unavailable"] += 1
                continue
            source = {m.fqn: m for m in methods_at(repo, original_sha, old_path)}
            old = source.get(old_fqn)
            if old is None:
                tree = run_git(repo, "ls-tree", "-r", "--name-only", original_sha).splitlines()
                historical_path = file_path_for_name(old_fqn,
                                  [p for p in tree if p.endswith(".java") and "/test/" in p.lower()],
                                  row.get("Module Path", ""))
                if historical_path:
                    old_path = historical_path
                    source = {m.fqn:m for m in methods_at(repo, original_sha, old_path)}
                    old = source.get(old_fqn)
            if old is None:
                excluded["labeled_method_missing_at_detection"] += 1
                continue
            # IDoFT's detected SHA can be years before the linked migration
            # commit.  Keep *direct adjacency* as an explicit experimental
            # cohort: a historical test absent from migration^ cannot be a
            # valid parent -> migration event for instance-level carryover.
            parent_source = {m.fqn:m for m in methods_at(repo, parent, old_path)}
            parent_old = parent_source.get(old_fqn)
            if parent_old is None:
                for possible_path in old_paths:
                    if possible_path == old_path:
                        continue
                    parent_matches = {m.fqn:m for m in methods_at(repo,parent,possible_path)}
                    parent_old = parent_matches.get(old_fqn)
                    if parent_old is not None:
                        break
            alternatives = []
            for new in new_methods.values():
                if new.fqn == old.fqn:
                    continue
                # Only changed files are compared, so a source-control move
                # through *untouched* files cannot accidentally become gold.
                s = candidate_score(old, new, file_rename=rename.get(old_path) == new.path)
                alternatives.append({"target": new.fqn, "target_path": new.path,
                                     **s})
            alternatives.sort(key=lambda x: (-x["score"], x["target"]))
            # IDoFT provides the positive lineage label, but not a target FQN.
            # Preserve source-derived target certainty in its own field.
            exact_body = [x for x in alternatives if x["body_equal"]]
            file_name = [x for x in alternatives if x["file_rename"] and
                         x["target"].rsplit(".", 1)[-1] == old.name]
            same_name = [x for x in alternatives if
                         x["target"].rsplit(".", 1)[-1] == old.name]
            if row["Status"] == "Deleted":
                successor, certainty = None, "idoft_deleted_negative"
            elif len(file_name) == 1:
                successor, certainty = file_name[0]["target"], "path_move_same_method"
            elif len(same_name) == 1:
                successor, certainty = same_name[0]["target"], "moved_class_same_method"
            elif len(exact_body) == 1:
                successor, certainty = exact_body[0]["target"], "unique_equal_body_inference"
            elif len(exact_body) > 1:
                successor, certainty = None, "ambiguous_equal_bodies"
            else:
                successor, certainty = None, "target_not_independently_confirmed"
            event_cases.append({
                "event_id": event_id, "repository": slug,
                "before_sha": original_sha, "migration_parent_sha": parent,
                "after_sha": full_sha,
                "old_id": old_fqn, "old_path": old_path,
                "old_body_hash": old.body_hash, "old_body": old.body,
                "old_present_immediate_parent": parent_old is not None,
                "parent_body_equal_to_detection": bool(parent_old and parent_old.body_hash == old.body_hash),
                "old_parent_body_hash":parent_old.body_hash if parent_old else None,
                "old_assertions": old.calls,
                "idoft_status": row["Status"],
                "idoft_detected_sha": row.get("SHA Detected"),
                "idoft_category": row.get("Category"),
                "idoft_notes": row.get("Notes"),
                "target": successor, "target_certainty": certainty,
                "candidate_count": len(alternatives),
                "candidates": alternatives,
            })
        cases.extend(event_cases)
        output.append({"event_id": event_id, "repository": slug,
                       "commit": full_sha, "parent": parent,
                       "rows_in_idoft": len(rows), "rows_with_old_source": len(event_cases),
                       "changed_test_files": len(entries),
                       "source_commit_url": f"https://github.com/{slug}/commit/{full_sha}"})
    # A unique target for *each old method* does not imply a unique mapping:
    # 27 JUnit4 tests can collapse into 2 parameterized methods. Such rows
    # cannot carry test-instance quarantine identities without parameter data.
    incoming = Counter((c["event_id"], c["target"]) for c in cases if c["target"])
    for case in cases:
        case["many_old_to_one_method"] = bool(case["target"] and
              incoming[case["event_id"], case["target"]] > 1)
        if case["many_old_to_one_method"]:
            case["target_certainty"] = "parameterized_group_only"
    return {"benchmark": "IDoFT fixed Git migration/deletion commits, FQNs and source-derived targets",
            "status_scope": "IDoFT MovedOrRenamed/Deleted labels; original authors distinguish true carryover from deleted or semantically changed tests",
            "labeling_caution": "IDoFT label confirms migration, not target FQN; inferred targets are source-dependent and must be evaluated separately",
            "excluded": dict(excluded), "events": output, "cases": cases}


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--idoft", type=Path, required=True)
    a.add_argument("--repo", nargs=2, action="append", required=True)
    a.add_argument("--output", type=Path, required=True)
    args = a.parse_args()
    repos = {k: Path(v) for k, v in args.repo}
    data = construct([args.idoft / x for x in ("pr-data.csv", "gr-data.csv")], repos)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(json.dumps({"events": len(data["events"]), "cases": len(data["cases"]),
                      "certain": Counter(c["target_certainty"] for c in data["cases"]),
                      "excluded": data["excluded"]}, indent=2))


if __name__ == "__main__":
    main()
