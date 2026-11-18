"""Post-hoc v2 versus existing-practice baselines on fresh SYNTHETIC seeds.

These intervals quantify repeatability under this generator only; no real
deployment project or production incident was independently sampled.
"""

from __future__ import annotations

from collections import defaultdict
import csv
import json
from pathlib import Path
import random
import statistics

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "exploratory_holdout" / "raw" / "paired_policy_results.csv"


def compare() -> dict:
    paired: dict[str, dict[str, dict]] = defaultdict(dict)
    with SAMPLES.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            paired[row["episode_id"]][row["policy"]] = row

    rng = random.Random(101001)
    result = {"phase": "post-hoc policy on new synthetic seeds 101,211,307",
              "industrial_data": False, "promtool_run": False, "pairs": {}}
    for baseline in ("owner_lookback", "owner_relink", "service_grace", "probe_latch"):
        baseline_results = {}
        for metric, positive in (("any_correct_page", True), ("any_false_page", False)):
            strata: dict[tuple, list[float]] = defaultdict(list)
            for item in paired.values():
                v2 = item["owner_relink_v2"]
                if (v2["oracle_positive"] == "True") != positive:
                    continue
                b = item[baseline]
                delta = float(v2[metric] == "True") - float(b[metric] == "True")
                strata[(v2["profile"], v2["seed"], v2["family"])].append(delta)
            vals = [x for group in strata.values() for x in group]
            resamples = []
            for _ in range(2000):
                draw = [rng.choice(group) for group in strata.values() for _ in range(len(group))]
                resamples.append(statistics.mean(draw))
            resamples.sort()
            baseline_results[metric] = {
                "paired_episodes": len(vals),
                "v2_minus_baseline": round(statistics.mean(vals), 6),
                "mc95_low": round(resamples[49], 6),
                "mc95_high": round(resamples[1949], 6),
                "scope": "stratified Monte Carlo over synthetic generator only",
            }

        one = [item for item in paired.values()
               if item["owner_relink_v2"]["oracle_positive"] == "True"]
        rescued = sum(item["owner_relink_v2"]["any_correct_page"] == "True" and
                      item[baseline]["any_correct_page"] == "False" for item in one)
        lost = sum(item["owner_relink_v2"]["any_correct_page"] == "False" and
                   item[baseline]["any_correct_page"] == "True" for item in one)
        both = [item for item in one if item["owner_relink_v2"]["any_correct_page"] == "True" and
                item[baseline]["any_correct_page"] == "True"]
        earlier = sum(int(item["owner_relink_v2"]["correct_first_tick"]) <
                      int(item[baseline]["correct_first_tick"]) for item in both)
        baseline_results["timeliness"] = {
            "rescued_positives_v2_only": rescued,
            "lost_positives_baseline_only": lost,
            "both_detected": len(both),
            "v2_earlier_by_at_least_one_15_second_evaluation": earlier,
        }
        result["pairs"][baseline] = baseline_results
    dest = ROOT / "exploratory_holdout" / "v2_paired_audit.json"
    dest.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(compare(), indent=2))
