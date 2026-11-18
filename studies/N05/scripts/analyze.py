#!/usr/bin/env python3
"""Recompute tables, project-cluster CIs, and a claim-bounded results report."""
import collections
import csv
import json
from pathlib import Path
import random
import statistics

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RESULTS = ROOT / "results"
PAPER = ROOT / "paper"


def load(path):
    return [json.loads(s) for s in path.read_text().splitlines() if s.strip()] if path.exists() else []


def bootstrap_cluster_diff(rows, n=10000, outcome="success"):
    # Independent re-sampling units are *projects*, not adjacent snippets.
    by_project = collections.defaultdict(list)
    for row in rows:
        by_project[row["crate"]].append(row)
    names = list(by_project)
    if len(names) < 2:
        return None
    rng = random.Random(51005)
    deltas = []
    for _ in range(n):
        chosen = [rng.choice(names) for _ in names]
        sub = [r for crate in chosen for r in by_project[crate]]
        if outcome == "success":
            d = statistics.mean(r["guided"] - r["random"] for r in sub)
        else:
            d = statistics.mean(r["random_attempts"] - r["guided_attempts"] for r in sub)
        deltas.append(d)
    deltas.sort()
    return (round(deltas[int(0.025 * n)], 4), round(deltas[int(0.975 * n) - 1], 4))


def main():
    PAPER.mkdir(exist_ok=True)
    RESULTS.mkdir(exist_ok=True)
    meta = {x["crate"]: x for x in json.loads((DATA / "crates_manifest.json").read_text())}
    sample = json.loads((DATA / "frozen_sample.json").read_text())
    screen = {r["id"]: r for r in load(RESULTS / "screen.jsonl")}
    search = {r["id"]: r for r in load(RESULTS / "search.jsonl")}
    labels = collections.Counter(r["label"] for r in screen.values())
    sampled_ids = {r["id"] for r in sample["assignments"]}
    missing = sampled_ids - screen.keys()
    positives = [r for r in screen.values() if r["label"] == "eligible_mismatch"]
    negative_controls = [r for r in screen.values() if r["default_status"] == "pass" and r["docs_status"] == "pass"]
    default_works_docs_fail = [r for r in screen.values() if r["default_status"] == "pass" and r["docs_status"] != "pass"]
    completed = []
    for r in positives:
        out = search.get(r["id"])
        if not out:
            continue
        completed.append({"id": r["id"], "crate": r["crate"],
                          "guided": float(out["guided"]["pass"]),
                          "random": statistics.mean(float(k["pass"]) for k in out["random"]),
                          "explicit": float(out["explicit"]["pass"]),
                          "guided_attempts": out["guided"]["attempts"],
                          "random_attempts": statistics.mean(k["attempts"] for k in out["random"]),
                          "random_success_len": (statistics.mean(len(k["features"]) for k in out["random"] if k["pass"])
                                                 if any(k["pass"] for k in out["random"]) else None),
                          "fix_len": len(out["guided"]["features"]) if out["guided"]["pass"] else None,
                          "docs_extra": (len(meta[r["crate"]]["feature_names"]) - 1 if meta[r["crate"]]["docs_metadata"].get("all-features")
                                         else len(meta[r["crate"]]["docs_metadata"].get("features", [])))})
    by_crate = collections.defaultdict(lambda: collections.Counter())
    for r in screen.values():
        by_crate[r["crate"]][r["label"]] += 1
        by_crate[r["crate"]]["screened"] += 1
    with (RESULTS / "per_project.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["crate", "version", "screened", "eligible_mismatch", "default_compiles", "invalid_doc_sample", "infrastructure"])
        for name in sorted(meta):
            c = by_crate[name]
            w.writerow([name, meta[name]["version"], c["screened"], c["eligible_mismatch"],
                        c["default_compiles"], c["invalid_doc_sample"], c["infrastructure"]])
    ci = bootstrap_cluster_diff(completed)
    attempts_ci = bootstrap_cluster_diff(completed, outcome="attempts")
    total_admissible = labels["eligible_mismatch"] + len(negative_controls)
    seed_outcomes = {}
    for seed in sample["seeds"]:
        unique_ids = {a["id"] for a in sample["assignments"] if a["seed"] == seed}
        this = [screen[x] for x in unique_ids if x in screen]
        seed_outcomes[str(seed)] = {"screened": len(this),
                                   "positive": sum(x["label"] == "eligible_mismatch" for x in this),
                                   "docs_and_default_both_pass": sum(x["docs_status"] == "pass" and x["default_status"] == "pass" for x in this)}
    risk_admissible = [r for r in screen.values() if r["risk"] and r["docs_status"] == "pass"]
    risk_mismatch = sum(r["label"] == "eligible_mismatch" for r in risk_admissible)
    minimization = load(RESULTS / "minimized.jsonl")
    generic_ablation = load(RESULTS / "generic_ablation.jsonl")
    ablations = json.loads((RESULTS / "visible_ablation.json").read_text()) if (RESULTS / "visible_ablation.json").exists() else []
    metrics = {
        "frozen_projects": len(meta),
        "candidate_snippets": sum(m["n_snippets"] for m in meta.values()),
        "frozen_seed_assignments": len(sample["assignments"]),
        "frozen_distinct_snippets": len(sampled_ids),
        "screened": len(screen),
        "missing_screens": len(missing),
        "labels": dict(labels),
        "admissible": total_admissible,
        "strict_negative_controls": len(negative_controls),
        "default_pass_docs_fail_not_in_denominator": len(default_works_docs_fail),
        "seed_outcomes": seed_outcomes,
        "risk_static_prefilter_precision_on_compiler_mismatch": round(risk_mismatch / len(risk_admissible), 4) if risk_admissible else None,
        "conditional_mismatch_rate_among_admissible": round(labels["eligible_mismatch"] / total_admissible, 4) if total_admissible else None,
        "searched": len(completed),
        "unsearched_positive": len(positives) - len(completed),
        "guided_success_at_8": round(statistics.mean(r["guided"] for r in completed), 4) if completed else None,
        "random_success_at_8": round(statistics.mean(r["random"] for r in completed), 4) if completed else None,
        "explicit_success_at_8": round(statistics.mean(r["explicit"] for r in completed), 4) if completed else None,
        "guided_mean_additional_compilations": round(statistics.mean(r["guided_attempts"] for r in completed), 4) if completed else None,
        "random_mean_additional_compilations": round(statistics.mean(r["random_attempts"] for r in completed), 4) if completed else None,
        "random_minus_guided_compilations_95pct_project_cluster_bootstrap_CI": attempts_ci,
        "guided_mean_requested_features_on_success": round(statistics.mean(r["fix_len"] for r in completed if r["fix_len"] is not None), 4) if any(r["fix_len"] is not None for r in completed) else None,
        "random_mean_requested_features_on_success_conditional": round(statistics.mean(r["random_success_len"] for r in completed if r["random_success_len"] is not None), 4) if any(r["random_success_len"] is not None for r in completed) else None,
        "guided_minus_random_95pct_project_cluster_bootstrap_CI": ci,
        "projects_with_eligible_mismatch": sum(bool(c["eligible_mismatch"]) for c in by_crate.values()),
        "completed_minimizations": len(minimization),
        "certified_subset_minimal": sum(x["subset_minimal_certified"] for x in minimization),
        "certified_one_flag_cardinality_optimal": sum(x["globally_minimal_certified"] for x in minimization),
        "post_discovery_minimization_compilations": sum(len(x["post_discovery_checks"]) for x in minimization),
        "generic_lexical_ablation_completed": len(generic_ablation),
        "generic_lexical_ablation_success_at_8": round(statistics.mean(float(x["lexical_only"]["pass"]) for x in generic_ablation),4) if generic_ablation else None,
        "visible_only_ablations": len(ablations),
        "visible_only_failed": sum(x["visible_only_status"] == "fail" for x in ablations),
        "results_complete": not missing and len(positives) == len(completed),
    }
    (RESULTS / "summary.json").write_text(json.dumps(metrics, indent=2) + "\n")
    lines = [
        "# N05 — Measured experimental results (automatically generated)", "",
        "**All result counts below are from actual Cargo compilations. They must not be interpreted as population prevalence.**", "",
        f"- Source: {len(meta)} pinned crates.io releases; {metrics['candidate_snippets']:,} syntactically extracted Rustdoc fences.",
        f"- Pre-registered assignments: {len(sample['assignments'])} over three seeds, {len(sampled_ids)} distinct snippets.",
        f"- Screened: {len(screen)}/{len(sampled_ids)} distinct snippets; remaining {len(missing)}.",
        f"- Labels: {dict(labels)}.",
        f"- Feature mismatch in consumer-compile-admissible set: {labels['eligible_mismatch']}/{total_admissible if total_admissible else 0} (stratified sample; no population estimator).",
        f"- Strict negative controls passing both profiles: {len(negative_controls)}. Default-works/docs-fails samples excluded from that denominator: {len(default_works_docs_fail)}.",
        f"- Crates with one or more independently observed gap witnesses: {metrics['projects_with_eligible_mismatch']}.",
        f"- Search outcomes: {len(completed)}/{len(positives)} eligible witnesses completed; fixed budget of eight additional Cargo checks per method.",
        f"- Independent post-discovery subset minimizations: {len(minimization)} performed, {sum(x['subset_minimal_certified'] for x in minimization)} verified.",
        f"- One-flag feature additions with trivial global minimum cardinality: {metrics['certified_one_flag_cardinality_optimal']}. Other fixes have **no** global minimum claim.",
        f"- Search effort: guided {metrics['guided_mean_additional_compilations']} vs random {metrics['random_mean_additional_compilations']} additional compiles per positive.",
        f"- Lexical-only post-hoc ablation: {len(generic_ablation)} cases, success@8={metrics['generic_lexical_ablation_success_at_8']}.",
        f"- Visible-copy ablations: {len(ablations)} performed, {sum(x['visible_only_status'] == 'fail' for x in ablations)} failed without Rustdoc-hidden preparation.",
    ]
    if completed:
        lines += [
            f"- Guided success@8 = {metrics['guided_success_at_8']}; lexical explicit-hint baseline = {metrics['explicit_success_at_8']}; random order (3 seeds) = {metrics['random_success_at_8']}.",
            f"- Guided minus random project-cluster bootstrap 95% interval = {ci}." if ci else "- Fewer than two projects; cluster CI unavailable.",
            f"- Random minus guided Cargo checks project-cluster bootstrap 95% interval = {attempts_ci}." if attempts_ci else "- Fewer than two projects; cluster CI unavailable.",
        ]
    lines += ["", "## Per-project breakdown", "", "| Crate | Compiled samples | Gap witnesses | Default works | Invalid document sample |", "|---|---:|---:|---:|---:|"]
    for name in sorted(meta):
        c = by_crate[name]
        lines.append(f"| {name} {meta[name]['version']} | {c['screened']} | {c['eligible_mismatch']} | {c['default_compiles']} | {c['invalid_doc_sample']} |")
    lines += [
        "", "## Operational definitions and limits", "",
        "- Gap witness: the **same** published-source Rustdoc code fence compiles in an external consumer Cargo package under docs.rs's declared *feature* profile but fails under default Cargo features.",
        "- This tests the documentation's code against consumer build configurations; it does **not** establish that docs.rs ran the individual doctest or that the snippet is visible on every rendered item page.",
        "- Rustdoc-hidden lines were compiled, as in Rustdoc itself; the visible-only copy/paste analysis is a separate future/ablation question. External test dependencies were not guessed.",
        "- Doctest `ignore` and `compile_fail` code fences were excluded; `no_run` fences were compiled but never executed. This guards against mistaking intentional behavior for a defect.",
        "- docs.rs-specific rustdoc `--cfg` and nightly flags are not applied to consumer Cargo. The documented **feature** profiles are tested separately; platform is fixed to x86_64-unknown-linux-gnu.",
        "- Samples deliberately oversample code mentioning extra feature names. Reported conditional rates are not unbiased estimates of Rust ecosystem prevalence.",
        "- `invalid_doc_sample` means the synthetic consumer did not compile even with the docs feature set (possibly an external dev dependency, context, cfg or a true doc bug); it is excluded from a feature-gap finding.",
        "- Feature search is budgeted and heuristic. The current guided `features` lists are *not* proven cardinality-minimal; a separate minimization oracle or bounded exhaustive test is needed before claiming minimality.",
        "- The selected 24 popular projects are a convenience sample, not an independent random sample of crates.io; results have no demonstrated industrial adoption outcome.",
        "- Lockfile transitive dependencies and compiler/toolchain need to be preserved to reproduce exact behavior in the future.",
        "", "## Evidence files", "",
        "`data/crates_manifest.json` (SHA-256 per official .crate); `data/frozen_sample.json` (pre-registered selection); `results/screen.jsonl`; `results/search.jsonl`; `results/checks/*.json` and corresponding compressed Cargo logs; `results/per_project.csv`.",
        "",
    ]
    (PAPER / "RESULTS.md").write_text("\n".join(lines))
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
