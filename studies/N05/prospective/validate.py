#!/usr/bin/env python3
"""Independent-repository statistics and explicitly bounded CI applicability."""
import collections
import math
import json
from pathlib import Path
import random
import re
import statistics
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent

# Workspace-inherited `package.repository = { workspace = true }` cannot be
# resolved from an isolated published .crate, so these must be independently
# matched to the canonical upstream repository. No changes based on outcomes.
WORKSPACE_REPOS = {
    "serde_with": "https://github.com/jonasbb/serde_with",
    "config": "https://github.com/rust-cli/config-rs",  # verify against crates.io API
    "notify": "https://github.com/notify-rs/notify",
    "clap_complete": "https://github.com/clap-rs/clap",
    "poem": "https://github.com/poem-web/poem",
}


def read_jsonl(path):
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()] if path.exists() else []


def resolve_repositories(meta):
    mapping, notes = {}, []
    for name, rec in meta.items():
        raw = rec.get("repository")
        if isinstance(raw, dict):
            raw = WORKSPACE_REPOS.get(name)
            notes.append({"crate": name, "reason": "Cargo workspace-inherited repository", "fallback": raw})
            try:
                url = f"https://crates.io/api/v1/crates/{name}"
                req = urllib.request.Request(url, headers={"User-Agent": "N05-research-ci-replay/1.0"})
                with urllib.request.urlopen(req, timeout=15) as f:
                    remote = json.load(f).get("crate", {}).get("repository")
                if remote:
                    raw = remote
                    notes[-1]["crates_io_repository"] = remote
                    notes[-1]["source"] = url
            except Exception as exc:
                notes[-1]["upstream_fetch_error"] = str(exc)
        if isinstance(raw, str) and raw.startswith("https://github.com/"):
            parts = re.sub(r"\.git$", "", raw).split("/")
            mapping[name] = "/".join(parts[3:5]).lower()
        else:
            mapping[name] = f"UNVERIFIED:{name}"
            notes.append({"crate": name, "source": str(raw), "issue": "unverified repository grouping"})
    return mapping, notes


def bootstrap(rows, key, n=10000):
    """Exact project-level percentile cluster bootstrap, no MC seed noise.

    Enumerate multinomial count vectors, rather than sampling 10k random
    project tuples. There are C(2K-1,K-1) such vectors for K projects; the
    current positive set has K=9 and only 24,310 count vectors.
    """
    units = sorted({x["repo"] for x in rows})
    if len(units) < 2:
        return None
    groups = {u: [x for x in rows if x["repo"] == u] for u in units}
    k = len(units)
    if k > 12:
        # Exact enumeration grows combinatorially; retain deterministic
        # 10000-replicate approximation if the project count exceeds 12.
        rng = random.Random(20271105)
        out = []
        for _ in range(n):
            subset = [item for u in (rng.choice(units) for _ in units) for item in groups[u]]
            out.append(statistics.mean(x[key] for x in subset))
        out.sort()
        return [round(out[int(.025 * n)], 4), round(out[int(.975 * n)-1], 4)]

    def counts_for(total, parts):
        if parts == 1:
            yield (total,)
            return
        for first in range(total + 1):
            for rest in counts_for(total - first, parts - 1):
                yield (first,) + rest

    denom_weights = k**k
    factorials = [math.factorial(j) for j in range(k+1)]
    sizes = [len(groups[u]) for u in units]
    totals = [sum(x[key] for x in groups[u]) for u in units]
    outcomes = []
    for c in counts_for(k, k):
        numerator = sum(c[i] * totals[i] for i in range(k))
        denominator = sum(c[i] * sizes[i] for i in range(k))
        weight = factorials[k] / (math.prod(factorials[j] for j in c) * denom_weights)
        outcomes.append((numerator / denominator, weight))
    outcomes.sort(key=lambda r: r[0])
    quantiles = []
    for q in (.025, .975):
        mass = 0.0
        for value, w in outcomes:
            mass += w
            if mass + 1e-12 >= q:
                quantiles.append(round(value, 4))
                break
    return quantiles


def main():
    manifest = json.loads((HERE / "data/crates_manifest.json").read_text())
    meta = {r["crate"]: r for r in manifest}
    old_cache = HERE / "results/independent_validation.json"
    previous = json.loads(old_cache.read_text()) if old_cache.exists() else {}
    if set(previous.get("source_repository_by_crate", {})) == set(meta):
        repos = previous["source_repository_by_crate"]
        notes = previous.get("repository_resolution_notes", [])
    else:
        repos, notes = resolve_repositories(meta)
    first = json.loads((ROOT / "data/crates_manifest.json").read_text())
    held = json.loads((ROOT / "holdout/data/crates_manifest.json").read_text())
    historical = {}
    for r in first + held:
        raw = r.get("repository")
        if isinstance(raw, str) and raw.startswith("https://github.com/"):
            p = re.sub(r"\.git$", "", raw).split("/")
            historical[r["crate"]] = "/".join(p[3:5]).lower()
    historical["clap"] = "clap-rs/clap"
    known_repo_groups = set(historical.values())
    overlapping = sorted((crate, repo) for crate, repo in repos.items() if repo in known_repo_groups)
    screening = read_jsonl(HERE / "results/screen.jsonl")
    found = {x["id"]: x for x in read_jsonl(HERE / "results/search.jsonl")}
    pathaware = {x["id"]: x for x in read_jsonl(HERE / "results/pathaware.jsonl")}
    diagnostic = {x["id"]: x for x in read_jsonl(HERE / "results/diagnostic.jsonl")}
    positives = [x for x in screening if x["label"] == "eligible_mismatch"]
    rows = []
    for x in positives:
        y = found.get(x["id"])
        if not y:
            continue
        rands = y["random"]
        repo = repos[x["crate"]]
        g = y["guided"]
        v2 = pathaware.get(x["id"], {}).get("pathaware")
        rustc = diagnostic.get(x["id"], {}).get("strong_baseline")
        rf = statistics.mean(int(v["pass"]) for v in rands)
        ra = statistics.mean(v["attempts"] for v in rands)
        rfl = [len(v["features"]) for v in rands if v["pass"]]
        docs = meta[x["crate"]]["docs_metadata"]
        docs_flags = (len([z for z in meta[x["crate"]]["feature_names"] if z != "default"])
                      if docs.get("all-features") else len(docs.get("features", [])))
        rows.append({"id": x["id"], "crate": x["crate"], "repo": repo,
                     "prior_repo_overlap": repo in known_repo_groups,
                     "guided_success": int(g["pass"]), "random_success": rf,
                     "explicit_success": int(y["explicit"]["pass"]),
                     "gain": int(g["pass"])-rf,
                     "guided_attempts": g["attempts"], "random_attempts": ra,
                     "attempt_gain": ra-g["attempts"],
                     "guided_feature_count": len(g["features"]) if g["pass"] else None,
                     "random_features_on_success": statistics.mean(rfl) if rfl else None,
                     "pathaware_success": int(v2["pass"]) if v2 else None,
                     "pathaware_attempts": v2["attempts"] if v2 else None,
                     "pathaware_feature_count": len(v2["features"]) if v2 and v2["pass"] else None,
                     "pathaware_gain": int(v2["pass"])-rf if v2 else None,
                     "pathaware_attempt_gain": ra - v2["attempts"] if v2 else None,
                     "diagnostic_success": int(rustc["pass"]) if rustc else None,
                     "diagnostic_attempts": rustc["attempts"] if rustc else None,
                     "diagnostic_minus_guided": int(rustc["pass"])-int(g["pass"]) if rustc else None,
                     "diagnostic_hint_found": bool(diagnostic.get(x["id"], {}).get("compiler_only_hints")) if rustc else None,
                     "docs_profile_features": docs_flags,
                     "docs_profile_success": 1, "docs_profile_attempts": 1})
    independent = [r for r in rows if not r["prior_repo_overlap"] and not r["repo"].startswith("UNVERIFIED")]

    def aggregate(subset):
        if not subset:
            return None
        f = lambda key: round(statistics.mean(x[key] for x in subset), 4)
        result = {
            "positive_witnesses": len(subset), "source_repositories": len({x["repo"] for x in subset}),
            "guided_success_at_8": f("guided_success"), "random_success_at_8": f("random_success"),
            "explicit_success_at_8": f("explicit_success"),
            "gain_at_8": f("gain"), "gain_repository_cluster_bootstrap_95ci": bootstrap(subset, "gain"),
            "guided_mean_additional_compilations": f("guided_attempts"),
            "random_mean_additional_compilations": f("random_attempts"),
            "random_minus_guided_compilations": f("attempt_gain"),
            "attempt_gain_repository_cluster_bootstrap_95ci": bootstrap(subset, "attempt_gain"),
            "docs_profile_success_at_1": 1.0, "docs_profile_mean_feature_flags": f("docs_profile_features"),
            "guided_feature_count_mean_on_success": round(statistics.mean(x["guided_feature_count"] for x in subset if x["guided_feature_count"] is not None), 4) if any(x["guided_feature_count"] is not None for x in subset) else None,
            "random_feature_count_mean_on_success": round(statistics.mean(x["random_features_on_success"] for x in subset if x["random_features_on_success"] is not None), 4) if any(x["random_features_on_success"] is not None for x in subset) else None,
        }
        v2_cases = [x for x in subset if x["pathaware_success"] is not None]
        result["pathaware_secondary_completed"] = len(v2_cases)
        if len(v2_cases) == len(subset):
            result.update({
                "pathaware_success_at_8": round(statistics.mean(x["pathaware_success"] for x in subset), 4),
                "pathaware_minus_random_success": round(statistics.mean(x["pathaware_gain"] for x in subset), 4),
                "pathaware_minus_random_repository_cluster_bootstrap_95ci": bootstrap(subset, "pathaware_gain"),
                "pathaware_mean_additional_compilations": round(statistics.mean(x["pathaware_attempts"] for x in subset), 4),
                "random_minus_pathaware_compilations_repository_cluster_bootstrap_95ci": bootstrap(subset, "pathaware_attempt_gain"),
            })
        diag_cases = [x for x in subset if x["diagnostic_success"] is not None]
        result["compiler_diagnostic_baseline_completed"] = len(diag_cases)
        if len(diag_cases) == len(subset):
            result.update({
                "compiler_diagnostic_success_at_8": round(statistics.mean(x["diagnostic_success"] for x in subset),4),
                "compiler_diagnostic_hints_available_fraction": round(statistics.mean(x["diagnostic_hint_found"] for x in subset),4),
                "compiler_diagnostic_minus_guided_success": round(statistics.mean(x["diagnostic_minus_guided"] for x in subset),4),
                "compiler_diagnostic_minus_guided_repo_cluster_bootstrap_95ci": bootstrap(subset,"diagnostic_minus_guided"),
                "compiler_diagnostic_mean_additional_compilations": round(statistics.mean(x["diagnostic_attempts"] for x in subset),4),
            })
        return result

    group = aggregate(independent)
    claim = bool(group and group["source_repositories"] >= 5 and group["gain_at_8"] >= .15 and
                 group["gain_repository_cluster_bootstrap_95ci"] and group["gain_repository_cluster_bootstrap_95ci"][0] > 0)
    pathaware_claim = bool(group and group["source_repositories"] >= 5 and
                           group.get("pathaware_minus_random_success", -1) >= .15 and
                           group.get("pathaware_minus_random_repository_cluster_bootstrap_95ci") and
                           group["pathaware_minus_random_repository_cluster_bootstrap_95ci"][0] > 0)
    checks = list((HERE / "results/checks").glob("*.json")) if (HERE / "results/checks").exists() else []
    seconds = sum(json.loads(f.read_text()).get("seconds", 0) for f in checks)
    result = {
        "release_count": len(meta),
        "unique_source_repositories": len(set(repos.values())),
        "source_repository_by_crate": repos,
        "repository_resolution_notes": notes,
        "overlapping_original_repositories": overlapping,
        "frozen_total_snippets": len({x["id"] for x in json.loads((HERE / "data/frozen_sample.json").read_text())["assignments"]}),
        "screened_snippets": len(screening), "positive_feature_profile_mismatches": len(positives),
        "searched_feature_profile_mismatches": len(rows),
        "all_prospective_packages": aggregate(rows),
        "strictly_independent_repositories": group,
        "pre_registered_superiority_criterion_satisfied": claim,
        "secondary_pathaware_superiority_criterion_satisfied": pathaware_claim,
        "compiler_checks_saved_as_provenance": len(checks),
        "sum_serial_Cargo_check_wall_seconds_on_this_host": round(seconds, 2),
        "warning_on_cost": "Shared compilation cache, not an actual GitHub-hosted runner measurement; does not include new fresh runner cache cold start.",
        "negative_conclusions": "Feature-profile divergence is not a defect unless independently reviewed. No upstream CI intervention or developer-hour savings have been observed.",
        "individual_positive_cases": rows,
    }
    out = HERE / "results/independent_validation.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k in ("release_count", "unique_source_repositories", "positive_feature_profile_mismatches", "searched_feature_profile_mismatches", "strictly_independent_repositories", "pre_registered_superiority_criterion_satisfied")}, indent=2))


if __name__ == "__main__":
    main()
