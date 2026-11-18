"""Counterfactual quarantine replay on *real* repeated test executions.

Input: 330 compressed CSV snapshots from Wendler & Winter (FTW 2024),
https://doi.org/10.5281/zenodo.10639030 . The outcomes are real; the
identity reset and false-transfer interventions are controlled counterfactuals.
This is NOT a reconstruction of actual CI quarantine actions.
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import lzma
import random
import re
import statistics
import time
from pathlib import Path


REPETITIONS = 30
SEEDS = (17, 29, 43)


def summarize(files: Path) -> tuple[dict, dict]:
    full = collections.defaultdict(lambda: [None] * REPETITIONS)
    duplicate = 0
    row_count = 0
    parse_failures = []
    by_project = collections.Counter()
    prefix_re = re.compile(r"(.+)_test_results_(\d+)\.csv\.xz$")
    all_files = sorted(files.glob("*.csv.xz"))
    for file in all_files:
        m = prefix_re.fullmatch(file.name)
        if m is None or not (1 <= int(m.group(2)) <= REPETITIONS):
            parse_failures.append(str(file))
            continue
        prefix, repeat = m.group(1), int(m.group(2)) - 1
        with lzma.open(file, mode="rt", encoding="utf-8", errors="replace", newline="") as f:
            for row in csv.DictReader(f):
                row_count += 1
                slug = row.get("Slug", "").strip()
                module = row.get("module name", "").strip()
                commit = row.get("commit hash", "").strip()
                suite = row.get("test suite name", "").strip()
                name = row.get("test case name", "").strip()
                status = row.get("test result", "").strip().lower()
                if not slug or not commit or not suite or not name:
                    continue
                key = (prefix, slug, module, commit, suite, name)
                if full[key][repeat] is not None:
                    duplicate += 1
                    if full[key][repeat] != status:
                        full[key][repeat] = "duplicate_conflict"
                else:
                    full[key][repeat] = status
                by_project[slug] += 1
    audit = {"files_read": len(all_files), "total_csv_rows": row_count,
             "distinct_test_commit_keys": len(full), "duplicate_key_per_repetition": duplicate,
             "unparseable_filenames": parse_failures,
             "rows_by_project": dict(by_project)}
    return dict(full), audit


def outcome(v: str | None) -> str | None:
    if v is None or v == "duplicate_conflict":
        return None
    if v == "passed":
        return "P"
    if v in ("failure", "failed", "error"):
        return "F"
    if v in ("skipped", "skip", "ignored"):
        return "S"
    return None


def is_flaky(sequence: list[str | None], *, min_count: int = 1) -> bool:
    good = sum(x == "P" for x in sequence)
    bad = sum(x == "F" for x in sequence)
    return good >= min_count and bad >= min_count


def outcome_statistics(values: dict) -> dict:
    classified = collections.Counter()
    complete = 0
    eligible = 0
    group = collections.defaultdict(set)
    for key, seq in values.items():
        states = [outcome(x) for x in seq]
        if all(x is not None for x in states):
            complete += 1
            if all(x != "S" for x in states):
                eligible += 1
        if is_flaky(states):
            classified["pass_fail_flaky"] += 1
        if all(x == "P" for x in states):
            classified["always_pass"] += 1
        if all(x == "F" for x in states):
            classified["always_fail"] += 1
        group[(key[0], key[3])].add((key[4], key[5]))
    return {"complete_30_runs": complete, "fully_observed_non_skip_30_runs": eligible,
            "class_counts": dict(classified), "commit_snapshots": len(group)}


def experiment(values: dict, seeds: tuple[int, ...]) -> tuple[list[dict], dict]:
    keys = sorted(k for k, v in values.items() if all(outcome(x) in ("P", "F") for x in v))
    eligible_flaky = [k for k in keys if is_flaky([outcome(x) for x in values[k]])]
    # This is a subset drawn using 30-repetition labels for descriptive purposes.
    # The replay decision uses ONLY the designated training outcomes.
    rng_data = collections.defaultdict(list)
    for k in keys:
        rng_data[k[:4]].append(k)

    rows = []
    for seed in seeds:
        detection = collections.Counter()
        costs = collections.Counter()
        # The permutation is fixed per seed and test (not adjusted for outcomes).
        for key in keys:
            seq = [outcome(x) for x in values[key]]
            rng = random.Random(int.from_bytes(hashlib.sha256(f"{seed}:{key}".encode()).digest()[:8], "big"))
            indices = list(range(REPETITIONS))
            rng.shuffle(indices)
            training = [seq[i] for i in indices[:20]]
            recent = training[-5:]
            future = [seq[i] for i in indices[20:]]
            preserved = is_flaky(training)
            reset = is_flaky(recent)
            reference = is_flaky(future)
            test_group = key[1]
            detection[(seed, test_group, "reference", reference)] += 1
            detection[(seed, test_group, "preserved", preserved)] += 1
            detection[(seed, test_group, "reset", reset)] += 1
            if reference:
                costs[(seed, test_group, "missed_reference", "preserved")] += int(not preserved)
                costs[(seed, test_group, "missed_reference", "reset")] += int(not reset)
            elif all(x == "P" for x in future):
                costs[(seed, test_group, "false_quarantine", "preserved")] += int(preserved)
                costs[(seed, test_group, "false_quarantine", "reset")] += int(reset)
            rows.append({"seed":seed,"project":key[1],"module":key[2],"commit":key[3],
                         "test_suite":key[4],"test_name":key[5],
                         "globally_flaky_30":is_flaky(seq),"future_flaky_10":reference,
                         "future_pass":future.count("P"),"future_fail":future.count("F"),
                         "preserved_quarantine":preserved,"reset_quarantine":reset,
                         "quarantine_lost":int(preserved and not reset),
                         "future_flaky_missed_preserved":int(reference and not preserved),
                         "future_flaky_missed_reset":int(reference and not reset)})
    summary = {
        "identities_complete_30":len(keys),
        "distinct_30_run_flaky":len(eligible_flaky),
        "events":len(rows),
        "rows_by_seed":{str(seed):len([r for r in rows if r["seed"] == seed]) for seed in seeds},
        "by_seed":[],
    }
    for seed in seeds:
        r = [x for x in rows if x["seed"] == seed]
        f = [x for x in r if x["globally_flaky_30"]]
        t = [x for x in r if x["future_flaky_10"]]
        summary["by_seed"].append({
            "seed":seed,"all_tests":len(r), "global_flaky":len(f), "future_flaky":len(t),
            "quarantine_preserved":sum(x["preserved_quarantine"] for x in r),
            "quarantine_reset":sum(x["reset_quarantine"] for x in r),
            "quarantine_lost_on_reset":sum(x["quarantine_lost"] for x in r),
            "future_flaky_missed_preserved":sum(x["future_flaky_missed_preserved"] for x in r),
            "future_flaky_missed_reset":sum(x["future_flaky_missed_reset"] for x in r),
        })
    # The false-inheritance intervention considers unmatched, always-passing
    # target tests with an old flaky source in the same real module and commit.
    # This is a controlled negative linking experiment (not observed renaming).
    by_group = collections.defaultdict(list)
    for key in keys:
        by_group[key[:4]].append(key)
    false_pair_examples = []
    for group, members in sorted(by_group.items()):
        flaky = [k for k in members if is_flaky([outcome(x) for x in values[k]])]
        stable = [k for k in members if all(outcome(x) == "P" for x in values[k])]
        if not flaky or not stable:
            continue
        for source in flaky:
            r = random.Random(int.from_bytes(hashlib.sha256(f"transfer:{source}".encode()).digest()[:8], "big"))
            target = r.choice(stable)
            src = [outcome(x) for x in values[source]]
            dst = [outcome(x) for x in values[target]]
            for seed in seeds:
                ids = list(range(REPETITIONS))
                random.Random(int.from_bytes(hashlib.sha256(f"{seed}:{source}:{target}".encode()).digest()[:8], "big")).shuffle(ids)
                src_train = [src[i] for i in ids[:20]]
                target_recent = [dst[i] for i in ids[15:20]]
                false_pair_examples.append({"seed":seed,"project":source[1],"module":source[2],
                                            "source_id":"::".join(source[-2:]),
                                            "target_id":"::".join(target[-2:]),
                                            "wrong_carryover_quarantine":is_flaky(src_train),
                                            "correct_target_quarantine":is_flaky(target_recent)})
    summary["wrong_transfer_counterfactual"] = {
        "candidate_pairs_per_seed":len(false_pair_examples)//max(1,len(seeds)),
        "induced_false_quarantine_by_seed":{str(seed):sum(int(x["wrong_carryover_quarantine"]) for x in false_pair_examples if x["seed"]==seed) for seed in seeds}}
    return rows, {"summary":summary, "wrong_transfer_examples":false_pair_examples}


def run(root: Path, dest: Path, seeds: tuple[int,...]):
    t0 = time.perf_counter()
    vals, audit = summarize(root)
    stats = outcome_statistics(vals)
    rows, extras = experiment(vals, seeds)
    dest.mkdir(parents=True, exist_ok=True)
    out_file = dest / "real_history_decisions.csv"
    with out_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    examples = extras.pop("wrong_transfer_examples")
    with (dest / "wrong_transfer_counterfactual.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(examples[0]) if examples else ["seed"])
        writer.writeheader()
        writer.writerows(examples)
    result = {"title":"FTW2024 authentic outcomes with synthetic identity interventions",
              "data_source":"https://doi.org/10.5281/zenodo.10639030",
              "audit": audit, "real_outcome_statistics":stats, **extras,
              "runtime_seconds":time.perf_counter()-t0}
    (dest / "history_results.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps({"audit":audit,"real_outcome_statistics":stats,
                      "counterfactual":result["summary"],"runtime_seconds":result["runtime_seconds"]},indent=2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data",type=Path,default=Path("data/raw/flaky_histories_dataset/simulated_rt_results"))
    ap.add_argument("--out",type=Path,default=Path("results/history_replay"))
    ap.add_argument("--seeds",nargs="+",type=int,default=list(SEEDS))
    args = ap.parse_args()
    run(args.data,args.out,tuple(args.seeds))
