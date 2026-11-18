"""Ingest the public FTW 2024 repeated-regression-test-history data.

Only measured outcomes from the archived CSV files are accepted here.  This
module never fabricates test results, and never equates an absent test with a
passing test.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import json
import lzma
from pathlib import Path


RESULTS = ("passed", "failure", "error", "skipped")


def ingest(input_dir: Path) -> dict:
    files = sorted(input_dir.glob("*_test_results_*.csv.xz"))
    if not files:
        raise FileNotFoundError(f"No published CSV.xz files in {input_dir}")

    # project_key -> commit -> full test ID -> status counts
    data = defaultdict(lambda: defaultdict(lambda: defaultdict(Counter)))
    commit_times = defaultdict(lambda: defaultdict(list))
    per_file_rows = Counter()
    unusual_results = Counter()
    project_url = {}
    for file in files:
        run_key = file.name.split("_test_results_")[0]
        with lzma.open(file, "rt", encoding="utf-8", newline="") as stream:
            for row in csv.DictReader(stream):
                repo = row["Slug"].replace("https://github.com/", "")
                mod = row["module name"]
                key = run_key
                project_url[key] = {"repository": repo, "module": mod}
                commit = row["commit hash"]
                test = f'{row["test suite name"]}::{row["test case name"]}'
                result = row["test result"]
                if result not in RESULTS:
                    unusual_results[result] += 1
                data[key][commit][test][result] += 1
                per_file_rows[key] += 1
                # The first of 30 repetitions gives a useful *execution*
                # chronology. This is not claimed to be the git ancestry.
                if file.name.endswith("_1.csv.xz"):
                    commit_times[key][commit].append(int(row["timeStamp"]))

    projects = {}
    summary = []
    transition_rows = []
    for key, commits in sorted(data.items()):
        ordered_commits = sorted(
            commits,
            key=lambda c: (min(commit_times[key].get(c, [2**63])), c),
        )
        all_test_names = set()
        flaky_name_commits = set()
        for commit in ordered_commits:
            for name, outcomes in commits[commit].items():
                all_test_names.add(name)
                if outcomes["passed"] > 0 and (outcomes["failure"] + outcomes["error"] > 0):
                    flaky_name_commits.add(name)

        project_transitions = []
        for previous, following in zip(ordered_commits, ordered_commits[1:]):
            a, b = set(commits[previous]), set(commits[following])
            vanished, appeared = sorted(a - b), sorted(b - a)
            if vanished or appeared:
                row = {
                    "project": key,
                    "before": previous,
                    "after": following,
                    "vanished": vanished,
                    "appeared": appeared,
                    "vanished_count": len(vanished),
                    "appeared_count": len(appeared),
                }
                project_transitions.append(row)
                transition_rows.append(row)
        projects[key] = {
            **project_url[key],
            "commits": [
                {
                    "hash": c,
                    "executed_at": min(commit_times[key].get(c, [0])),
                    "tests": {n: dict(statuses) for n, statuses in sorted(commits[c].items())},
                }
                for c in ordered_commits
            ],
            "transitions": project_transitions,
        }
        summary.append({
            "project": key,
            **project_url[key],
            "n_commits": len(ordered_commits),
            "n_distinct_tests": len(all_test_names),
            "n_flaky_test_ids": len(flaky_name_commits),
            "n_status_observations": per_file_rows[key],
            "n_transitions_with_id_churn": len(project_transitions),
            "n_possible_one_to_one_churn": sum(
                bool(x["vanished_count"] and x["appeared_count"])
                for x in project_transitions
            ),
        })
    return {
        "source": "https://doi.org/10.5281/zenodo.10639030",
        "test_result_semantics": "30 observed reruns per commit; this study is an offline regression-history replay, not deployed CI",
        "files": len(files),
        "unexpected_results": dict(unusual_results),
        "summary": summary,
        "transitions": transition_rows,
        "projects": projects,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    output = ingest(a.input)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps({"source_files": output["files"], "summary": output["summary"]}, indent=2))


if __name__ == "__main__":
    main()
