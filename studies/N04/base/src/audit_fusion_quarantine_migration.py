"""Real, source-linked file-level quarantine identity migration in Fusion.

This audit reads committed ledger, runner configuration and test sources on
both sides of one maintainer-authored commit. It does NOT invent CI outcomes,
reruns, or runtime savings. Counterfactual policies are clearly static.
"""

from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import subprocess


SHA="b5450832494d24e4171acea606b4c022a5a8475b"
OLD="packages/cli/src/__tests__/extension.test.ts"
NEW="packages/cli/src/__tests__/extension-dist-barrel.test.ts"
LEDGER="scripts/lib/test-quarantine.json"
CONFIG="packages/cli/vitest.config.ts"
ACTION_URL="https://github.com/Runfusion/Fusion/actions/runs/28697507894"
TEST_TITLE="executes with @fusion/core resolved through the built dist barrel"


def git(repo,*args):
    p=subprocess.run(["git","-C",str(repo),*args],capture_output=True)
    if p.returncode:raise RuntimeError(p.stderr.decode(errors="replace")[:200])
    return p.stdout.decode("utf-8",errors="replace")


def show(repo,sha,path):
    try:return git(repo,"show",sha+":"+path)
    except RuntimeError:return None


def methods_count(text):
    if text is None:return 0
    # Source declarations, not a test-runner collection count.
    return len(re.findall(r"(?m)^\s*it(?:\.skipIf|\.skip|\.only|\.todo|\.each)?\s*\(",text))


def find_entry(text,identifier):
    matches=[x for x in json.loads(text)["entries"] if x.get("file")==identifier]
    if len(matches)!=1:raise ValueError(f"expected one ledger entry: {identifier}")
    return matches[0]


def expect_lines(text,start_at):
    # Only inside the moved case's remaining source section; assertion strings
    # are compared as normalized source lines, not inferred semantics.
    start=text.index(TEST_TITLE,start_at)
    section=text[start:]
    next_it=re.search(r"(?m)^\s*it(?:\.skipIf|\.skip|\.only)?\s*\(",section[10:])
    if next_it:section=section[:10+next_it.start()]
    return sorted(re.sub(r"\s+","",x) for x in section.splitlines() if "expect(" in x)


def audit(repo):
    parent=git(repo,"rev-parse",SHA+"^1").strip()
    actual=git(repo,"rev-parse",SHA).strip()
    b=json.loads(show(repo,parent,LEDGER));a=json.loads(show(repo,actual,LEDGER))
    old_before=find_entry(json.dumps(b),OLD)
    new_after=find_entry(json.dumps(a),NEW)
    old_before_excluded=bool(re.search(r'"src/__tests__/extension\.test\.ts"\s*,',show(repo,parent,CONFIG)))
    new_after_excluded=bool(re.search(r'"src/__tests__/extension-dist-barrel\.test\.ts"\s*,',show(repo,actual,CONFIG)))
    old_after_excluded=bool(re.search(r'"src/__tests__/extension\.test\.ts"\s*,',show(repo,actual,CONFIG)))
    old_before_source=show(repo,parent,OLD)
    old_after_source=show(repo,actual,OLD)
    new_after_source=show(repo,actual,NEW)
    old_asserts=expect_lines(old_before_source,old_before_source.index("it.skipIf"))
    new_asserts=expect_lines(new_after_source,new_after_source.index("it.skipIf"))
    evidence={"repository":"https://github.com/Runfusion/Fusion",
              "migration_commit":actual,"parent":parent,
              "maintainer_commit_subject":git(repo,"show","-s","--format=%s",SHA).strip(),
              "source_paths":{"before_quarantined":OLD,"after_quarantined":NEW,"after_restored":OLD},
              "decision_provenance":{"ledger_before":{"file":OLD,"quarantinedAt":old_before.get("quarantinedAt")},
                                      "ledger_after":{"file":NEW,"quarantinedAt":new_after.get("quarantinedAt")},
                                      "same_action_run_in_reasons":ACTION_URL in old_before["reason"] and ACTION_URL in new_after["reason"],
                                      "linked_actions_run":ACTION_URL,
                                      "actual_before_excluded":old_before_excluded,
                                      "actual_after_new_excluded":new_after_excluded,
                                      "actual_after_old_not_excluded":not old_after_excluded},
              "identity_confirmation":{"same_single_test_title_before_after":TEST_TITLE in old_before_source and TEST_TITLE in new_after_source,
                                       "source_assertion_lines_equal":old_asserts==new_asserts,
                                       "assertion_statement_lines":len(old_asserts),
                                       "new_file_contains_single_it_declaration":methods_count(new_after_source)==1},
              "source_declared_test_counts":{"old_file_before":methods_count(old_before_source),
                                             "old_file_after":methods_count(old_after_source),
                                             "new_file_after":methods_count(new_after_source)},
              "reported_by_maintainer":{"approximately_stable_tests_collaterally_excluded":68,
                                        "loaded_shard_timeout_ms":5000,
                                        "local_runtime_approx_ms":1200,
                                        "passes_in_nearby_four_ci_runs":3,
                                        "source":"Git commit b545083 and source-controlled ledger notes; not independently downloaded CI job results"},
              "policy_counterfactual":{"exact_file_id_without_manual_update":"Would leave the new file without matched old exclusion, unless explicitly re-quarantined",
                                       "observed_actual_policy":"Quarantine moved to new file and original file re-admitted",
                                       "not_observed":"No matched GitHub Actions full workflow timeline, rerun count, build spend, or before-after CI duration obtained"},
              "scope_limit":"One source-controlled, file-level split/partial quarantine, not an independently replicated N04 Java method-history deployment"}
    if not all([old_before_excluded,new_after_excluded,not old_after_excluded,
                evidence["decision_provenance"]["same_action_run_in_reasons"],
                evidence["identity_confirmation"]["same_single_test_title_before_after"]]):
        raise AssertionError("Quarantine link is not established; inspect commit")
    return evidence


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--repo",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    evidence=audit(a.repo)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(evidence,indent=2),encoding="utf-8")
    print(json.dumps({"source_declared_test_counts":evidence["source_declared_test_counts"],
                      "identity_confirmation":evidence["identity_confirmation"],
                      "decision_provenance":evidence["decision_provenance"]},indent=2))
