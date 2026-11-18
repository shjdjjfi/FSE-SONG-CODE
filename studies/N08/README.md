# N08 — From Owners to Experts? Measuring What Public Traces Can Identify

Reproducible empirical research bundle for the **sixth** idea in `FINAL_7_IDEAS.md` (FSE 2027 Industry Track). **The latest research pivot asks whether public GitHub traces can identify expert knowledge coverage after CODEOWNERS cross-team transfers**, not whether a recommender is more accurate. This is an **executed, explicitly scoped observational study**, not a claim that unavailable independent expertise, human membership, or industrial ROI was established.

## 2026-11-15 new measurement-study experimental results — START HERE

The complete new offline measurement pipeline, a manuscript-ready English
experiments draft, a Chinese report, four tables, four figures (SVG/PNG),
per-PR witnesses, precise conditional bounds, 4,500 mathematical validation
tests and a structured verification audit are in **`measurement/`**.

- Read **`measurement/README.md`** for the revised question, formulas, evidence
  ledger, limitations and exact offline reproduction commands.
- Read **`measurement/results/PAPER_EXPERIMENTS_EN.md`** for the English paper
  experimental narrative, and **`measurement/SUBMISSION_POSITIONING.md`** for
  the scoped abstract and honest FSE readiness checklist.
- 9 real migrations, 114 PR–event pairs / 103 unique PRs, 48 changed
  recommendations. In 41/48 switched cases both exclusive candidates have
  prior module-review history; in 5/48 both sides submitted a formal review
  on the target PR. These public signals cannot decide *which person had the
  necessary expertise*.
- Under the **unsupported, deliberately optimistic** premise of exactly one
  qualified expert among actual reviewers, the sharp event-macro K=2
  policy-difference identified region is **[-7.1,+12.7] percentage points**.
  Allowing prior module reviewers yields **[-33.6,+40.5] pp**. They are not
  statistical confidence intervals; no independent expertise oracle exists.
- GitHub REST Issue Events exposed team-request slugs in two archived cases,
  correcting the rendered HTML's opaque “a team” label. The preselected
  36-case audit stopped after **2/36** because of HTTP 403. This is a
  case-level correction, not a prevalence estimate.
- All new mathematical claims were checked by 4,500 brute-force synthetic
  comparisons (zero disagreements). The earlier +10 pp independent-expert
  performance target is **not** met and the work does not claim real savings.

To reproduce from the `n08_study/` directory without requesting GitHub API
access:

```bash
python measurement/run_measurement.py
python measurement/validate_bounds.py
python measurement/robustness.py
python measurement/build_paper.py
python -m unittest discover -s measurement -p 'test_*.py' -q
python measurement/verify.py
```

The prior algorithm-recommendation pilot is kept below strictly for historical
transparency, not as the revised paper's central positive finding.

## 2026-11-15 follow-up: evidence, expert role, membership, ROI, performance gate

The researcher has now executed additional real-data experiments. **Important: the original four acceptance gates remain unpassed**, and the added evidence is explicitly scoped rather than fabricated:

- Rechecked **93 of 114** PR patches with source SHA-256 verification; 21 remaining requests returned GitHub **HTTP 429** and were not bypassed.
- Performed **one model-assisted researcher's review** of the source excerpts: 46 semantically substantive, 2 presentational-only, 66 unknown. This judgment occurred after seeing earlier method results, so **it is not a blind or independent expert oracle**. No named expert who was independently known to be available at that time is asserted.
- Audited historical CODEOWNERS team handles and before-transfer review events. Public team endpoints for all ten distinct referenced teams returned **8×401 and 2×403**; code contributors are listed only as **historically observed reviewers**, never as proven team members.
- Replayed review requests in shadow mode: 62 person–PR suggestion switches in 48 PRs; 17 swapped-in accounts also naturally reviewed. Hypothetical reviewer-hour break-even was computed, but **no reviewer was invited by the proposed method and no realized industrial savings were measured**.
- Evaluated 80-config commit-author + review-request + review-history hybrid using strictly historical prequential model selection and event-held-out analysis. Prequential reviewer Recall@2 **35.0%** vs current-path 30.1%; event-held-out hybrid Recall@2 **28.8%**. Both are proxies on the previously explored cohort, far from confirming +10pp independent expert coverage.

Most useful starting document: `results/FOLLOWUP_EXPERIMENT_REPORT_CN.md`. Exact evidence is in `results/FINAL_SUBMISSION_GATE_AUDIT.json`; per-PR model-researcher reasoning is `results/SINGLE_RESEARCHER_ANNOTATIONS.csv` and `results/single_researcher_patch_annotation.json`.

Publication artifacts added: `results/REVISED_EXPERIMENTS_SECTION_EN.md` (qualified English results), `results/PROSPECTIVE_INDUSTRIAL_EVALUATION_PLAN.md` (the actual external evidence still required), and Figures 4–5 in `results/figures/` (observed proxy recall and **hypothetical** cost sensitivity, respectively).

Reproduce the **offline** follow-up on the frozen data (from `n08_study/`):

```bash
python src/shadow_roi.py
python src/experiment_cv.py
python src/researcher_annotations.py
python src/finalize_followup.py
python src/plot_followup.py
python src/verify_followup.py
python -m unittest discover -s tests -v
```

The optional `python src/augment_evidence.py` and `python src/audit_membership.py` consult public GitHub and may be rate limited or require credentials; no rerun is necessary for the saved experiment. The historical membership probe intentionally does not authenticate or infer private employee identity.

## What was actually executed

- Reconstructed **nine** genuinely merged cross-path / code-owner handoffs in **two** public industrial repositories: `bitwarden/clients` and `grafana/grafana`.
- Verified **112** Git-detected rename pairs and before/after historical CODEOWNERS entries against exact merge/base SHA snapshots.
- Collected 365-day pre- and post-handoff path histories, then selected at most 12 recent pre-handoff PRs for training and the first 20 eligible post-handoff PRs per event for prediction.
- Extracted actual human review decision events, author identity and historical reviewer-request events from public PR timelines. Nine PRs' human review decisions were independently checked against GitHub REST API responses.
- Evaluated seven equal-budget reviewer-retrieval strategies (K=1,2,3,5), including a temporary 180-day knowledge-transfer proposal and temporal/workload-based comparators. **PR authors and robot-authored outcome PRs are excluded.**
- Performed 6 externally grounded no-intervention negative controls, PR code-diff audits, event-cluster bootstrap, exact sign-flip tests, grace-window ablations, time strata and two-project sensitivity analyses.
- Produced publication figures, bilingual summaries, and a **blank** independent expert-label annotation queue (two raters, no fabricated annotations).

The observed outcome is **retrieval of historical reviewers who eventually submitted an APPROVED or CHANGES_REQUESTED review**, *not* independently established reviewer expertise. The original >10-percentage-point expert-recall gate cannot be declared met.

## Reproduce from the frozen collected evidence (offline)

Python 3.10+ with `lxml` and `matplotlib` is required; measured in Python 3.12.14, lxml 6.1.1, matplotlib 3.10.8.

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python src/analyze.py
python src/analyze.py --code-only --tag code
python src/analyze.py --focused-only --tag focused
python src/audit_diffs.py
python src/audit_requests.py
python src/sensitivity.py
python src/plots.py
python src/export_annotations.py
```

Run these commands **from the `n08_study/` directory**. They reuse the already downloaded, provenance-rich, compact evidence in `data/`. `audit_diffs.py` and `audit_requests.py` also cache their public-source checks and should not redownload unless explicitly asked to refresh.

To independently refresh from public GitHub, use:

```bash
python src/harvest.py --timelines --max-train 12 --max-test 20
python src/negative_controls.py
python src/validate_reviews.py
python src/audit_diffs.py --overwrite
python src/audit_requests.py --overwrite
```

Re-fetching GitHub REST API endpoints may be rate-limited without authentication. The dataset is time-frozen by exact commit and date windows, but HTML rendering and API returned snapshots may change; compare hashes and validation results before claiming bit-for-bit re-identification.

## Where to look

| Path | Purpose |
|---|---|
| `results/EXPERIMENT_REPORT_CN.md` | Comprehensive Chinese report with final measured evidence, threats, and submission gates |
| `results/EXPERIMENTS_SECTION_EN.md` | FSE-style English experimental section draft, explicitly identifying proxy outcome |
| `results/PAPER_TABLES_AND_LIMITATIONS.md` | Main event tables, results, paired tests |
| `results/ROBUSTNESS_TABLES.md` | K budgets, focus filtering, grace-window, time and repository strata |
| `results/figures/` | Recomputed scientific figures (SVG and PNG) |
| `results/negative_controls.json` | Six real controls showing the eligibility gate did not create spurious transfers |
| `results/rest_review_validation.json` | Direct HTML-versus-REST review cross-checks |
| `results/request_audit.json` | Historical human and anonymized team-review request audit |
| `results/BLIND_EXPERT_ANNOTATION_QUEUE.csv` | **Unfilled** double-annotation sheet |
| `results/EXPERT_ANNOTATION_PROTOCOL.md` | Independent oracle construction protocol |
| `results/metrics.json` | Machine-readable primary results, event-level bootstrap, exact comparisons |
| `data/events/`, `data/commit_queries/`, `data/pr_timelines/` | Compact timestamped evidence, source URLs and raw source SHA-256 hashes |
| `config/events.json` | Preidentified migration event definitions and expected owner transitions |
| `src/` and `tests/` | Fetch/analysis/figure implementations and controlled tests |

## Research integrity and redistribution

Public GitHub PR pages and patches are **not** redistributed as complete HTML or diffs. The archive contains normalized public event derivatives, links, hashes, limited public reviewers' GitHub handles, and code to re-fetch. Some API metadata is cached as JSON for verification and may contain public author information. Do not infer individual code-owner team membership or unpublished reviewer expertise from this archive. See `DATA_AND_LIMITATIONS.md` and the annotation protocol.

## Submission-ready status

**No.** A main experiment that only measures similarity to the observed reviewers is endogenous: these reviewers were selected under the existing review process. Completing the paper requires independent expert labels and team membership resolution, stronger full-history/workload baselines, additional independent organization events, human semantic adjudication, and a valid design before asserting response-time or productivity benefit. These tasks are not marked as complete.
