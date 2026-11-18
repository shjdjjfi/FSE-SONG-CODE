"""Independently audit N04 frozen public-data outputs without source downloads.

Usage (from the package root):
  python3 src/verify_frozen.py
  python3 src/verify_frozen.py --make-checksums   # release maintainer only

The checksums cover only files under src/tests/results/figures. The checksum
manifest is intentionally excluded from its own digest.
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
from pathlib import Path


def ensure(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def get_json(path: Path):
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def close(actual: float, expected: float, description: str) -> None:
    ensure(abs(actual - expected) < 1e-12, f"{description}: {actual} != {expected}")


def check_migration(root: Path) -> None:
    d = root / "results/migration_benchmark"
    j = get_json(d / "results.json")
    ensure(j["audit"]["counts"]["unique_pairs"] == 875, "source inclusion audit")
    ensure(len(j["per_seed"]) == 3, "seed count")
    counts = collections.defaultdict(lambda: collections.Counter())
    with (d / "predictions.csv").open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            c = counts[r["method"]]
            c["pairs"] += 1
            c["recovered"] += r["present_pred"] == r["uid"]
            c["wrong_matched"] += bool(r["present_pred"]) and r["present_pred"] != r["uid"]
            c["wrong_absent"] += bool(r["absent_pred"])
    ensure(set(counts) == set(j["summary"]), "complete baseline/ablation arms")
    for arm, c in counts.items():
        published = j["summary"][arm]
        ensure(c["pairs"] == published["pairs"] == 842 * 3, f"{arm}: samples")
        for key in ("recovered", "wrong_matched", "wrong_absent"):
            ensure(c[key] == published[key], f"{arm}: {key}")
        close(c["recovered"] / c["pairs"], published["recovery_rate"], f"{arm}: recall")
        close((c["wrong_matched"] + c["wrong_absent"]) / (2 * c["pairs"]),
              published["combined_false_transfer_rate"], f"{arm}: false transfer")
    ensure(counts["method_name"]["recovered"] == 2436, "strong baseline count")
    ensure(counts["semantic_anchor"]["recovered"] == 1238, "model candidate count")
    print("PASS identity benchmark: 8 arms x 2,526 paired-query predictions, no silent exclusions")


def check_history(root: Path) -> None:
    j = get_json(root / "results/history_replay/history_results.json")
    audit = j["real_outcome_statistics"]
    ensure(j["audit"]["total_csv_rows"] == 4654230, "upstream execution rows")
    ensure(audit["fully_observed_non_skip_30_runs"] == 148211, "non-skipped units")
    expected = {int(v["seed"]): v for v in j["summary"]["by_seed"]}
    counter = collections.defaultdict(collections.Counter)
    with (root / "results/history_replay/real_history_decisions.csv").open(
            newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            s = int(r["seed"])
            c = counter[s]
            c["all_tests"] += 1
            c["global_flaky"] += r["globally_flaky_30"] == "True"
            c["future_flaky"] += r["future_flaky_10"] == "True"
            c["quarantine_preserved"] += r["preserved_quarantine"] == "True"
            c["quarantine_reset"] += r["reset_quarantine"] == "True"
            c["future_flaky_missed_preserved"] += int(r["future_flaky_missed_preserved"])
            c["future_flaky_missed_reset"] += int(r["future_flaky_missed_reset"])
    ensure(set(counter) == {17, 29, 43}, "history replay seeds")
    for seed, count in counter.items():
        for name, value in count.items():
            ensure(value == expected[seed][name], f"history seed {seed} {name}")
    print("PASS authentic outcome replay: 444,633 frozen decisions across 3 seeds")


def check_pytest(root: Path) -> None:
    scenarios = {"function_rename": (3, 1), "file_move": (3, 1),
                 "parameter_ids": (3, 1), "semantic_change": (1, 0),
                 "split": (4, 0)}
    for version in ("7.4.4", "8.4.2", "9.0.1"):
        p = get_json(root / f"results/pytest_behavior/pytest_{version}.json")
        ensure(p["pytest_version"] == version, "pytest version lock")
        ensure({s["scenario"] for s in p["scenarios"]} == set(scenarios), "pytest scenarios")
        for case in p["scenarios"]:
            after, bridge = scenarios[case["scenario"]]
            prefix = f"pytest {version} {case['scenario']}"
            ensure(case["same_identity_selection"]["collected_count"] == 1, prefix + " before")
            ensure(case["after_edit_selection"]["collected_count"] == after, prefix + " after")
            ensure(case["after_bridge_selection"]["collected_count"] == bridge, prefix + " bridge")
            ensure(case["empty_cache_control"]["collected_count"] == 0, prefix + " empty control")
    print("PASS actual pytest collections: 3 versions x 5 interventions")


def check_java(root: Path) -> None:
    j = get_json(root / "results/java_before_after/before_after_results.json")
    ensure(j["complete_40_case_mapping"], "source-mapped 40 cases complete")
    ensure(j["old_sha"] == "27e26758d6604f5d078709233028bb87b4a39e16", "old Git lock")
    ensure(j["new_sha"] == "2ce6e6149d0ef44f4919e75326265c64c144a00f", "new Git lock")
    case_names = {}
    for version in ("pre", "post"):
        path = root / f"results/java_{version}_30_complete/junit_cases.csv"
        counter = collections.Counter()
        bad = 0
        test_names = set()
        with path.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                iteration = int(r["iteration"])
                ensure(1 <= iteration <= 30, "JUnit repeat range")
                ensure(r["status"] in ("passed", "failed", "error", "skipped"), "JUnit outcome type")
                counter[iteration] += 1
                bad += r["status"] not in ("passed", "skipped")
                test_names.add((r["class"], r["test"]))
        ensure(set(counter) == set(range(1, 31)), f"{version} complete repeat indices")
        ensure(all(count == 40 for count in counter.values()), f"{version} 40 executions per round")
        ensure(len(test_names) == 40, f"{version} 40 unique JUnit IDs")
        ensure(bad == j["summaries"]["ALL"][f"{version}_nonpass"], f"{version} failure total")
        case_names[version] = test_names
    with (root / "results/java_before_after/before_after_40_cases.csv").open(
            newline="", encoding="utf-8") as f:
        cases = list(csv.DictReader(f))
    ensure(len(cases) == 40, "all case-map rows")
    ensure(all((r["class"], r["old_test"]) in case_names["pre"] and
               (r["class"], r["new_test"]) in case_names["post"] for r in cases),
           "source-derived mapping joins observed JUnit IDs")
    ensure(sum(r["pre_flaky"] == "True" for r in cases) == 5, "old flaky cases")
    ensure(sum(r["post_flaky"] == "True" for r in cases) == 6, "new flaky cases")
    l = get_json(root / "results/java_lineage/java_param_lineage_results.json")
    ensure(l["independent_idoft_moved_records"] == 27 and
           l["matching_independent_idoft_records"] == 27, "independent IDoFT validation")
    print("PASS real Java revisions: 1,200+1,200 JUnit executions, 40 joins, 27 IDoFT labels")


def check_figures(root: Path) -> None:
    for number in range(1, 5):
        for suffix in ("pdf", "png"):
            matches = list((root / "figures").glob(f"fig{number:02d}_*.{suffix}"))
            ensure(len(matches) == 1 and matches[0].stat().st_size > 10_000,
                   f"figure {number} {suffix}")
    print("PASS figures: 4 vector PDF + 4 PNG exports")


def check_extended_ci_events(root: Path) -> None:
    ledger = get_json(root / "results/real_ci_events/public_event_ledger.json")
    gitlab = {x["iid"]: x for x in ledger["gitlab"]["merge_requests"]}
    ensure(set(gitlab) == {162803, 164022, 195179, 228726, 149942, 155883},
           "GitLab real MRs enumerated")
    ensure(all(x["state"] == "merged" for x in gitlab.values()), "GitLab verified merge statuses")
    ensure(gitlab[162803]["quarantine_additions"] == 1 and
           gitlab[164022]["quarantine_removals"] == 1, "real same-test flag transitions")
    ensure(gitlab[162803]["files"][0]["added_test_descriptions"] ==
           gitlab[164022]["files"][0]["removed_test_descriptions"],
           "exact same test method name in source transition")
    aspire = {x["number"]: x for x in ledger["github"]["pull_requests"]}
    ensure(set(aspire) == {13874, 14040, 9023} and
           all(x["merged_at"] for x in aspire.values()), "Aspire real merged PRs")
    ensure([aspire[k]["quarantine_removals"] for k in (13874, 14040, 9023)] ==
           [17, 11, 4], "Aspire changed quarantine annotation counts")
    ensure(159 in aspire[13874]["claimed_runs_in_description"] and
           215 in aspire[14040]["claimed_runs_in_description"],
           "developer-reported repeated-run claims in PR descriptions")
    chain = get_json(root / "results/real_ci_events/gitlab_fix_action_chain.json")
    ensure([x["iid"] for x in chain["events"]] == [162803, 163832, 164022],
           "observed quarantine/fix/unquarantine chronological chain")
    ensure([x["merged_at"] for x in chain["events"]] ==
           sorted(x["merged_at"] for x in chain["events"]),
           "chronological merges")
    print("PASS 6 public GitLab actions + 3 Aspire PRs + 3-stage remediation chain; no CI causal claim")


def check_cross_repo_python(root: Path) -> None:
    d = root / "results/cross_repo_pytest"
    summary = get_json(d / "cross_repo_summary.json")
    ensure(summary["total_pytest_invocations"] == 80, "new Python process runs")
    ensure(summary["total_recorded_testcase_executions"] == 4990, "recorded real test cases")
    ensure(summary["all_invocations_exited_zero"], "all new historical checkouts ran")
    cases = {x["case"]: x for x in summary["cases"]}
    ensure(len(cases) == 4, "four historical migration situations")
    ensure(cases["click-case-split-2025"]["observed_test_method_split"]["safe_1_to_1_history_transfer"]
           is False, "authentic one-to-many test case")
    ensure(cases["markupsafe-semantic-extension-2022"]["observed_semantic_change"]
           ["wrong_transfer_was_observed"] is False, "semantic test extension != wrong CI action")
    counts = collections.defaultdict(collections.Counter)
    with (d / "real_pytest_runs.csv").open(newline="", encoding="utf-8") as f:
        runs = list(csv.DictReader(f))
    with (d / "real_pytest_testcase_outcomes.csv").open(newline="", encoding="utf-8") as f:
        tests = list(csv.DictReader(f))
    ensure(len(runs) == 80 and len(tests) == 4990, "full run + case traces retained")
    for row in runs:
        c = counts[(row["case"], row["revision"])]
        c["repeats"] += 1
        c["observed"] += int(row["observed_testcases"])
        ensure(int(row["returncode"]) == 0 and int(row["failed"]) == 0 and
               int(row["error"]) == 0, "passed historical pytest invocation")
    expected = {
        ("click-case-split-2025", "pre"): 1,
        ("click-case-split-2025", "post"): 2,
        ("click-module-split-types-2026", "pre"): 75,
        ("click-module-split-types-2026", "post"): 67,
        ("click-module-split-utils-2026", "pre"): 148,
        ("click-module-split-utils-2026", "post"): 148,
        ("markupsafe-semantic-extension-2022", "pre"): 29,
        ("markupsafe-semantic-extension-2022", "post"): 29,
    }
    ensure(set(counts) == set(expected), "all historical scenario/revision sides")
    for key, n in expected.items():
        ensure(counts[key]["repeats"] == 10 and counts[key]["observed"] == 10*n,
               f"historical testcase counts {key}")
    ensure(all(row["state"] in ("passed", "skipped") for row in tests),
           "JUnit per-test outcomes match run summaries")
    print("PASS cross-repository historical Python: 80 processes, 4,990 actual testcase executions")


def check_new_baselines(root: Path) -> None:
    strong = get_json(root / "results/strong_baselines/results.json")
    hier = get_json(root / "results/hierarchical_linker/results.json")
    external = get_json(root / "results/icpc2021_rename_probe/results.json")
    ensure(strong["summary"]["method_name"]["recovered"] == 2436,
           "original exact-name baseline reproduced in new comparison")
    ensure(strong["summary"]["name_body_tiebreak"]["recovered"] == 2460,
           "stronger simple baseline counts")
    ensure(hier["summary"]["hierarchical_case"]["recovered"] == 2481,
           "exploratory conditional case-normalization counts")
    ensure(hier["summary"]["hierarchical_case"]["wrong_absent"] == 33,
           "false-positive cost unchanged vs stronger baseline")
    ensure(external["audit"]["unique_refactoring_ids"] == 293 and
           external["audit"]["total_sheet_rows"] == 398,
           "external published rename dataset counts")
    ensure(external["audit"]["polarity_flip_warnings"] == 15,
           "negation-risk examples counted")
    for file, methods, rows_per_method, key in (
        (root / "results/strong_baselines/predictions.csv", strong["summary"], 2526, "uid"),
        (root / "results/hierarchical_linker/predictions.csv", hier["summary"], 2526, "uid"),
        (root / "results/icpc2021_rename_probe/predictions.csv", external["method_results"], 879, "id"),
    ):
        bymethod = collections.defaultdict(list)
        with file.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                bymethod[row["method"]].append(row)
        ensure(set(bymethod) == set(methods), "complete extension method arms")
        for method, rows in bymethod.items():
            ensure(len(rows) == rows_per_method, f"extension method sample count: {method}")
            got = sum(r.get("present_pred", r.get("pred")) == r[key] for r in rows)
            ensure(got == methods[method]["recovered"], f"extended method recoveries: {method}")
    print("PASS exploratory new risk-aware baselines and 293 independent annotated rename names")


def checksum_paths(root: Path):
    for directory in ("src", "tests", "results", "figures"):
        for path in sorted((root / directory).rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
                yield path


def check_checksums(root: Path, make: bool) -> None:
    path = root / "RESULT_CHECKSUMS.json"
    if make:
        digest = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in checksum_paths(root)}
        path.write_text(json.dumps({"sha256": digest}, indent=2) + "\n", encoding="utf-8")
        print(f"FROZEN {len(digest)} source, figure, report-source and result file checksums")
    else:
        expected = get_json(path)["sha256"]
        actual = {str(p.relative_to(root)) for p in checksum_paths(root)}
        ensure(actual == set(expected), "checksum file set differs from release")
        for rel, sha in expected.items():
            ensure(hashlib.sha256((root / rel).read_bytes()).hexdigest() == sha,
                   f"checksum mismatch: {rel}")
        print(f"PASS integrity: {len(expected)} SHA-256 frozen file digests")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--make-checksums", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    check_migration(root)
    check_history(root)
    check_pytest(root)
    check_java(root)
    check_figures(root)
    check_extended_ci_events(root)
    check_cross_repo_python(root)
    check_new_baselines(root)
    check_checksums(root, args.make_checksums)
    print("ALL FROZEN EXPERIMENT AUDITS PASSED")


if __name__ == "__main__":
    main()
