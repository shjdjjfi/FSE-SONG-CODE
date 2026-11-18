"""Execute untouched public Python tests before and after historical commits.

The unit of observation is an actual pytest invocation in an upstream Git
checkout. The Git revision, test paths, test-case JUnit rows and stdout hashes
are retained. Analyses of quarantine-history *transfers* are explicitly
source-based counterfactuals, not changes applied to the upstream CI service.

Run from the N04 package root after fetching the worktrees listed below:
    python3 src/cross_repo_real_replay.py --repeats 10
"""

from __future__ import annotations

import argparse
import ast
import collections
import csv
import datetime as dt
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path


CASES = (
    {
        "id": "click-case-split-2025", "project": "pallets/click",
        "commit": "7c7ec36354f49d1a092cb077fa4881ea4d70ba01",
        "pre": "92129c552da88ac30b578132031efa4b003ecc46",
        "pre_dir": "click_pre_case_split", "post_dir": "click_post_case_split",
        "pre_target": "tests/test_context.py::test_with_resource_exception",
        "post_target": ("tests/test_context.py::test_with_resource_exception",
                        "tests/test_context.py::test_with_resource_nested_exception"),
        "pre_sources": ("tests/test_context.py",),
        "post_sources": ("tests/test_context.py",),
        "annotation": "one-to-many test-method split: nested resource logic extracted",
    },
    {
        "id": "click-module-split-types-2026", "project": "pallets/click",
        "commit": "7ecc8d7ee4a2e5c0732d6551baeb7597b7a73ade",
        "pre": "87f7a316f482d88d7ef45660da12cdcc5a5c14f6",
        "pre_dir": "click_pre_types", "post_dir": "click_post_types",
        "pre_target": "tests/test_types.py", "post_target": "tests/test_types",
        "pre_sources": ("tests/test_types.py",),
        "post_sources": ("tests/test_types", "tests/test_exceptions/test_FileError.py"),
        "annotation": "module split into multiple files; do not label all as test-case splits",
    },
    {
        "id": "click-module-split-utils-2026", "project": "pallets/click",
        "commit": "9ab346f6b57f2c99388b4e9db58a0961bc3027c8",
        "pre": "df2e5ed8c4e89f51ff4eddb9600d913083613e62",
        "pre_dir": "click_pre_utils", "post_dir": "click_post_utils",
        "pre_target": "tests/test_utils.py", "post_target": "tests/test_utils",
        "pre_sources": ("tests/test_utils.py",),
        "post_sources": ("tests/test_utils",),
        "annotation": "module split into multiple files; same-name collisions possible",
    },
    {
        "id": "markupsafe-semantic-extension-2022", "project": "pallets/markupsafe",
        "commit": "e49d257126d09937b1bf5e2b2173238df729fb13",
        "pre": "0e366be90424816156802b41997b37b5dadd0851",
        "pre_dir": "markupsafe_pre_strip", "post_dir": "markupsafe_post_strip",
        "pre_target": "tests/test_markupsafe.py",
        "post_target": "tests/test_markupsafe.py",
        "pre_sources": ("tests/test_markupsafe.py",),
        "post_sources": ("tests/test_markupsafe.py",),
        "annotation": "same test name, changed coverage after fix; unsafe not proven",
    },
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def checked_sha(repo: Path, commit: str) -> None:
    if not repo.is_dir():
        raise FileNotFoundError(f"Worktree absent: {repo}")
    got = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    if got != commit:
        raise RuntimeError(f"Expected {commit}, found {got} in {repo}")


def source_functions(repo: Path, source_paths: tuple[str, ...]):
    paths = []
    for item in source_paths:
        p = repo / item
        if p.is_file():
            paths.append(p)
        elif p.is_dir():
            paths.extend(p.rglob("test_*.py"))
        else:
            raise FileNotFoundError(p)
    output = []
    for p in sorted(set(paths)):
        text = p.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(text)
        rel = str(p.relative_to(repo))
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                found = [(node, "")]
            elif isinstance(node, ast.ClassDef):
                found = [(n, node.name) for n in node.body if isinstance(n, (
                    ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test_")]
            else:
                found = []
            for fun, klass in found:
                # The function name is not part of its behavioral body hash.
                body = ast.dump(ast.Module(body=fun.body, type_ignores=[]),
                                annotate_fields=True, include_attributes=False)
                doc = ast.get_docstring(fun)
                output.append({
                    "id": f"{rel}::{klass + '::' if klass else ''}{fun.name}",
                    "file": rel, "method": fun.name, "class": klass,
                    "start_line": fun.lineno, "full_source_sha256": sha(ast.get_source_segment(text, fun).encode()),
                    "body_ast_sha256": sha(body.encode()),
                    "has_nested_resource": "base_val_nested" in body,
                    "source_docstring": bool(doc),
                })
    return output


def summarize_source(pre: list, post: list):
    old_count = collections.Counter(f["method"] for f in pre)
    new_count = collections.Counter(f["method"] for f in post)
    old_hash = collections.defaultdict(list)
    new_hash = collections.defaultdict(list)
    for row in pre:
        old_hash[row["body_ast_sha256"]].append(row)
    for row in post:
        new_hash[row["body_ast_sha256"]].append(row)
    identical = []
    for fingerprint in sorted(set(old_hash) & set(new_hash)):
        if len(old_hash[fingerprint]) == len(new_hash[fingerprint]) == 1:
            x, y = old_hash[fingerprint][0], new_hash[fingerprint][0]
            identical.append({"before": x["id"], "after": y["id"],
                              "name_changed": x["method"] != y["method"],
                              "path_changed": x["file"] != y["file"]})
    same_name_changed_body = []
    for old in pre:
        matching = [q for q in post if q["method"] == old["method"]]
        if len(matching) == 1 and old["body_ast_sha256"] != matching[0]["body_ast_sha256"]:
            same_name_changed_body.append({"before": old["id"], "after": matching[0]["id"]})
    return {
        "pre_functions": len(pre), "post_functions": len(post),
        "pre_duplicate_names": sum(v > 1 for v in old_count.values()),
        "post_duplicate_names": sum(v > 1 for v in new_count.values()),
        "unique_identical_body_lineages": len(identical),
        "identical_body_moved_paths": sum(x["path_changed"] for x in identical),
        "identical_body_renamed_methods": sum(x["name_changed"] for x in identical),
        "verified_identical_body_links": identical,
        "unique_name_with_modified_body_count": len(same_name_changed_body),
        "same_name_body_changed_examples": same_name_changed_body[:30],
    }


def parse_junit(xml_path: Path) -> list[dict]:
    result = []
    root = ET.parse(xml_path).getroot()
    for tc in root.findall(".//testcase"):
        cls = tc.attrib.get("classname", "")
        name = tc.attrib.get("name", "")
        state = "passed"
        for attr in ("failure", "error", "skipped"):
            if tc.find(attr) is not None:
                state = attr
                break
        result.append({"node": cls + "::" + name, "state": state,
                       "duration_seconds": tc.attrib.get("time", "")})
    return result


def write_csv(path: Path, rows: list[dict]):
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def run(data: Path, out: Path, repeats: int, only: list[str]):
    # Child pytest processes change cwd to the source checkout. All inputs,
    # especially PYTHONPATH, must therefore use absolute paths.
    data = data.resolve()
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    run_rows, test_rows, source_records, case_summaries = [], [], [], []
    included = [c for c in CASES if not only or c["id"] in only]
    if len(included) != (len(only) if only else len(CASES)):
        raise ValueError(f"Unknown case in {only}")
    for case in included:
        pre_repo, post_repo = data / case["pre_dir"], data / case["post_dir"]
        checked_sha(pre_repo, case["pre"])
        checked_sha(post_repo, case["commit"])
        old_functions = source_functions(pre_repo, case["pre_sources"])
        new_functions = source_functions(post_repo, case["post_sources"])
        source_records.extend({"case": case["id"], "revision": rev, **row}
                              for rev, items in (("pre", old_functions), ("post", new_functions)) for row in items)
        summaries = summarize_source(old_functions, new_functions)
        summaries.update({"case": case["id"], "project": case["project"],
                          "pre_sha": case["pre"], "post_sha": case["commit"],
                          "developer_change_annotation": case["annotation"]})
        if case["id"] == "click-case-split-2025":
            x = next(x for x in old_functions if x["method"] == "test_with_resource_exception")
            y = next(x for x in new_functions if x["method"] == "test_with_resource_exception")
            z = next(x for x in new_functions if x["method"] == "test_with_resource_nested_exception")
            assert x["has_nested_resource"] and not y["has_nested_resource"] and z["has_nested_resource"]
            summaries["observed_test_method_split"] = {
                "before": x["id"], "after": [y["id"], z["id"]],
                "evidence": "nested resource checks moved from original test into a newly introduced method",
                "safe_1_to_1_history_transfer": False,
            }
        if case["id"] == "markupsafe-semantic-extension-2022":
            x = next(x for x in old_functions if x["method"] == "test_escaping")
            y = next(x for x in new_functions if x["method"] == "test_escaping")
            assert x["full_source_sha256"] != y["full_source_sha256"]
            summaries["observed_semantic_change"] = {
                "before": x["id"], "after": y["id"],
                "evidence": "commit adds multiline comments and newline-in-tag cases to existing test",
                "wrong_transfer_was_observed": False,
            }
        case_summaries.append(summaries)
        for revision, repo, target in (("pre", pre_repo, case["pre_target"]),
                                       ("post", post_repo, case["post_target"])):
            env = os.environ.copy()
            env["PYTHONPATH"] = str(repo / "src")
            env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
            env["PYTHONHASHSEED"] = "0"
            for repeat in range(repeats):
                with tempfile.TemporaryDirectory(prefix="n04-junit-") as temp:
                    junit = Path(temp) / "pytest.xml"
                    selected = list(target) if isinstance(target, tuple) else [target]
                    command = [sys.executable, "-m", "pytest", "-q", "--disable-warnings",
                               "-o", "cache_dir=" + temp + "/cache", "--junitxml", str(junit), *selected]
                    t0 = time.perf_counter()
                    proc = subprocess.run(command, cwd=repo, env=env,
                                          capture_output=True, text=True, timeout=120)
                    elapsed = time.perf_counter() - t0
                    if not junit.is_file():
                        raise RuntimeError(f"Missing junit for {case['id']} {revision} repeat={repeat}: {proc.stderr[-900:]}")
                    parsed = parse_junit(junit)
                state_counts = collections.Counter(x["state"] for x in parsed)
                run_rows.append({
                    "case": case["id"], "project": case["project"],
                    "revision": revision, "git_sha": case["pre"] if revision == "pre" else case["commit"],
                    "repeat": repeat, "returncode": proc.returncode,
                    "observed_testcases": len(parsed), "passed": state_counts["passed"],
                    "skipped": state_counts["skipped"], "failed": state_counts["failure"],
                    "error": state_counts["error"], "elapsed_seconds": round(elapsed, 5),
                    "stdout_sha256": sha(proc.stdout.encode()),
                    "stderr_sha256": sha(proc.stderr.encode()),
                    "python": platform.python_version(), "pytest": "8.4.2",
                })
                test_rows.extend({"case": case["id"], "revision": revision, "repeat": repeat,
                                  "git_sha": case["pre"] if revision == "pre" else case["commit"], **x}
                                 for x in parsed)
            print(case["id"], revision, repeats, "runs", state_counts, flush=True)
    write_csv(out / "real_pytest_runs.csv", run_rows)
    write_csv(out / "real_pytest_testcase_outcomes.csv", test_rows)
    write_csv(out / "source_test_signatures.csv", source_records)
    result = {
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source": "Real, immutable historical source revisions in two external projects; no upstream CI job modified",
        "total_pytest_invocations": len(run_rows),
        "total_recorded_testcase_executions": len(test_rows),
        "all_invocations_exited_zero": all(r["returncode"] == 0 for r in run_rows),
        "cases": case_summaries,
        "limits": ["PYTEST results are local replays, not the original project's CI runs.",
                   "Module splitting and individual test-case splitting are different events.",
                   "Source-equivalent links do not establish equality of fixture/environment semantics.",
                   "A same-name test gaining new assertions is risk evidence, not an observed false CI outcome."]}
    (out / "cross_repo_summary.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data", type=Path, default=Path("data"))
    p.add_argument("--out", type=Path, default=Path("results/cross_repo_pytest"))
    p.add_argument("--repeats", type=int, default=10)
    p.add_argument("--only", nargs="*", default=[])
    args = p.parse_args()
    if args.repeats < 1:
        p.error("--repeats must be positive")
    d = run(args.data, args.out, args.repeats, args.only)
    print(json.dumps({k: d[k] for k in ("total_pytest_invocations",
                                      "total_recorded_testcase_executions",
                                      "all_invocations_exited_zero")}, indent=2))


if __name__ == "__main__":
    main()
