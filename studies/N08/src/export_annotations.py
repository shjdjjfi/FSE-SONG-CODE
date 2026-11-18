#!/usr/bin/env python3
"""Prepare blinded, unfilled independent human expert-labeling sheets."""

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"


def main():
    rows = json.loads((RESULTS / "predictions.json").read_text())
    event_data = {p.stem: json.loads(p.read_text()) for p in (ROOT / "data" / "events").glob("*.json")}
    diff_data = { (v["event"], v["pr"]): v for v in json.loads((RESULTS / "diff_audit_summary.json").read_text())["rows"]}
    fieldnames = ["annotation_id", "annotator", "migration_event", "repository", "migration_pr_url", "evaluation_pr_url",
                  "source_codeowner_team_handles", "target_codeowner_team_handles", "migrated_target_path", "changed_files_under_target",
                  "automatic_code_touched", "automatic_focus_filter", "semantic_continuity_yes_no_unknown",
                  "legacy_team_expertise_needed_yes_no_unknown", "new_team_expertise_needed_yes_no_unknown",
                  "independently_verifiable_expert_handle", "evidence_url_to_source_or_discussion", "annotator_confidence_1_to_5", "rationale"]
    outpath = RESULTS / "BLIND_EXPERT_ANNOTATION_QUEUE.csv"
    with outpath.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            e, d = event_data[row["event"]], diff_data.get((row["event"], row["pr"]), {})
            for rater in ("R1", "R2"):
                writer.writerow({"annotation_id": f"{row['event']}-{row['pr']}-{rater}", "annotator": rater,
                                 "migration_event": row["event"], "repository": row["repo"],
                                 "migration_pr_url": f"https://github.com/{row['repo']}/pull/{e['migration_pr']}",
                                 "evaluation_pr_url": row["url"] + "/files",
                                 "source_codeowner_team_handles": " ".join(e["old_owner"]),
                                 "target_codeowner_team_handles": " ".join(e["new_owner"]),
                                 "migrated_target_path": e["new_prefix"],
                                 "changed_files_under_target": d.get("changed_files_under_target", ""),
                                 "automatic_code_touched": d.get("code_touched", ""),
                                 "automatic_focus_filter": d.get("focused_code_touched", "")})
    protocol = """# Independent expertise labeling protocol (not yet performed)

The attached CSV intentionally contains **blank labels**. This is a real protocol for a required future experiment; the presence of rows does not mean annotation happened.

1. Recruit two reviewers familiar with industrial code review, blinded to the ranking algorithms, the experimental predictions, actual review outcomes, and to each other's ratings. Show only the migration PR and subsequent PR file diff in the assigned CSV row. Reviewers should avoid the PR Conversation page and review timeline until the ratings are locked.
2. Establish **semantic continuity**: does the subsequent PR modify the moved component's original business logic, not a broad automated formatting, translation, generated-code, or test-only change? Enter yes/no/unknown and cite the exact changed files and migration context.
3. Establish independently whether **knowledge from the old team is needed** to review this specific change, and separately whether new team expertise is needed. Cite actionable rationale: original architecture decisions, a pre-migration invariant, or a documented prior incident. Merely seeing a `git mv`, former CODEOWNERS handle, or high git contribution count is insufficient.
4. Supply named expert handles only when there is independent publicly verifiable evidence (original author of relevant design decision, documented module maintainer, domain design review) *before the target PR opened*. An owner team name cannot be treated as a resolved human member.
5. Use `unknown` whenever the data cannot justify an expert label; do not treat unknown as negative. Record confidence 1–5 and at least one non-circular evidence URL. Disallow the evaluated PR's reviewers and requested-reviewers list as labeling evidence.
6. Freeze R1 and R2 sheets separately. Compute Cohen's kappa (binary labels after excluding unknown), report unknown and disagreement rates, and adjudicate by an independent third reviewer. The adjudicated oracle can then be scored at fixed K=1,2,3,5 with per-project and per-migration confidence intervals.
7. Freeze labels and decision thresholds before inspecting the algorithm predictions. Only then estimate expert recall and extra-review workload. Review request/response times are **observational** unless a prospective deployment is randomized.

No annotator, oracle label, team membership, or measured expert-recall result is supplied by this package.
"""
    (RESULTS / "EXPERT_ANNOTATION_PROTOCOL.md").write_text(protocol, encoding="utf-8")
    print("Created", len(rows) * 2, "blank annotator rows for", len(rows), "PR-event pairs")


if __name__ == "__main__":
    main()
