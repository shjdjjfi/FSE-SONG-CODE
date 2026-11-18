# Independent expertise labeling protocol (not yet performed)

The attached CSV intentionally contains **blank labels**. This is a real protocol for a required future experiment; the presence of rows does not mean annotation happened.

1. Recruit two reviewers familiar with industrial code review, blinded to the ranking algorithms, the experimental predictions, actual review outcomes, and to each other's ratings. Show only the migration PR and subsequent PR file diff in the assigned CSV row. Reviewers should avoid the PR Conversation page and review timeline until the ratings are locked.
2. Establish **semantic continuity**: does the subsequent PR modify the moved component's original business logic, not a broad automated formatting, translation, generated-code, or test-only change? Enter yes/no/unknown and cite the exact changed files and migration context.
3. Establish independently whether **knowledge from the old team is needed** to review this specific change, and separately whether new team expertise is needed. Cite actionable rationale: original architecture decisions, a pre-migration invariant, or a documented prior incident. Merely seeing a `git mv`, former CODEOWNERS handle, or high git contribution count is insufficient.
4. Supply named expert handles only when there is independent publicly verifiable evidence (original author of relevant design decision, documented module maintainer, domain design review) *before the target PR opened*. An owner team name cannot be treated as a resolved human member.
5. Use `unknown` whenever the data cannot justify an expert label; do not treat unknown as negative. Record confidence 1–5 and at least one non-circular evidence URL. Disallow the evaluated PR's reviewers and requested-reviewers list as labeling evidence.
6. Freeze R1 and R2 sheets separately. Compute Cohen's kappa (binary labels after excluding unknown), report unknown and disagreement rates, and adjudicate by an independent third reviewer. The adjudicated oracle can then be scored at fixed K=1,2,3,5 with per-project and per-migration confidence intervals.
7. Freeze labels and decision thresholds before inspecting the algorithm predictions. Only then estimate expert recall and extra-review workload. Review request/response times are **observational** unless a prospective deployment is randomized.

No annotator, oracle label, team membership, or measured expert-recall result is supplied by this package.
