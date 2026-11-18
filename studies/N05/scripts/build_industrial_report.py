#!/usr/bin/env python3
"""Generate claim-bounded journal-style audit from executable, archived data."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads((ROOT / path).read_text())


def fmt(n, digits=1):
    return "n/a" if n is None else f"{n * 100:.{digits}f}%"


def ci(interval, percentage=True):
    if interval is None:
        return "n/a (too few independent repositories)"
    return f"[{fmt(interval[0])}, {fmt(interval[1])}]" if percentage else f"[{interval[0]:.2f}, {interval[1]:.2f}]"


def main():
    old = load("results/summary.json")
    held = load("holdout/results/summary.json")
    prospect = load("prospective/results/independent_validation.json")
    actual_ci = load("industrial/public_ci_and_fixes.json")
    historic = load("industrial/historical/historical_case_coverage.json")
    disclosed = load("industrial/rendered_feature_disclosure.json")
    footprint = load("industrial/feature_footprint.json")
    dominated = load("industrial/verified_dominated_fix.json")
    sensitivity = load("prospective/results/consumer_sensitivity.json")
    strict = prospect["strictly_independent_repositories"]
    naive = prospect["all_prospective_packages"]
    byrepo = {}
    for x in prospect["individual_positive_cases"]:
        byrepo[x["repo"]] = byrepo.get(x["repo"], 0) + x["gain"]
    gain_repos = sum(v > 0 for v in byrepo.values())
    zero_mass = ((len(byrepo)-gain_repos)/len(byrepo))**len(byrepo) if byrepo else 0

    def perf(label, s):
        return (f"| {label} | {s['positive_witnesses']} | {s['source_repositories']} | "
                f"{fmt(s['guided_success_at_8'])} | {fmt(s['random_success_at_8'])} | "
                f"{fmt(s['gain_at_8'])} | {ci(s['gain_repository_cluster_bootstrap_95ci'])} | "
                f"{s['guided_mean_additional_compilations']:.2f} | {s['random_mean_additional_compilations']:.2f} |")

    lines = [
        "# N05 — independent source-release and real-world CI evidence audit", "",
        "## Executive verdict", "",
        f"- **Original v1 generalization superiority established:** **{'YES' if prospect['pre_registered_superiority_criterion_satisfied'] else 'NO'}** against three seeded random orders under the pre-registered +15 pp / project-cluster-CI rule. The exact project-bootstrap 95% lower endpoint is {strict['gain_repository_cluster_bootstrap_95ci'][0]}, so the criterion is not satisfied if that lower bound equals zero.",
        f"- **Secondary generic source-path v2 criterion established:** **{'YES' if prospect['secondary_pathaware_superiority_criterion_satisfied'] else 'NO'}**. This is a separate refinement developed after inspecting the older 8-project validation set, not the original algorithm.",
        "- **Real upstream CI adoption/intervention demonstrated:** **NO**. We retrieved successful upstream CI run metadata and published workflow definitions (not job logs), but have no upstream installation of N05, A/B comparison, or measured developer-hours benefit.",
        "- **Independently confirmed actionable issues detected by this original extractor:** **0 of 2 historical iced fixes**. Their affected APIs were absent from its Rustdoc literal-code-fence coverage in the pre- and post-fix published releases.",
        "- **Confirmed errors among all feature-profile discrepancies:** **UNDETERMINED**; those with visible feature prerequisites cannot be called missing-documentation defects.",
        "", "## Exact replays and independent validation", "",
        f"- Development: {old['frozen_projects']} crate releases, {old['screened']} screened snippets, {old['labels'].get('eligible_mismatch',0)} profile mismatches; guided success {fmt(old['guided_success_at_8'])}, random {fmt(old['random_success_at_8'])}.",
        f"- First held-out set: {held['frozen_projects']} releases, {held['screened']} screened, {held['labels'].get('eligible_mismatch',0)} profile mismatches; guided {fmt(held['guided_success_at_8'])}, random {fmt(held['random_success_at_8'])}.",
        f"- Second frozen cohort: {prospect['release_count']} releases across {prospect['unique_source_repositories']} repository labels, {prospect['screened_snippets']}/{prospect['frozen_total_snippets']} screened; {prospect['positive_feature_profile_mismatches']} profile mismatches, {prospect['searched_feature_profile_mismatches']} fully searched.",
        "", "| Second holdout slice | Positive cases | Independent repos | v1 success@8 | Random success@8 | Δ success | 95% repo-cluster CI | v1 checks | Random checks |",
        "|---|---:|---:|---:|---:|---:|---|---:|---:|",
        perf("All new crate names", naive),
        perf("Strictly new source repositories", strict),
        "", "**Exact bootstrap verification:** The nominal 10,000-draw project bootstrap is unstable at a boundary: "
        f"only {gain_repos} of {len(byrepo)} source repositories have a positive v1-minus-random difference. "
        f"When resampling {len(byrepo)} projects with replacement, the exact probability "
        f"that *all* sampled clusters have zero gain is {zero_mass:.4%}, larger than the 2.5% lower-tail level. "
        "The exact multinomial-enumerated percentile CI therefore **starts at zero**. "
        "An earlier 10,000-replicate estimate from a different random seed had a slightly positive lower endpoint; "
        "claiming a significant gain from that unstable Monte Carlo outcome would be misleading. "
        "The overall method success and mean effort estimates are unchanged.",
        "", "### Post-hoc consumer-relevance sensitivity", "",
        "In the exact `sea-query 0.32.5` source, `src/lib.rs` declares `#[doc(hidden)]` and `#[cfg(feature = \"tests-cfg\")]` "
        "on `pub mod tests_cfg`. Six of the 24 supposedly consumer-mismatched examples directly import this hidden test fixture. "
        "The formal full-set statistic is retained, but those six should **not** be counted as developer-actionable user API repairs.",
        "", "| Sensitivity | Examples | Source repos | Guided | Random | Δ success | Exact repo-cluster CI | Compiler-hint baseline |",
        "|---|---:|---:|---:|---:|---:|---|---:|",
        f"| All pre-registered cases | {sensitivity['full_preregistered_cohort']['case_count']} | {sensitivity['full_preregistered_cohort']['repo_count']} | "
        f"{fmt(sensitivity['full_preregistered_cohort']['guided_success_at_8'])} | "
        f"{fmt(sensitivity['full_preregistered_cohort']['random_success_at_8'])} | "
        f"{fmt(sensitivity['full_preregistered_cohort']['guided_minus_random'])} | "
        f"{ci(sensitivity['full_preregistered_cohort']['project_cluster_95ci_guided_minus_random'])} | "
        f"{fmt(sensitivity['full_preregistered_cohort']['diagnostic_success_at_8'])} |",
        f"| Exclude published hidden tests_cfg fixtures (post-hoc) | {sensitivity['after_excluding_explicit_test_fixture_import']['case_count']} | "
        f"{sensitivity['after_excluding_explicit_test_fixture_import']['repo_count']} | "
        f"{fmt(sensitivity['after_excluding_explicit_test_fixture_import']['guided_success_at_8'])} | "
        f"{fmt(sensitivity['after_excluding_explicit_test_fixture_import']['random_success_at_8'])} | "
        f"{fmt(sensitivity['after_excluding_explicit_test_fixture_import']['guided_minus_random'])} | "
        f"{ci(sensitivity['after_excluding_explicit_test_fixture_import']['project_cluster_95ci_guided_minus_random'])} | "
        f"{fmt(sensitivity['after_excluding_explicit_test_fixture_import']['diagnostic_success_at_8'])} |",
        "", "The sensitivity subset was identified after inspecting the outcomes, not preregistered. "
        "Its purpose is to bound industrial relevance, **not** rescue a significant p-value. "
        "The native compiler baseline ties v1 at 100% on these 18 plausible consumer examples.",
        "", "For those 18 cases, the native compiler-hint baseline uses "
        f"{sensitivity['after_excluding_explicit_test_fixture_import']['mean_compiler_diagnostic_additional_compilations']:.2f} "
        "additional Cargo checks per example, while v1 uses "
        f"{sensitivity['after_excluding_explicit_test_fixture_import']['mean_guided_additional_compilations']:.2f}. "
        "The paired difference (compiler minus v1) is "
        f"{sensitivity['after_excluding_explicit_test_fixture_import']['compiler_minus_guided_additional_compilations']:.2f} "
        "checks, exact repository-cluster 95% CI "
        f"{ci(sensitivity['after_excluding_explicit_test_fixture_import']['compiler_minus_guided_compilation_project_cluster_ci'], percentage=False)}. "
        "This exploratory effort metric may be useful for a developer tool, but is **not** an observed "
        "upstream CI runtime, maintainer effort, or business return; it excludes indexing/preprocessing overhead.",
        "", "### Pre-registered secondary source-path algorithm", "",
        f"Among strictly independent sources, source-path v2 success@8 = {fmt(strict.get('pathaware_success_at_8'))}, "
        f"difference from random = {fmt(strict.get('pathaware_minus_random_success'))}, "
        f"repository-cluster 95% CI = {ci(strict.get('pathaware_minus_random_repository_cluster_bootstrap_95ci'))}. "
        f"Path-aware {strict.get('pathaware_secondary_completed', 0)}/{strict['positive_witnesses']} positive records are complete.",
        "", "### Mandatory compiler-diagnostic strong baseline", "",
        f"Rustc itself emits feature-gate hints in the default-profile error messages. "
        f"Among the strictly independent positive cases with completed matches "
        f"({strict.get('compiler_diagnostic_baseline_completed',0)}/{strict['positive_witnesses']}), "
        f"the diagnostic-first baseline success@8 = {fmt(strict.get('compiler_diagnostic_success_at_8'))}, "
        f"versus original v1 = {fmt(strict['guided_success_at_8'])}. "
        f"Direct actionable rustc feature hints were present in "
        f"{fmt(strict.get('compiler_diagnostic_hints_available_fraction'))} of the positive cases. "
        "It shares every default-check diagnostic with v1 and uses at most eight *additional* Cargo checks; "
        "this is a stronger state-of-practice challenge than uniform random search.",
        "", "The docs.rs feature-profile one-shot baseline passes all pre-screened mismatches by construction; "
        "its implementation cost is one compiler check but its flag set can be broad. "
        f"Average declared docs profile contains {strict['docs_profile_mean_feature_flags']:.2f} named feature flags across this strict positive subset; "
        f"v1 successful repairs request {strict['guided_feature_count_mean_on_success']} flags on average. "
        "A flag-count comparison is not a measured change in CI cost or semantic minimality; full dependency feature closure matters.",
        "", "## Five genuine public upstream CI snapshots", "",
        "Each row is a successful GitHub Actions workflow run on an upstream project at the recorded commit, "
        "with archived workflow source and SHA-256. These runs were NOT performed by N05. "
        "Their commit SHAs are not pinned to the 2025 crates.io packages used for example replay, so the table "
        "does not prove that a particular replayed failure passed this historical CI run. "
        "A missing literal consumer replay in one workflow is not proof no related check exists in reused actions or other workflows.",
        "", "| Repository | Upstream successful run | Cargo-hack command found in workflow | Doctest/all-target command found | N05 deployed? |",
        "|---|---|---|---|---|",
    ]
    for p in actual_ci["projects"]:
        lines.append(f"| {p['repo']} | [#{p['run_id']}]({p['run_url']}) (`{p['head_sha'][:10]}`) | "
                     f"{'Yes' if p['has_cargo_hack'] else 'No literal command'} | "
                     f"{'Yes' if p['has_doc_test_command'] else 'No literal command'} | No |")
    lines += [
        "", "This is stronger, publicly deployed state-of-practice context than a simulated random feature order; "
        "any industrial improvement claim requires a head-to-head run against these native gates and actual upstream decisions.",
        "", "## Independent upstream maintenance evidence and blind spots", "",
    ]
    for case in actual_ci["maintainer_fixes"]:
        lines.append(f"- [iced #{case['number']}]({case['html_url']}), closed {case['closed_at']}: "
                     f"**{case['title']}** — independently reported/accepted upstream documentation repair, "
                     "not credited to this method.")
    for target in historic["historical_targets"]:
        pre = target["releases"]["0.10.0"]["literal_snippets_mentioning_affected_api"]
        post = target["releases"]["0.12.0"]["literal_snippets_mentioning_affected_api"]
        lines.append(f"- Coverage for {target['description']}: {pre} eligible literal target code fences before the fixes, "
                     f"{post} after. These are **not detection successes**; upstream's affected API was outside the current extractor.")
    lines += [
        "", "## Actual version-specific documentation disclosure", "",
        "For four hand-selected first-holdout issue cases, independently fetch and hash the *actual rendered* version-specific rustdoc page:", "",
        "| Published version and API | Required feature visibly disclosed? | Source |",
        "|---|---|---|",
    ]
    for r in disclosed["cases"]:
        lines.append(f"| {r.get('crate')} {r.get('version')} — {r.get('expected_explicit_feature_statement')} | "
                     f"{'Yes' if r.get('matched_in_version_specific_rendered_text') else 'Not confirmed'} | "
                     f"[Version-specific rendered documentation]({r['source_url']}) |")
    lines += [
        "", "This is intentionally not a population-estimated false-positive rate. The four examples were targeted "
        "because they occurred in the old validation set; the checked pages already disclose a prerequisite and do not substantiate omissions.",
        "", "## Cargo feature-footprint caveat", "",
        f"The independent static closure audit covers {len(footprint['cases'])} prior successful minimized fixes. "
        f"{sum(bool(x['narrower_structural_subfeature_candidates']) for x in footprint['cases'])} contain a smaller transitive internal-feature-set candidate, "
        "requiring independent recompilation before it can be called an alternative repair. "
        "The tower `balance` one-flag fix enables seven non-default internal features while a narrower `util` direct flag is a structural candidate. "
        f"Actual independent Cargo checks now **confirm both patches compile**: the v1-suggested "
        f"`balance` enables {dominated['original_broad']['feature_closure_size']} internal Cargo features, "
        f"whereas `util` enables {dominated['narrow_candidate']['feature_closure_size']} on the same tower 0.5.2 consumer snippet. "
        "Therefore the one-flag certificate was correct only for requested-flag count, and was "
        "**not** optimal in feature closure or least-privilege configuration.",
        "", "## What is and is not demonstrated", "",
        "Observed: official published archives; direct compiler statuses and complete Cargo stdout/stderr; "
        "independent successful GitHub Actions runs and pinned workflow YAML; independent historical maintainer fixes; "
        "rendered documentation badges on four chosen examples.", "",
        "Not observed: N05 adopted into those upstream repos; actual maintained pull requests caused by N05; "
        "reduction in false CI quarantines or build failures; measured engineer-hours saved; "
        "a blinded human review of all alleged doc defects; a causal ROI estimate.", "",
        "## Prospective two-repository deployment design needed to close ROI evidence gap", "",
        "1. Obtain agreement from two independent maintainers/projects and archive the exact release tags, workflow YAML, runner environment, timestamps and permissions. Do not alter third-party repositories unilaterally.",
        "2. Freeze a blinded sample of newly modified feature-gated examples. Run native rustdoc/default doctests and cargo-hack feature powerset as active baselines, then N05 on the exact same release snapshot.",
        "3. Ask maintainers to decide *actionable omission vs already disclosed prerequisite* without revealing which tool raised an alert. Time the review and archive accepted/rejected documentation PRs with commit SHAs.",
        "4. Compare unique confirmed defects, false-positive proportion, fresh-runner CPU minutes, queue delay, repair latency, and developer effort. Report project-cluster CI and both positive and null cases.",
        "5. For industrial production ROI, include actual downstream user issue/CI failures associated with a published example and the observed changes after a correction; local hypothetical savings must remain explicitly modelled.",
        "", "## FSE 2027 Industry Track fit", "",
        "The [official FSE 2027 Industry Track call](https://conf.researchr.org/track/fse-2027/fse-2027-industry-papers) "
        "welcomes industrially relevant research even without an industrial partner, but calls for a clear industrial context and outcomes. "
        "The current research package supports a documented external-consumer compatibility observation. "
        "Do not submit a long-paper claim of measured industrial gains or general superiority if the above preregistered criteria fail.",
        "", "## Reproducibility and evidence boundaries", "",
        "- `prospective/PREREGISTRATION.md`, `prospective/data/frozen_sample.json`, pinned source archives & SHA-256, "
        "`prospective/results/checks/`, `check_logs/`, `search.jsonl`, `pathaware.jsonl`, `independent_validation.json`.",
        "- `industrial/public_records/` raw upstream API and workflow payloads with retrieval stamps and hashes; "
        "`industrial/historical/` pre/post published releases and zero-coverage results; "
        "`industrial/rendered/` version-specific HTML docs; `feature_footprint.json`.",
        "- `industrial/consumer_gate.py` and `github_actions_gate.yml` are reproducible integration templates only. "
        "They were not deployed to the upstream runs enumerated here.",
    ]
    dest = ROOT / "paper/INDUSTRIAL_VALIDATION.md"
    dest.write_text("\n".join(lines) + "\n")
    print("Wrote", dest, "with", len(lines), "lines")


if __name__ == "__main__":
    main()
