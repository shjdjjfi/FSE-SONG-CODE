# N04 — remaining publication-critical gaps and falsifiable stop/go gates

## Dated update: 2026-11-15 (supersedes the original freeze status below)

The public CI **action evidence** and the cross-repository **local execution**
subtasks are now materially advanced. This does **not** reverse the final
NO-GO verdict for an Industry paper claiming measured deployment savings.
Full details: `EXTENSION_REPORT_2026_11_15_ZH.md` and
`EXTENSION_PAPER_RESULTS_EN.md`.

| Original gate | New verified evidence | Still missing for an Industry *outcome* claim |
|---|---|---|
| STOP-1: no quarantine decisions | 6 merged GitLab MRs + 3 merged Microsoft Aspire PRs; one GitLab quarantine → fix → unquarantine chain; Aspire developers report zero failures across 159/215 runs before release | **Raw per-test CI results after the action** and identity-continuity changes in the same longitudinal stream; no observed causal labor/build savings |
| STOP-2: baseline superiority | Name+body-tiebreak 97.39% vs original name-only 96.44%, both 0.71% false; post-hoc hierarchical case 98.22%, 0.71% false; 293 real annotated rename IDs in separate ICPC 2021 dataset | Headroom makes +15pp **impossible on original benchmark**; +0.83pp vs new best trivial baseline CI95 [0,+5.69]pp touches zero; post-hoc rule selection; direct executable TestRefactoringMiner and future sealed confirmatory projects |
| STOP-3: no independent historical tests | 4 actual Click/MarkupSafe source changes tested pre/post: 80 pytest invocations, 4,990 case outcomes, actual method 1→2 split, module split and same-name changed input semantics; plus 2,400 Java-WebSocket JUnit outcomes | Production **wrong inheritance outcome** never observed; same-name semantic addition does not prove old history is incorrect; broader independently administered systems needed |

The remainder of this document records the original freeze's findings and its
contemporary STOP assessment **before** the dated extension. Do not quote its
"no real quarantine actions" sentence as the state of the updated archive.

**Decision at package freeze: NO-GO for an FSE 2027 Industry Long paper making an industrial-benefit or superior-matcher claim.** The empirical study and real execution audit are delivered; the proposal's original key outcomes are not established. This is a research outcome, not an indication that a failed job was silently omitted.

The initial proposal already instructed: **if independent, actual quarantine decisions cannot be obtained, restrict claims to cache behavior and stop the principal paper claim**. That stop condition is triggered here.

## Critical gaps (ranked by importance)

| Tier | Evidence still missing | Why the current results cannot replace it | Concrete acceptance gate |
|---|---|---|---|
| STOP-1 | Actual CI **quarantine/unquarantine actions**, test execution reports and test identity changes over the same revisions | FTW 2024 provides genuine executed tests but no actual quarantine decisions; all history handoff actions here were simulated | At least two independently maintained public repositories or CI installations with timestamped test identities, changes, actions and subsequent outcomes; independently reproduce action chronology |
| STOP-2 | Primary algorithm outperforms the strongest name baseline at bounded wrong-transfer risk | Current best simple method has **96.44%** recovery with **0.71%** wrong transfer; semantic anchor has **49.01% / 3.19%** | Freeze a new non-leaky, genuinely challenging benchmark *before* algorithm iteration, meet ≤2% false transfers, and show robust paired benefit vs method-name, file+method and other published lineage methods; don't claim +15pp on a 96.44%-covered benchmark |
| STOP-3 | Verified cross-project, cross-time **rename, split, parameterization, deletion and semantic-change** ground truth | Main data contain only 20 method renames in 3 projects; Java case is one commit, target-absent and wrong-inheritance examples are artificial | Independent historical events over several projects and time periods, manually adjudicated ambiguous lineages, blind inter-rater checks, disjoint author/project-time holdouts |
| P1 | Deployment-level industrial cost/utility | Counting missed future flaky outcomes in a counterfactual is not measured CI productivity | Replay decisions on genuine time-ordered build records; report triage time, quarantine-hours, extra reruns, broken builds, false quarantines, and confidence intervals with actionable intervention logs |
| P1 | Robust baseline literature and novel contribution | IDoFT already uses method-body equivalence as a renaming identity precedent; pure fingerprinting is not novel | Formal differentiator from IDoFT, test lineage/tracking work, AST renaming, Git rename detection, flaky-test prediction and automated quarantine products; a separate ablation showing why it matters |
| P1 | Applicability outside older Java parametrization & controlled Python pytest | The successful source rule is tailored to `Issue256Test`/`Issue580Test`; pytest bridge only sees deterministic authored fixtures | At least one other genuine Java rename/parameter ID transition and one actual Python migration with runnable pre/post tests; report build-success selection bias and explicit failures |
| P2 | Long-term reproducibility/deployment integration | Source package re-downloads external Git/Zenodo and requires working Maven deps | Archive content hashes, CI workflow, Docker/runtime manifest and artifact validation in an independent clean environment; no redistribution of unlicensed source snippets |

## Decisions already resolved by experiments

1. **Can cache identity break?** Yes, directly observed on pytest 7.4.4, 8.4.2, 9.0.1.
2. **Can a strict 1:1 mechanism rescue the selected failed test?** Yes, on five controlled edits, while explicitly abstaining for semantic change/split.
3. **Could losing old history matter when outcomes truly fluctuate?** Yes, in a specified *simulated identity reset* over 30 real result repetitions; not proof that any real industrial system experienced the reset.
4. **Is a real Java historical source mapping possible?** Yes, 40/40 from one conversion and 27/27 checked IDoFT labels; only one commit.
5. **Do the originally proposed semantic-anchor results meet the main success criterion?** No; both recovery and false-transfer comparisons fail.
6. **Are “before/after real test runs” absent?** No, now completed: 30×40 tests on each of two actual Java Git revisions, all 2,400 case results retained.
7. **Is there independent real quarantine history?** No. That remains the decisive stop.

## Most defensible research pivots

- **Narrow methods/tool paper:** focus on well-specified pytest last-failed cache migration and an independently validated real-world Python corpus. The existing strict prototype is not sufficient for a strong general methods paper; add package-ready hook integration and actual Python project end-to-end tests.
- **Replication/negative-results study:** quantify how name matching already solves most migrations in the sampled corpus, and when it fails. Need a diverse ground-truth dataset and strong published baselines before claiming a new benchmark contribution.
- **Industry-paper continuation:** obtain legitimately public quarantine action traces or collaborate with a CI vendor/project that can release deidentified, permissioned data, then redesign the identity mechanism and evaluate actionable utility.

## Claims that must not appear as measured findings

- “Flaky/quarantine decisions improved by 28.30pp **in production**.” Only a synthetic reset, using real outcome sequences, produced this difference.
- “Identity matching 100% accurate across industrial Java projects.” The source rule covers 40 cases in a single commit.
- “The method improves recovery by 50pp.” The positive 50% change is a 20-event exploratory method-rename subgroup **against a name baseline that by definition cannot match a changed name**; overall performance is much worse.
- “11 failures became 6 because of our bridge.” Separate builds had 11 and 6 nonpass runs; no randomized intervention/causal effect was measured.
- “CI quarantine savings measured.” No real quarantine action logs were present.

**What to do next**: Treat this package as the completed **measured feasibility and falsification study**. For a defensible FSE Industry submission, first resolve STOP-1 and STOP-2 with independent data; otherwise submit different research claims or choose another of the seven ideas.
