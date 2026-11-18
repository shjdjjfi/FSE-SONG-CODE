# N08 research pivot — public trace identifiability after CODEOWNERS transfers

**Research question:** After a CODEOWNERS transfer across teams, can public
software-development records establish whether the relevant *human knowledge*
was consulted? **Not:** Did a new recommender improve expert accuracy?

The frozen study uses nine actual merged migration events in two public
industrial GitHub repositories, 112 Git-verified moved-file pairs and 114
PR–migration-event pairs (103 unique PRs). It is an observational, curated
corpus. A PR can be counted in two or more migration events; all principal
outcomes use migration-event macro aggregation and unique-PR sensitivity is
reported separately.

## What was measured versus what was not

| Object | Status | Source / limitation |
| --- | --- | --- |
| Path lineage and old/new CODEOWNERS team handles | 114/114 | Frozen git commits and owner rules |
| Whole-PR HTML anonymous team-request event | 110/114 | Archived public PR timelines |
| Named reviewer request by 72h (excluding author) | 56/114 | Requests before PR merge, timestamp-filtered |
| Named request any time before merge (excluding author) | 96/114 | Same |
| Actual human formal decision reviewer | 114/114 | PR timeline; 9/9 external REST case validations |
| Team request slug visible in *public Issue Events REST* | 2/2 checked | Registered 36-pair sample halted after HTTP403; no prevalence estimate |
| Historical person-to-CODEOWNERS-team membership | 0 independently verified | Public historical team-member lists not available in this corpus |
| Independently adjudicated PR-specific human expertise | 0 | Public reviewing is not independent validation of competence |
| Realized industrial intervention benefit | Not measured | No method-driven reviewer invitations or enterprise counterfactual |

The historical member count of zero is a **verification count**, not evidence
that no team members existed. Similarly, two API requests revealing slugs
disprove blanket team-handle opacity but cannot establish how common public
team-request visibility is. Team-request events refer to the entire PR; the
record does not causally assign the request to the migrated file.

## Analysis design

1. Freeze public migration and PR traces. Confirm exact old/new CODEOWNERS
   snapshots; construct event-aware historical module-reviewer pools without
   using future information for recommendations.
2. Enumerate which evidence channels are observable on the **same** PR cohort:
   teams from policy, team requests, individual requests, decision reviewers,
   historical participants, formal dated memberships and expertise judgments.
3. Compare two *already fixed* K=2 reviewer lists: current-path and temporary
   180-day handoff. These are probes, **not proposed field interventions**.
4. Construct opposing expert allocations when two exclusively suggested
   candidates have prior module reviews or target PR decisions. This proves
   observational equivalence conditional on what expert allocations remain
   feasible. It does **not** assert which person is actually qualified.
5. For an allowed possible-expert set U and exactly m experts, calculate the
   sharp difference bounds by sorting
   `1[u in handoff] - 1[u in current_path]` over u in U and averaging the m
   smallest / largest values. Compute event-macro aggregates. Repeat for m=1
   and m=2 and progressively wider U definitions.
6. Redefine “ground truth” as observed decision reviewers, review comments,
   early reviewer requests, late requests, old-module and new-module review
   participants. Report proxy-specific variation and within-event ranking
   reversals on *matched eligible PRs*.
7. Stress-test K=1,2,3,5, grace=30,90,180,365 days, code-substance filters,
   pre/post 90-day cohorts, per-repository results and 103-unique-PR dedup.
8. Algebraically validate sharp bounds on **4,500 synthetic finite-set cases**
   via exhaustive enumeration. Synthetic cases validate formulae, not people.

The sharp regions are **identified sets under stated assumptions**; they are
not frequentist confidence intervals and do not address sampling error or
unobserved expertise outside U. Since the actual expert pool could include
people with *no* historical public footprint, even the broad U definition is
an assumption, not a guarantee.

## Offline reproduction (no GitHub API calls)

Run from `n08_study/` after installing `requirements.txt`:

```bash
python measurement/run_measurement.py
python measurement/validate_bounds.py
python measurement/robustness.py
python measurement/build_paper.py
python -m unittest discover -s measurement -p 'test_*.py' -v
python -m unittest discover -s tests -v
python src/verify.py
python src/verify_followup.py
python measurement/verify.py
python src/package.py
```

**Do not run `harvest_issue_events.py` to reproduce the frozen findings.** Its
stored sample consists of 2 of 36 selected PR–migration pairs; a GitHub HTTP
403 access failure terminated API collection. `results/issue_event_sampling_audit.json`
identifies exactly which were obtained and which remain unobserved. Retain
these missingness markers; do not recode missing requests as absent.

## Paper components

- `results/PAPER_EXPERIMENTS_EN.md`: FSE-style evidence, method, results,
  interpretation, limitations and primary-source links.
- `results/EXPERIMENT_REPORT_CN.md`: Chinese result digest.
- `results/TABLES_FOR_PAPER.md`: four derived tables.
- `results/figures/fig_m1`–`fig_m4`: scientific figures in SVG and PNG.
- `results/measurement_metrics.json`: aggregate outcomes and proxy sensitivity.
- `results/per_pr_observability_and_witnesses.json`: PR-level evidence and
  observationally equivalent world candidates.
- `results/robustness.json`: prespecified-style and exploratory robustness
  distinguished in field names, including 103-PR dedup.
- `results/synthetic_bounds_validation.json`: seeded exhaustive checks.
- `results/VERIFICATION_AUDIT.json`: offline structural checks, including
  a digest for every downloaded Issue Events normalized record.

## Integrity and submission scope

Before interpreting any count, inspect `../results/FINAL_SUBMISSION_GATE_AUDIT.json`.
The original recommendation-accuracy experiment **did not** meet its +10 pp
independent-expert gate; that negative result must not be erased by the pivot.
The new paper's claim is an **identifiability finding**, not an intervention
claim. Reviewers may still require a wider independent organizational sample,
complete source cross-validation, expert-interview triangulation, or evidence
of direct industry adoption. Those are genuinely uncompleted; none is silently
replaced by a simulated person or a model-written expert rating.

The API check, per-event curation and non-blind code-substance annotations are
exploratory. We must not retroactively call them preregistered confirmation.
The fixed API selection was made before the particular Issue Events responses
were harvested, **not** before the original research cohort and models were
constructed. The actual result remains vulnerable to selection and process
confounding; no organization population parameter is estimated.
