"""Compare ID lineage methods on source-verified natural Java refactors."""

import argparse
from collections import Counter, defaultdict
from difflib import SequenceMatcher
import json
from pathlib import Path

from java_source import file_path_for_name, java_test_diff, methods_at, run_git


def predict(case: dict, new_methods: list, strategy: str) -> str | None:
    old_method = case["old"].split("::")[-1]
    old_body = case["old_body_hash"]
    candidates = [m for m in new_methods if (m.classname + "::" + m.name) != case["old"]]
    if strategy == "exact_id":
        return None  # by construction these are all changed IDs
    if strategy == "git_path_and_method":
        return None  # no Java class-level file rename in this control sample
    if strategy in ("body_fingerprint", "guarded"):
        match = [m for m in candidates if m.body_hash == old_body]
        if len(match) == 1:
            m = match[0]
            return m.classname + "::" + m.name
        return None
    ranked = sorted(
        ((SequenceMatcher(None, old_method, m.name).ratio(), m) for m in candidates),
        key=lambda x: (-x[0], x[1].fqn),
    )
    if not ranked:
        return None
    best_score, best = ranked[0]
    if strategy == "name_similarity":
        return best.classname + "::" + best.name if best_score >= .45 else None
    if strategy == "no_ambiguity_gate":
        return best.classname + "::" + best.name if best_score >= .30 else None
    raise ValueError(strategy)


def experiment(gold: dict, repos: dict[str, Path]) -> dict:
    rows = []
    baseline_names = ("exact_id", "git_path_and_method", "name_similarity",
                      "body_fingerprint", "no_ambiguity_gate", "guarded")
    for label in gold["labels"]:
        repo = str(repos[label["repository"]].resolve())
        before, after = label["before"], label["after"]
        entries, old_paths, new_paths = java_test_diff(repo, before, after)
        old_path = file_path_for_name(label["old"].replace("::", "."), old_paths)
        if not old_path:
            raise AssertionError(f"Couldn't find old method source: {label}")
        old_funcs = {m.classname + "::" + m.name:m
                     for m in methods_at(repo, before, old_path)}
        old = old_funcs.get(label["old"])
        if old is None:
            raise AssertionError(f"Old method absent in {old_path}: {label['old']}")
        changed_new = [m for p in new_paths for m in methods_at(repo, after, p)
                       if m.is_test]
        case = {**label, "old_body_hash": old.body_hash}
        for strategy in baseline_names:
            chosen = predict(case, changed_new, strategy)
            positive = label["decision"] == "transfer"
            correct = chosen == label["new"] if positive else chosen is None
            rows.append({"repository":label["repository"],
                         "event":label["repository"]+"@"+after,
                         "old":label["old"],"oracle_decision":label["decision"],
                         "oracle_new":label["new"],
                         "strategy":strategy,"predicted_new":chosen,
                         "correct":correct,
                         "true_transfer":positive and chosen == label["new"],
                         "wrong_transfer":bool(chosen is not None and chosen != label["new"])})
    summary = []
    for strategy in baseline_names:
        subset = [x for x in rows if x["strategy"] == strategy]
        true = sum(x["true_transfer"] for x in subset)
        wrong = sum(x["wrong_transfer"] for x in subset)
        false_on_negative = sum(x["wrong_transfer"] and x["oracle_decision"] != "transfer"
                                for x in subset)
        abstain = sum(x["predicted_new"] is None for x in subset)
        positives = sum(x["oracle_decision"] == "transfer" for x in subset)
        summary.append({"strategy":strategy,"cases":len(subset),
                        "gold_transfers":positives,"correct_transfers":true,
                        "wrong_transfers":wrong,"abstentions":abstain,
                        "false_transfers_on_negative": false_on_negative,
                        "recall":round(true / positives,4) if positives else None,
                        "false_transfer_rate_on_negative":round(false_on_negative /
                                                                  max(1,len(subset)-positives),4)})
    return {"scope":"six source-inspected test cases in three independent Git commits; not a production study",
            "rows":rows,"summary":summary}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--gold", type=Path, required=True)
    p.add_argument("--repo", nargs=2, action="append", required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    result = experiment(json.loads(a.gold.read_text()), {k: Path(v) for k,v in a.repo})
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2),encoding="utf-8")
    for row in result["summary"]:
        print(row)


if __name__ == "__main__":
    main()
