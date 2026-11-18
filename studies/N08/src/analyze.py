#!/usr/bin/env python3
"""Leakage-checked, equal-budget reviewer suggestion pilot for N08.

IMPORTANT: held-out labels are *observed human review participation*. They are
not independent expert-oracle labels, and this study cannot establish causality.
"""

import argparse
import collections
import datetime as dt
import itertools
import json
import math
import random
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RESULTS = ROOT / "results"
SEEDS = (17, 29, 43)
METHODS = ("popularity", "current_path", "source_only", "git_follow", "recency_follow",
           "sampled_load_balanced", "windowed_handoff")


def is_handoff(old_owners, new_owners, moved_files, substantive=True):
    """Control gate: no handoff for same-team renames or documentation-only edits."""
    return bool(moved_files and substantive and set(old_owners) and set(new_owners)
                and (set(old_owners) - set(new_owners)))


def is_bot_author(name):
    return bool(name and (name.lower().endswith('[bot]') or name.lower().startswith('app:')))


def parse_time(ts):
    return dt.datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else None


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(name, obj):
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def pr_data(repo, num):
    path = DATA / "pr_timelines" / f"{repo.replace('/', '__')}__{num}.json"
    if not path.exists():
        return None
    pr = read_json(path)
    requests = DATA / "request_timelines" / f"{repo.replace('/', '__')}__{num}.json"
    if requests.exists():
        pr['author'] = read_json(requests).get('pr_author')
    return pr


def reviewed_users(pr, before=None):
    if not pr:
        return set()
    merged = parse_time(pr.get("merged_at"))
    users = set()
    for r in pr.get("reviews", []):
        at = parse_time(r["submitted_at"])
        if r["state"] in ("APPROVED", "CHANGES_REQUESTED") and (before is None or at < before) and (not merged or at <= merged):
            users.add(r["login"].lower())
    return users


def reviewer_counts(entries, t):
    counts = collections.Counter()
    for pr in entries:
        if pr is None:
            continue
        merged = parse_time(pr.get("merged_at"))
        # Do not borrow information from an unmerged/open PR or another PR's future.
        if not merged or merged >= t:
            continue
        counts.update(reviewed_users(pr, before=t))
    return counts


def recency_counts(entries, t, half_life_days=180):
    counts = collections.defaultdict(float)
    for pr in entries:
        if not pr:
            continue
        merged = parse_time(pr.get('merged_at'))
        if not merged or merged >= t:
            continue
        age = (t - merged).total_seconds() / 86400
        weight = 2 ** (-age / half_life_days)
        for user in reviewed_users(pr, before=t):
            counts[user] += weight
    return dict(counts)


def sampled_workload(entries, t, lookback_days=30):
    counts = collections.Counter()
    for pr in entries:
        if not pr:
            continue
        merged = parse_time(pr.get('merged_at'))
        if merged and 0 < (t - merged).total_seconds() / 86400 <= lookback_days:
            counts.update(reviewed_users(pr, before=t))
    return counts


def recommend(method, source, target, global_pop, days_since, k=2, excluded_user=None,
              temporal=None, workload=None, grace_days=180):
    if method == "popularity":
        scores = {u: float(v) for u, v in global_pop.items()}
    elif method == "current_path":
        scores = {u: float(v) for u, v in target.items()}
    elif method == "source_only":
        scores = {u: float(v) for u, v in source.items()}
    elif method == "git_follow":
        scores = {u: 1.0 * source.get(u, 0) + target.get(u, 0) for u in set(source) | set(target)}
    elif method in ('recency_follow', 'sampled_load_balanced'):
        scores = dict(temporal or {})
        if method == 'sampled_load_balanced':
            scores = {u: score / (1 + .2 * (workload or {}).get(u, 0)) for u, score in scores.items()}
    elif method == "windowed_handoff":
        # Old reviewer knowledge expires linearly over a 180-day handoff window;
        # historical new-path reviewer evidence is counted independently.
        legacy_weight = max(0., 1. - days_since / grace_days) if grace_days > 0 else 0.
        scores = {u: legacy_weight * source.get(u, 0) + target.get(u, 0) for u in set(source) | set(target)}
    else:
        raise ValueError(method)
    # Equal number of recommendations where observable candidate pools permit;
    # fallback is only from timestamp-safe, sampled repository history.
    for u in global_pop:
        scores.setdefault(u, 0.)
    if excluded_user:
        scores.pop(excluded_user.lower(), None)
    return [u for u, _ in sorted(scores.items(), key=lambda uv: (-uv[1], -global_pop.get(uv[0], 0), uv[0]))[:k]]


def make_history(events, max_train, max_test):
    historical, candidates = [], []
    coverage = []
    for event in events:
        role_prs = {}
        for role, n in [("before", max_train), ("after", max_test)]:
            records = event["histories"][role]["records"]
            selected = list(reversed(records))[:n] if role == "before" else records[:n]
            selected = [x for x in selected if x["pr"] != event["migration_pr"]]
            role_prs[role] = selected
        before = []
        for rec in role_prs["before"]:
            pr = pr_data(event["repo"], rec["pr"])
            if pr and parse_time(pr.get("merged_at")) and parse_time(pr["merged_at"]) < parse_time(event["merged_at"]):
                before.append(pr)
                historical.append(pr)
        after = []
        for rec in role_prs["after"]:
            pr = pr_data(event["repo"], rec["pr"])
            if not pr or not pr.get("opened_at") or not pr.get("merged_at"):
                continue
            if parse_time(pr["opened_at"]) <= parse_time(event["merged_at"]):
                continue
            after.append(pr)
            historical.append(pr)
        # Dedup is in the scoring stage via one PR per unique (repo, id).
        coverage.append({"event": event["id"], "migration_pr": event["migration_pr"],
                         "pre_path_prs": len(role_prs["before"]), "pre_timelines_valid": len(before),
                         "post_path_prs": len(role_prs["after"]), "post_timelines_valid": len(after),
                         "post_human_review_prs": sum(bool(reviewed_users(x)) and not is_bot_author(x.get('author')) for x in after),
                         "post_bot_authored_prs": sum(is_bot_author(x.get('author')) for x in after),
                         "pre_query_truncated": event["histories"]["before"]["truncated"],
                         "post_query_truncated": event["histories"]["after"]["truncated"],
                         "handoff_verified": event["valid"],
                         "renamed_files": len(event["rename_pairs"])})
        candidates.append((event, before, sorted(after, key=lambda x: x["opened_at"])))
    # One public PR may appear in more than one event; it still contributes once
    # to the sampled repository-wide fallback reviewer pool.
    pooled = {(x["repo"], x["pr"]): x for x in historical}
    return candidates, list(pooled.values()), coverage


def observe(events, k, max_train, max_test, code_only=False, focused_only=False, grace_days=180):
    groups, global_history, coverage = make_history(events, max_train, max_test)
    rows = []
    for event, before, after in groups:
        migration_time = parse_time(event["merged_at"])
        if not is_handoff(event["old_owner"], event["new_owner"], event["rename_pairs"]):
            continue
        for pr in after:
            if is_bot_author(pr.get('author')):
                continue
            observed = reviewed_users(pr)
            if not observed:
                continue
            if not pr.get('author'):
                raise ValueError(f"Missing PR author for {event['repo']} #{pr['pr']}: author-safe evaluation cannot proceed")
            if code_only or focused_only:
                audit_path = DATA / "diff_audit" / f"{event['id']}__{pr['pr']}.json"
                key = "focused_code_touched" if focused_only else "code_touched"
                if not audit_path.exists() or not read_json(audit_path).get(key):
                    continue
            opened = parse_time(pr["opened_at"])
            days = (opened - migration_time).total_seconds() / 86400
            source = reviewer_counts(before, opened)
            new_path = reviewer_counts(after, opened)
            global_pop = reviewer_counts(global_history, opened)
            source_temporal = recency_counts(before, opened)
            target_temporal = recency_counts(after, opened)
            temporal = {u: source_temporal.get(u, 0) + target_temporal.get(u, 0)
                        for u in set(source_temporal) | set(target_temporal)}
            workload = sampled_workload(global_history, opened)
            suggestion_lists = {m: recommend(m, source, new_path, global_pop, days, k, pr['author'],
                                             temporal=temporal, workload=workload,
                                             grace_days=grace_days) for m in METHODS}
            rows.append({"event": event["id"], "repo": event["repo"], "pr": pr["pr"],
                         "pr_author": pr['author'],
                         "url": pr["source_url"], "opened_at": pr["opened_at"],
                         "days_after_handoff": round(days, 3),
                         "actual_reviewers": sorted(observed),
                         "pre_source_reviewer_pool": dict(source),
                         "previous_target_reviewer_pool": dict(new_path),
                         "reviewers_ever_observed_in_pool": len(global_pop),
                         "suggestions": suggestion_lists,
                         "method_outcomes": {m: {"recall": len(observed.intersection(users)) / len(observed),
                                                  "hit": int(bool(observed.intersection(users))),
                                                  "suggestions": len(users)}
                                             for m, users in suggestion_lists.items()}})
    return rows, coverage


def exact_sign_flip(event_diffs):
    nonzero = [v for v in event_diffs if abs(v) > 1e-12]
    if not nonzero:
        return 1.0
    obs = abs(sum(nonzero))
    extremes = 0
    for signs in itertools.product((-1, 1), repeat=len(nonzero)):
        if abs(sum(a * b for a, b in zip(nonzero, signs))) >= obs - 1e-10:
            extremes += 1
    return extremes / (2 ** len(nonzero))


def clustered_summary(rows, outcome="recall", n_boot=3000):
    grouped = collections.defaultdict(list)
    for row in rows:
        grouped[row["event"]].append(row)
    if not grouped:
        return {}
    events = sorted(grouped)
    results = {}
    for m in METHODS:
        event_means = [statistics.mean(r["method_outcomes"][m][outcome] for r in grouped[e]) for e in events]
        overall = statistics.mean(event_means)
        cis = []
        for seed in SEEDS:
            rng = random.Random(seed)
            trials = sorted(statistics.mean(rng.choices(event_means, k=len(event_means))) for _ in range(n_boot))
            cis.append([trials[int(0.025 * (n_boot - 1))], trials[int(0.975 * (n_boot - 1))]])
        results[m] = {"event_macro_mean": overall,
                      "event_bootstrap_95ci_seed17": cis[0],
                      "bootstrap_ci_seed_variation": cis,
                      "event_count": len(events), "pr_count": len(rows),
                      "event_means": {e: v for e, v in zip(events, event_means)}}
    for competitor in ("current_path", "source_only", "git_follow", "recency_follow",
                       "sampled_load_balanced", "popularity"):
        diff = [results["windowed_handoff"]["event_means"][e] - results[competitor]["event_means"][e] for e in events]
        results["windowed_handoff"]["comparison_vs_" + competitor] = {
            "event_macro_delta": statistics.mean(diff),
            "two_sided_exact_event_sign_flip_p": exact_sign_flip(diff),
            "event_deltas": dict(zip(events, diff)),
            "events_with_positive_delta": sum(d > 1e-12 for d in diff),
            "events_with_negative_delta": sum(d < -1e-12 for d in diff)}
    return results


def report_markdown(events, rows, coverage, summaries):
    lines = ["# N08: Reproducible observational pilot — results and limitations", "",
             "All numbers below are computed from publicly visible pull requests in the selected repositories. They are **not** randomized interventions, independently adjudicated expertise labels, or estimates of causal reduction in review delays.", "",
             "## Dataset validation", "",
             "| Event | Migration PR | Verified cross-team renames | Historical PRs with timelines | Follow-up PRs with timelines | With human decision reviews | Truncated commit query |", "|---|---:|---:|---:|---:|---:|---|"]
    for c in coverage:
        trunc = "yes" if c["pre_query_truncated"] or c["post_query_truncated"] else "no"
        event = next(e for e in events if e["id"] == c["event"])
        lines.append(f"| {c['event']} | [#{c['migration_pr']}](https://github.com/{event['repo']}/pull/{c['migration_pr']}) | {c['renamed_files']} | {c['pre_timelines_valid']} | {c['post_timelines_valid']} | {c['post_human_review_prs']} | {trunc} |")
    lines += ["", "The commit-path API may include a migration commit timestamped before its merge; that PR is explicitly removed. Events are checked against the CODEOWNERS revision on each side of the migration and their actual Git-detected rename pairs. A future PR must open after the migration and merge to be evaluated.", "",
              "## Reviewer-retrieval task: fixed budget", "",
              "The observed positive label is a distinct human account that submitted APPROVED or CHANGES_REQUESTED before that PR merged. Reviewers are ranked using only earlier merged PRs; the PR author is excluded. K=2 recommendations. 'Current path' has no cross-path memory; 'source only' inherits pre-move reviewers; 'git follow' permanently pools both; 'recency follow' uses a fixed 180-day reviewer half-life; 'sampled load balanced' penalizes activity observed in a sampled 30-day window; 'windowed handoff' gives source-history a linearly decreasing weight over 180 days. The pooled popularity and workload fallback are learned from this *sampled* repository history, not the whole repository.", "",
              "| Reviewer strategy | Event-macro Recall@2 | Event-cluster bootstrap 95% CI | Hit@2 |", "|---|---:|---:|---:|"]
    for m in METHODS:
        if m not in summaries["recall"]:
            continue
        r = summaries["recall"][m]
        h = summaries["hit"][m]
        low, high = r["event_bootstrap_95ci_seed17"]
        lines.append(f"| {m} | {r['event_macro_mean']:.3f} | [{low:.3f}, {high:.3f}] | {h['event_macro_mean']:.3f} |")
    comp = summaries["recall"].get("windowed_handoff", {})
    lines += ["", "### Paired comparisons (event-level; exploratory)", "",
              "| Comparator | Recall@2 difference (pp) | Two-sided exact sign-flip p | Events better / worse |", "|---|---:|---:|---:|"]
    for m in ("current_path", "source_only", "git_follow", "recency_follow", "sampled_load_balanced", "popularity"):
        x = comp.get("comparison_vs_" + m, {})
        if x:
            lines.append(f"| {m} | {100*x['event_macro_delta']:+.1f} | {x['two_sided_exact_event_sign_flip_p']:.3f} | {x['events_with_positive_delta']} / {x['events_with_negative_delta']} |")
    lines += ["", "## Scientific boundary", "",
              f"- This dataset comes from **{len(set(e['repo'] for e in events))} public repositories**, with unbalanced event counts. The migrations within each repository are correlated; simple event bootstrap cannot fully recover cross-company generalization.",
              "- Review participation is selected by the *existing* routing process and is not an independent 'true expert' label. The proposed thesis of missing expert coverage therefore remains **untested**.",
              "- Teams in CODEOWNERS are not publicly resolvable to their complete historical individual membership. The company CODEOWNERS policy is verified, but no claim is made that the `current_path` strategy is literal GitHub CODEOWNERS assignment.",
              "- Candidate sampling is path-based; Git commit histories may include broadly changed files, documentation-only changes, refactors, and later renames. Mechanically retrieved PR diffs and maintainer adjudication are needed before claiming semantically substantive PRs. For a partial team transfer, the source-reviewer pool includes members of retained and removed teams.",
              "- Neither review requests nor independent handoff/triage decisions were extracted. Response time or industrial ROI cannot be estimated causally from this data.",
              "- Exactly three bootstrap seeds (17, 29, 43) validate numerical reproducibility; they do not constitute three independent experimental worlds.",
              "- Strong competitors such as full history-aware recommendation, codeowners-diff, and workload-aware ranking need additional implementation and equivalent input data before formal submission.",
              "", "## Submission gate", "",
              "The pre-registered improvement target was ≥10 pp expert coverage over the strongest baseline at equal budget. Observed reviewer Recall@2 is only a diagnostic proxy; **do not claim this submission gate passed**, irrespective of its numeric value. Minimum remaining evidence: independent expert labels, additional repositories, controls, complete review requests/events, semantic PR adjudication, and workload calibration.", ""]
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--k", type=int, default=2)
    p.add_argument("--max-train", type=int, default=12)
    p.add_argument("--max-test", type=int, default=20)
    p.add_argument("--code-only", action="store_true", help="mechanical code-edit sensitivity, not semantic truth")
    p.add_argument("--focused-only", action="store_true", help="exploratory focus filter: >=10% of changed files in moved subtree and <=100 total")
    p.add_argument("--tag", default="", help="prefix result filenames to keep sensitivity runs separate")
    args = p.parse_args()
    events = [read_json(path) for path in sorted((DATA / "events").glob("*.json"))]
    if not events:
        raise SystemExit("No verified events; first run python src/harvest.py --timelines")
    rows, coverage = observe(events, args.k, args.max_train, args.max_test, args.code_only, args.focused_only)
    summaries = {metric: clustered_summary(rows, metric) for metric in ("recall", "hit")}
    prefix = args.tag + "_" if args.tag else ""
    save_json(prefix + "predictions.json", rows)
    save_json(prefix + "sampling_audit.json", coverage)
    save_json(prefix + "metrics.json", {"k": args.k, "code_only": args.code_only, "focused_only": args.focused_only,
                               "evaluated_prs": len(rows),
                               "nonempty_events": len(set(r["event"] for r in rows)),
                               "strategies": list(METHODS), "seeds": list(SEEDS),
                               "metrics": summaries})
    report = report_markdown(events, rows, coverage, summaries)
    (RESULTS / (prefix + "PAPER_TABLES_AND_LIMITATIONS.md")).write_text(report, encoding="utf-8")
    print("Evaluated", len(rows), "human-reviewed PRs across", len(set(r["event"] for r in rows)), "events")
    for name in METHODS:
        d = summaries["recall"].get(name)
        if d:
            print(f"{name:20s} event-macro Recall@{args.k} {d['event_macro_mean']:.4f}")


if __name__ == "__main__":
    main()
