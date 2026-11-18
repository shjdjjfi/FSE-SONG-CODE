"""Verify that stored v1 outputs still exactly match the extended v2 code.

This check reads all 19,800 policy rows but intentionally excludes the new,
post-hoc v2 policy from the original recorded comparison.
"""

from __future__ import annotations

import csv
import itertools
from pathlib import Path
import sys

from simulator import POLICIES, evaluate, make_episode

ROOT = Path(__file__).resolve().parent.parent
PATH = ROOT / "results_v2" / "raw" / "paired_policy_results.csv"


def stringify(value) -> str:
    return "" if value is None else str(value)


def check() -> tuple[int, int]:
    original_policies = tuple(x for x in POLICIES if x != "owner_relink_v2")
    episodes = 0
    rows_checked = 0
    with PATH.open(encoding="utf-8", newline="") as handle:
        grouped = itertools.groupby(csv.DictReader(handle), key=lambda x: x["episode_id"])
        for ident, sequence in grouped:
            source_rows = list(sequence)
            initial = source_rows[0]
            ep = make_episode(initial["profile"], initial["family"],
                              int(initial["seed"]), int(initial["replicate"]))
            if ep.episode_id != ident:
                raise AssertionError(f"episode ID changed: {ident}")
            observed = evaluate(ep, selected=original_policies)
            keyed = {row["policy"]: row for row in observed}
            for source in source_rows:
                current = keyed[source["policy"]]
                for key, expected in source.items():
                    actual = stringify(current[key])
                    if actual != expected:
                        raise AssertionError(f"{ident}:{source['policy']}:{key} {expected} != {actual}")
                rows_checked += 1
            episodes += 1
    return episodes, rows_checked


if __name__ == "__main__":
    try:
        eps, lines = check()
        print(f"PASS: {eps} frozen episodes / {lines} recorded method rows match current code exactly")
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise
