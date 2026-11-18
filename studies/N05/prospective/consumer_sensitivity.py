#!/usr/bin/env python3
"""Post-hoc industrial applicability of examples using hidden test fixtures.

Not a preregistered primary subset. `sea_query::tests_cfg` is explicitly
`#[doc(hidden)]` and available only under the `tests-cfg` Cargo feature in the
exact published sea-query 0.32.5 src/lib.rs.
"""
import json
from pathlib import Path
import re
import statistics

from validate import bootstrap

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent

FIXTURE_IMPORT = re.compile(r"\b(?:tests_cfg|test_helpers|test_utils)\s*::")


def read_jsonl(path):
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()] if path.exists() else []


def summary(rows):
    if not rows:
        return None
    diagnostic_delta = [dict(r, diagnostic_minus_guided_attempts=r["diagnostic_attempts"] - r["guided_attempts"])
                        for r in rows if r["diagnostic_attempts"] is not None]
    return {"case_count":len(rows),"repo_count":len({r["repo"] for r in rows}),
            "guided_success_at_8":round(statistics.mean(r["guided_success"] for r in rows),4),
            "random_success_at_8":round(statistics.mean(r["random_success"] for r in rows),4),
            "guided_minus_random":round(statistics.mean(r["gain"] for r in rows),4),
            "project_cluster_95ci_guided_minus_random":bootstrap(rows,"gain"),
            "mean_guided_additional_compilations":round(statistics.mean(r["guided_attempts"] for r in rows),4),
            "mean_random_additional_compilations":round(statistics.mean(r["random_attempts"] for r in rows),4),
            "pathaware_success_at_8":round(statistics.mean(r["pathaware_success"] for r in rows),4)
              if all(r["pathaware_success"] is not None for r in rows) else None,
            "diagnostic_success_at_8":round(statistics.mean(r["diagnostic_success"] for r in rows),4)
              if all(r["diagnostic_success"] is not None for r in rows) else None,
            "diagnostic_minus_guided_project_ci":bootstrap(rows,"diagnostic_minus_guided")
              if all(r["diagnostic_minus_guided"] is not None for r in rows) else None,
            "mean_compiler_diagnostic_additional_compilations":round(statistics.mean(r["diagnostic_attempts"] for r in rows),4)
              if all(r["diagnostic_attempts"] is not None for r in rows) else None,
            "compiler_minus_guided_additional_compilations":round(statistics.mean(x["diagnostic_minus_guided_attempts"] for x in diagnostic_delta),4)
              if len(diagnostic_delta)==len(rows) else None,
            "compiler_minus_guided_compilation_project_cluster_ci":bootstrap(diagnostic_delta,"diagnostic_minus_guided_attempts")
              if len(diagnostic_delta)==len(rows) else None,
            }


def main():
    b = json.loads((HERE / "results/independent_validation.json").read_text())
    all_cases = b["individual_positive_cases"]
    corpus = {r["id"]:r for r in read_jsonl(HERE / "data/corpus.jsonl")}
    excluded = [r for r in all_cases if FIXTURE_IMPORT.search(corpus[r["id"]]["compiled_code"])]
    retained = [r for r in all_cases if r not in excluded]
    if any(x["crate"] != "sea-query" for x in excluded):
        print("WARN: other crates match generic hidden-fixture import; inspect manually")
    result = {
        "type": "post_hoc_consumer_relevance_sensitivity_not_preregistered",
        "test_fixture_source_evidence": "sea-query 0.32.5 src/lib.rs: #[doc(hidden)] #[cfg(feature = \"tests-cfg\")] pub mod tests_cfg;",
        "hidden_test_fixture_release": "https://static.crates.io/crates/sea-query/sea-query-0.32.5.crate",
        "caveat": "Excluding a docs-only test fixture dependency avoids interpreting a doctest repair as a meaningful consumer Cargo.toml patch. The full pre-registered result is retained unchanged.",
        "excluded": [{"id":x["id"], "crate":x["crate"], "repo":x["repo"]} for x in excluded],
        "full_preregistered_cohort":summary(all_cases),
        "after_excluding_explicit_test_fixture_import":summary(retained),
        "exclusion_count":len(excluded),
    }
    target = HERE / "results/consumer_sensitivity.json"
    target.write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps(result,indent=2))


if __name__ == "__main__":
    main()
