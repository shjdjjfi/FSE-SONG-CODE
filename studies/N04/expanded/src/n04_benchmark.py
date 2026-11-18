"""Reproducible test-identity transfer benchmark from independent migration labels.

Usage: python3 src/n04_benchmark.py --dataset data/TestMigrationsInPy/projects

The benchmark is observational for developer-authored test migrations. Its
absent-target counterfactuals are explicitly *controlled*, not observed CI.
No model, raw material or evaluation labels are written to upstream projects.
"""

from __future__ import annotations

import argparse
import collections
import csv
import dataclasses
import difflib
import functools
import hashlib
import json
import math
import random
import re
import statistics
import time
from pathlib import Path


METHODS = (
    "exact_node_id", "method_name", "file_method", "source_similarity",
    "semantic_anchor", "ablate_assertions", "ablate_context", "hybrid_posthoc",
)
SEEDS = (17, 29, 43)
METHOD_RE = re.compile(r"(?m)^([ \t]*)(?:async\s+)?def\s+(test\w*)\s*\(")
CLASS_RE = re.compile(r"(?m)^\s*class\s+([A-Za-z_]\w*)\s*(?:\([^\n]*\))?\s*:")
WORD_RE = re.compile(r"[A-Za-z_]\w*|\d+(?:\.\d+)?|==|!=|<=|>=|['\"][^'\"\n]{0,70}['\"]")
BEFORE_RE = re.compile(r"^mig(\d+)-before-(.+\.py)$")


def norm_name(s: str) -> str:
    return re.sub(r"(?:^test|testcase|^case|^test_)", "", s.lower().replace("_", ""))


def similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


def normalize_assertions(source: str) -> str:
    """Reduce common unittest assertions to the pytest-shaped token pattern.

    This deliberately does not attempt semantic equivalence of arbitrary code.
    """
    patterns = (
        (r"self\.assert(?:Equal|Equals|EqualObjects)\(([^,\n]+),\s*([^\)\n]+)\)", r"assert \1 == \2"),
        (r"self\.assert(?:NotEqual|NotEquals)\(([^,\n]+),\s*([^\)\n]+)\)", r"assert \1 != \2"),
        (r"self\.assert(?:True|_)\(([^\)\n]+)\)", r"assert \1"),
        (r"self\.assertFalse\(([^\)\n]+)\)", r"assert not \1"),
        (r"self\.assertIsNone\(([^\)\n]+)\)", r"assert \1 is None"),
        (r"self\.assertIn\(([^,\n]+),\s*([^\)\n]+)\)", r"assert \1 in \2"),
    )
    for src, dst in patterns:
        source = re.sub(src, dst, source)
    return source.replace("self.", "").replace("pytest.", "")


def extract_test(source: str) -> tuple[str, str, str] | None:
    matches = list(METHOD_RE.finditer(source))
    if len(matches) != 1:
        return None
    m = matches[0]
    test_name = m.group(2)
    prev_classes = list(CLASS_RE.finditer(source[:m.start()]))
    class_name = prev_classes[-1].group(1) if prev_classes else ""
    indent = len(m.group(1).expandtabs(4))
    lines = source[m.start():].splitlines()
    keep = [lines[0]]
    for line in lines[1:]:
        level = len(line) - len(line.lstrip(" \t"))
        if line.strip() and level <= indent:
            break
        keep.append(line)
    return test_name, class_name, "\n".join(keep)


@dataclasses.dataclass(frozen=True)
class Snippet:
    uid: str
    project: str
    commit: str
    file: str
    name: str
    cls: str
    text: str

    @functools.cached_property
    def normalized(self) -> str:
        return normalize_assertions(self.text)

    @functools.cached_property
    def tokens(self) -> tuple[str, ...]:
        body = self.normalized
        body = re.sub(r"(?m)^\s*(?:async )?def\s+test\w*\s*\(.*?:", "", body)
        return tuple(w.lower() for w in WORD_RE.findall(body))[:240]

    @functools.cached_property
    def assertions(self) -> tuple[str, ...]:
        lines = [x.strip() for x in self.normalized.splitlines() if re.search(r"\bassert\b", x)]
        return tuple(" ".join(WORD_RE.findall(x.lower())) for x in lines)[:25]


def load_pairs(base: Path) -> tuple[list[tuple[Snippet, Snippet]], dict]:
    all_pairs = []
    audit = collections.Counter()
    reasons = []
    for before in sorted(base.glob("*/*/diff/*before*.py")):
        m = BEFORE_RE.fullmatch(before.name)
        if not m:
            audit["unmatched_filename"] += 1
            continue
        candidates = list(before.parent.glob(f"mig{m.group(1)}-after-*.py"))
        if len(candidates) != 1:
            audit["missing_or_multiple_after"] += 1
            reasons.append({"file": str(before.relative_to(base)), "reason": "after_count", "count": len(candidates)})
            continue
        after = candidates[0]
        old_text = before.read_text(encoding="utf-8", errors="replace")
        new_text = after.read_text(encoding="utf-8", errors="replace")
        old = extract_test(old_text)
        new = extract_test(new_text)
        if old is None or new is None:
            audit["non_single_test_snippet"] += 1
            reasons.append({"file": str(before.relative_to(base)), "reason": "not_one_test_per_side"})
            continue
        project, migration = before.parts[-4], before.parts[-3]
        commit_file = before.parent.parent / "output.info"
        info = commit_file.read_text(errors="replace")
        commit_m = re.search(r'"commit_hash":\s*"([a-f0-9]{40})"', info)
        commit = commit_m.group(1) if commit_m else f"migration-{migration}"
        uid = f"{project}/{migration}/{m.group(1)}"
        old_entry = Snippet(uid, project, commit, m.group(2), old[0], old[1], old[2])
        new_entry = Snippet(uid, project, commit, after.name.split("-after-", 1)[-1], new[0], new[1], new[2])
        all_pairs.append((old_entry, new_entry))
        audit["parsed_pairs"] += 1

    # Two snippets that refer to the same test within one commit do not give
    # an unambiguous 1:1 mapping. Remove the whole conflict cluster, not just
    # one convenient item; this exclusion is fixed before evaluation.
    source_ids = collections.Counter((o.project, o.commit, o.file, o.cls, o.name) for o, _ in all_pairs)
    target_ids = collections.Counter((n.project, n.commit, n.file, n.cls, n.name) for _, n in all_pairs)
    clean = []
    for old, new in all_pairs:
        src_key = (old.project, old.commit, old.file, old.cls, old.name)
        tgt_key = (new.project, new.commit, new.file, new.cls, new.name)
        if source_ids[src_key] > 1 or target_ids[tgt_key] > 1:
            audit["ambiguous_duplicate_identity"] += 1
            reasons.append({"file": old.uid, "reason": "duplicate_identity_in_commit"})
        else:
            clean.append((old, new))
    audit["unique_pairs"] = len(clean)
    audit["unique_projects"] = len(set(o.project for o, _ in clean))
    audit["unique_commits"] = len(set((o.project, o.commit) for o, _ in clean))
    return clean, {"counts": dict(audit), "exclusions_sample": reasons[:200]}


@functools.lru_cache(maxsize=180000)
def score(old: Snippet, new: Snippet, method: str) -> float:
    name = similarity(norm_name(old.name), norm_name(new.name))
    path = similarity(norm_name(old.file), norm_name(new.file))
    cls = similarity(norm_name(old.cls), norm_name(new.cls)) if old.cls and new.cls else 0.3
    if method == "exact_node_id":
        return float(old.file == new.file and old.cls == new.cls and old.name == new.name)
    if method == "method_name":
        return float(old.name == new.name)
    if method == "file_method":
        return 0.75 * float(old.name == new.name) + 0.25 * path
    old_tok, new_tok = old.tokens, new.tokens
    if method == "source_similarity":
        return difflib.SequenceMatcher(None, old_tok, new_tok, autojunk=False).ratio()
    sa, sb = set(old_tok), set(new_tok)
    jac = len(sa & sb) / len(sa | sb) if sa | sb else 0.0
    seq = difflib.SequenceMatcher(None, old_tok, new_tok, autojunk=False).ratio()
    a, b = set(old.assertions), set(new.assertions)
    ass = len(a & b) / len(a | b) if a | b else 0.5
    if method == "hybrid_posthoc":
        # Added AFTER inspection of the initial aggregate results: this is an
        # explicitly exploratory hybrid and not a prespecified primary model.
        # Preserve exact method-name continuity when textual evidence agrees;
        # fall back to transformed body similarity for actual renamed tests.
        contextual = .46 * seq + .40 * jac + .14 * ass
        if old.name == new.name:
            return (.97 + .03 * contextual) if (seq >= .18 or jac >= .25) else .25
        if norm_name(old.name) == norm_name(new.name) and norm_name(old.name):
            return .91 + .08 * contextual
        if seq >= .76 and jac >= .65:
            return .82 + .16 * contextual
        return .55 * contextual + .15 * path
    if method == "ablate_assertions":
        return min(1.0, 0.48 * seq + 0.32 * jac + 0.12 * name + 0.08 * path)
    if method == "ablate_context":
        return min(1.0, 0.45 * seq + 0.30 * jac + 0.25 * ass)
    if method == "semantic_anchor":
        return min(1.0, 0.37 * seq + 0.25 * jac + 0.20 * ass + 0.12 * name + 0.04 * path + 0.02 * cls)
    raise ValueError(method)


def choose_candidates(pairs: list, seed: int, max_candidates: int = 12) -> list[dict]:
    group = collections.defaultdict(list)
    for old, new in pairs:
        group[(old.project, old.commit)].append((old, new))
    examples = []
    for (project, commit), items in sorted(group.items()):
        if len(items) < 2:
            continue
        for old, good in items:
            # Candidate distractors are OTHER independently paired migrations in
            # the SAME developer commit, never fabricated code snippets.
            other = [new for _, new in items if new.uid != old.uid]
            if not other:
                continue
            rng = random.Random(int.from_bytes(hashlib.sha256(f"{seed}:{old.uid}".encode()).digest()[:8], "big"))
            rng.shuffle(other)
            # Include a fixed hard-negative core and a genuinely randomized
            # sample of remaining same-commit negatives, without inspecting
            # source-text scores from any evaluated method.
            other.sort(key=lambda x: (similarity(norm_name(old.name), norm_name(x.name)),
                                      similarity(old.file, x.file)), reverse=True)
            k = max(1, max_candidates - 1)
            hard_count = min(len(other), max(1, k // 2))
            hard = other[:hard_count]
            remainder = other[hard_count:]
            rng.shuffle(remainder)
            distractors = hard + remainder[:max(0,k-hard_count)]
            examples.append({"project": project, "commit": commit, "uid": old.uid,
                             "old": old, "good": good, "distractors": distractors,
                             "present_candidates": [good] + distractors,
                             "absent_candidates": distractors})
    return examples


def top_prediction(query: dict, method: str, present: bool) -> tuple[float, float, str]:
    old = query["old"]
    candidates = query["present_candidates"] if present else query["absent_candidates"]
    scored = sorted(((score(old, item, method), item.uid) for item in candidates), reverse=True)
    if not scored:
        return 0.0, 0.0, ""
    best = scored[0]
    next_score = scored[1][0] if len(scored) > 1 else 0.0
    return best[0], best[0] - next_score, best[1]


def accept(best: tuple, threshold: float, margin: float) -> str:
    s, gap, uid = best
    # A top-score tie is intrinsically ambiguous: deterministic abstention.
    return uid if s >= threshold and gap > max(1e-12, margin) else ""


def precompute(examples: list[dict]) -> dict:
    out = {}
    for q in examples:
        out[q["uid"]] = {m: {"present": top_prediction(q, m, True),
                             "absent": top_prediction(q, m, False)} for m in METHODS}
    return out


def tune(rows: list[dict], predictions: dict, method: str) -> tuple[float, float, dict]:
    """Risk-controlled calibration on training projects only.

    The empirical 2% false-transfer budget is a *calibration target*, not a
    statistical guarantee on independent projects.
    """
    if not rows:
        return 1.01, 1., {"calibration_recovery": 0, "calibration_false_transfer": 0}
    best = None
    for threshold_index in range(0, 102, 2):
        th = threshold_index / 100
        for margin in (0., .01, .025, .05, .10, .15):
            good, wrong, absent_wrong = 0, 0, 0
            for q in rows:
                top = predictions[q["uid"]][method]
                found = accept(top["present"], th, margin)
                if found == q["uid"]:
                    good += 1
                elif found:
                    wrong += 1
                if accept(top["absent"], th, margin):
                    absent_wrong += 1
            false_rate = (wrong + absent_wrong) / (2 * len(rows))
            recovery = good / len(rows)
            if false_rate <= .02 + 1e-12:
                # Prefer recovery; break ties by fewer false transfers and a
                # more conservative threshold to reduce risk of overfitting.
                key = (recovery, -false_rate, th, margin)
                if best is None or key > best[0]:
                    best = (key, th, margin, recovery, false_rate)
    if best is None:
        return 1.01, 1., {"calibration_recovery": 0, "calibration_false_transfer": 0}
    _, th, margin, recall, false_rate = best
    return th, margin, {"calibration_recovery": recall, "calibration_false_transfer": false_rate}


def test_statistics(rows: list[dict]) -> dict:
    n = len(rows)
    if not n:
        return {"pairs": 0}
    recovered = sum(x["present_pred"] == x["uid"] for x in rows)
    wrong_matched = sum(bool(x["present_pred"]) and x["present_pred"] != x["uid"] for x in rows)
    wrong_absent = sum(bool(x["absent_pred"]) for x in rows)
    return {"pairs": n, "recovered": recovered, "recovery_rate": recovered / n,
            "wrong_matched": wrong_matched, "wrong_absent": wrong_absent,
            "absent_false_transfer_rate": wrong_absent / n,
            "combined_false_transfer_rate": (wrong_matched + wrong_absent) / (2*n),
            "selective_precision": recovered / max(1, recovered+wrong_matched+wrong_absent),
            "cost_ratio_5": (n-recovered + 5*(wrong_matched+wrong_absent)) / n,
            "cost_ratio_10": (n-recovered + 10*(wrong_matched+wrong_absent)) / n}


def leave_one_project_out(examples: list[dict], predictions: dict, method: str) -> tuple[list[dict], list[dict]]:
    projects = sorted(set(q["project"] for q in examples))
    output, thresholds = [], []
    for p in projects:
        train = [q for q in examples if q["project"] != p]
        test = [q for q in examples if q["project"] == p]
        th, margin, t = tune(train, predictions, method)
        thresholds.append({"project": p, "method": method, "threshold": th, "margin": margin, **t})
        for q in test:
            top = predictions[q["uid"]][method]
            found = accept(top["present"], th, margin)
            absent = accept(top["absent"], th, margin)
            output.append({"uid": q["uid"], "project": p, "commit": q["commit"],
                           "method": method, "present_pred": found, "absent_pred": absent,
                           "present_score": top["present"][0], "absent_score": top["absent"][0],
                           "threshold": th, "margin": margin})
    return output, thresholds


def bootstrap_project_difference(rows: list[dict], a: str, b: str, seed: int = 2027) -> dict:
    """Paired project-cluster bootstrap; three seeds are NOT independent units."""
    by_key = collections.defaultdict(dict)
    for r in rows:
        by_key[(r["seed"], r["uid"])][r["method"]] = r
    by_project = collections.defaultdict(list)
    for key, both in by_key.items():
        if a in both and b in both:
            pa, pb = both[a], both[b]
            by_project[pa["project"]].append((float(pa["present_pred"] == pa["uid"]),
                                              float(pb["present_pred"] == pb["uid"])))
    projs = sorted(by_project)
    if len(projs) < 2:
        return {"cluster_count": len(projs), "diff": None, "ci95": None}
    def calc(selected):
        vals = [val for p in selected for val in by_project[p]]
        return sum(x-y for x,y in vals)/len(vals)
    rng = random.Random(seed)
    dist = sorted(calc([rng.choice(projs) for _ in projs]) for _ in range(1200))
    return {"cluster_count": len(projs), "diff": calc(projs),
            "ci95": [dist[29], dist[1170]]}


def write_csv(path: Path, rows: list[dict]):
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run(dataset: Path, output: Path, max_candidates: int, seeds: tuple[int, ...]):
    t0 = time.perf_counter()
    pairs, audit = load_pairs(dataset)
    output.mkdir(parents=True, exist_ok=True)
    rows, thresholds, scenario_stats = [], [], []
    per_seed = []
    for seed in seeds:
        examples = choose_candidates(pairs, seed, max_candidates)
        pred = precompute(examples)
        per_seed.append({"seed": seed, "queries": len(examples),
                         "projects": len(set(x["project"] for x in examples)),
                         "commits": len(set((x["project"], x["commit"]) for x in examples)),
                         "candidate_count_min": min(len(x["present_candidates"]) for x in examples),
                         "candidate_count_max": max(len(x["present_candidates"]) for x in examples),
                         "candidate_count_mean": statistics.mean(len(x["present_candidates"]) for x in examples)})
        for method in METHODS:
            prediction_rows, threshold_rows = leave_one_project_out(examples, pred, method)
            for x in prediction_rows:
                x["seed"] = seed
            rows.extend(prediction_rows)
            for x in threshold_rows:
                x["seed"] = seed
            thresholds.extend(threshold_rows)
            stats = test_statistics(prediction_rows)
            scenario_stats.append({"seed": seed, "method": method, **stats})
        print(f"seed={seed} done, queries={len(examples)}, elapsed={time.perf_counter()-t0:.1f}s", flush=True)
    write_csv(output / "predictions.csv", rows)
    write_csv(output / "thresholds.csv", thresholds)
    write_csv(output / "by_seed.csv", scenario_stats)
    summary = {}
    for method in METHODS:
        r = [x for x in rows if x["method"] == method]
        stat = test_statistics(r)
        stat["recovery_by_project"] = {p: test_statistics([x for x in r if x["project"] == p])["recovery_rate"]
                                       for p in sorted(set(x["project"] for x in r))}
        summary[method] = stat
    comparisons = {method: bootstrap_project_difference(rows, "semantic_anchor", method)
                   for method in METHODS if method != "semantic_anchor"}
    source_sha = hashlib.sha256((dataset.parent / "README.md").read_bytes()).hexdigest() \
        if (dataset.parent / "README.md").is_file() else None
    final = {"description": "Paired real-code identity-linking benchmark; target removal is controlled",
             "dataset": str(dataset), "dataset_readme_sha256": source_sha,
             "timestamp_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
             "audit": audit, "per_seed": per_seed,
             "summary": summary, "bootstrap_differences": comparisons,
             "total_runtime_seconds": time.perf_counter()-t0,
             "statistical_unit": "project; seeds are repeated random candidate samplings"}
    (output / "results.json").write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"audit": audit["counts"], "summary": {k:{"recovery":v["recovery_rate"],
                           "false_transfer":v["combined_false_transfer_rate"]} for k,v in summary.items()},
                      "runtime_seconds":final["total_runtime_seconds"]}, indent=2))
    return final


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", type=Path, default=Path("data/TestMigrationsInPy/projects"))
    p.add_argument("--out", type=Path, default=Path("results/migration_benchmark"))
    p.add_argument("--max-candidates", type=int, default=12)
    p.add_argument("--seeds", type=int, nargs="+", default=list(SEEDS))
    args = p.parse_args()
    run(args.dataset, args.out, args.max_candidates, tuple(args.seeds))


if __name__ == "__main__":
    main()
