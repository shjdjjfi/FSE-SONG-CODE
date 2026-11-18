# Manuscript-ready empirical results (English, with explicit limitations)

**Research line:** *Recovering Flaky Test History Across Test Identity Changes* (N04, the third topic **in the supplied ordered list**). This is a factual results draft, **not** a claim that the initially proposed technique or a full FSE Industry submission has been validated. All numeric results can be independently checked by `python3 src/verify_frozen.py`.

## Experimental questions

**RQ1: Identity linkage.** How often can several training-free methods correctly link an old test to a converted test within a real multi-test commit, at bounded risk of incorrectly transferring history?

**RQ2: Tool mechanics.** How do changes to pytest node identifiers affect last-failed selection in different pytest releases, and when can a conservative mapping of the cache restore the intended target?

**RQ3: Potential decision loss.** How many future flaky observations would be overlooked in a specified reset-versus-preserve *counterfactual* applied to authentic 30-fold test execution sequences?

**RQ4: Executable real-world transition.** Can the lineage of individual test instances be recovered and audited for a genuine developer-authored Java parametrization, and can the tests actually be executed on both historical revisions?

## Protocol and data provenance

We froze the public TestMigrationsInPy repository at commit `d29ae2370ee5d7ef81e78421c1f1d7f7b753c04c`. We parsed 875 unique, single-test before/after pairs across 13 repositories and 108 commits, excluding 55 non-single-test snippets and two duplicate-identity pairs. Because 33 remaining pairs lacked a same-commit competitor, the primary *candidate-selection* benchmark contained 842 real paired conversions per seed. Three seeds (17, 29, 43) sampled same-commit decoys, producing 2,526 method-query observations per arm; this multiplication should not be treated as independent repositories or commits. Every query had a real target-present variant and a constructed target-absent variant with its correct candidate removed.

Methods were thresholded using leave-one-project-out calibration on the other projects. The calibration target was 2% false transfers; it is an empirical constraint, not a held-out guarantee. Correct recovery was measured on target-present queries. Wrong transfer was counted when a target-present query selected the wrong candidate or a target-absent query selected any candidate, divided by the total number of present and absent queries. The eight arms were exact node ID, method name, file+method, source similarity, a proposed semantic anchor, two ablations, and a clearly labeled exploratory post-hoc hybrid. We used project-cluster bootstrap confidence intervals, not a naive independent-test resampling.

For historical execution outcomes, we used Wendler and Winter's FTW 2024 open repeated-results data (Zenodo DOI `10.5281/zenodo.10639030`), with attribution under the included CC BY 4.0 license. We parsed 330 files and 4,654,230 execution rows over eight projects. Of 149,110 distinct test-by-commit keys, 148,211 supplied complete, non-skipped 30-fold repetition sequences: 126,619 always passed, 20,551 always failed, and 1,041 exhibited pass/fail flakiness across repeats. We did not fabricate any test outcomes or assume the public dataset recorded quarantine actions.

## RQ1. Identity linkage on real converted tests

| Approach | Correct recovery (%) | Wrong transfer (%) | Interpretation |
|---|---:|---:|---|
| Exact node ID | 30.76 | 0.00 | Conservative, substantial loss |
| **Method name** | **96.44** | **0.71** | Strongest simple baseline |
| File + method | 95.72 | 0.71 | Strong baseline |
| Source similarity | 51.86 | 3.35 | Greater than 2% risk |
| **Semantic anchor (candidate)** | **49.01** | **3.19** | Fails the criterion |
| No assertions | 64.77 | 2.14 | Ablation |
| No call context | 43.67 | 2.75 | Ablation |
| Hybrid (post-hoc) | 95.72 | 1.19 | Exploratory, not confirmatory |

The proposed semantic anchor **underperformed** name matching by **47.43 percentage points** in correct linkage; the 13-project cluster-bootstrap 95% confidence interval for *anchor minus method name* was [−69.48, −27.37] pp. In particular, a baseline recovering 96.44% of targets admits a maximum additional recovery of 3.56 pp even for an oracle, making the original target of a 15 pp gain over the strongest baseline impossible *on this sample*. The proposed candidate also exceeded the 2% observed wrong-transfer threshold. This is an important negative finding, not an algorithmic success.

There is a small promising niche: of 875 usable source transitions, 25 changed the test method's name, and just **20 of these were present in the main candidate benchmark** (three projects). Within that subset, semantic anchors recovered 50% versus 0% for a name-only baseline, albeit using just 20 unique events. This subgroup was examined after the overall analysis, lacks broad project coverage, and is not a defensible confirmatory industrial gain. Stratified results for class moves, file moves, and rename cases are included as CSV. Sensitivity checks with maximum candidate counts four and twenty did not change the name baseline's 96.44% recovery and 0.71% wrong-transfer rate.

## RQ2. Actual pytest last-failed cache behavior

Across pytest 7.4.4, 8.4.2, and 9.0.1, we executed real pytest processes using controlled code edits and `--lf --lfnf none --collect-only`. A renamed test, moved file, or parameter ID change each caused the last-failed selection to expand from **one target before modification to three selected tests after the edit**; a strict prototype using AST body equality and unambiguous parameter position restored selection to **one**. For a semantic assertion change and a one-to-many split, the bridge declined to copy the former failure and left **zero** selected tests after intervention. Under the same empty-cache option, all five scenarios collected zero tests.

These are real pytest command-line measurements, but all fixtures and the initial failing assertions were authored for this mechanism test; they are **not** samples of naturally occurring flaky test events. We make no throughput, quarantine, or industrial cost claim from this experiment.

## RQ3. Replaying authentic 30-fold outcomes under hypothetical history resets

For each complete 30-fold outcome series, we permuted its observed outcomes with one of three fixed seeds and considered early outcomes as a history and later outcomes as a prospective ten-run segment. We applied two analysis-only history policies: preserve the earlier observations, or reset the identity and retain only the recent five. Both policies used the *same actual run outcomes*.

| Outcome permutation seed | Future flaky cases | Missed with full history | Missed after simulated reset |
|---:|---:|---:|---:|
| 17 | 521 | 202 | 347 |
| 29 | 533 | 210 | 377 |
| 43 | 536 | 217 | 355 |

The project-cluster bootstrap estimate of the increase in missed future-flaky cases attributable **within this counterfactual** to resetting rather than preserving the constructed past was **28.30 pp (95% CI [10.14, 31.40] pp)**, using eight project clusters. In a separate intentionally erroneous-link counterfactual, carrying a known flaky status to a stable target generated between 807 and 815 false quarantines among 1,038 *constructed* negative links, per seed. These figures characterize possible decision consequences **conditional on a particular identity intervention**, not the observed frequency of industrial renames, actual CI quarantine decisions, or the empirical error rate of our linker.

## RQ4. Genuine source revision and genuine pre/post JUnit execution

We checked out the actual Java-WebSocket parent and child of commit `2ce6e6149d0ef44f4919e75326265c64c144a00f`, a November 2018 parametrization change. In two test classes, 40 numbered test methods became four parameterized methods with ten instances each. We created a source-only deterministic lineage rule based on method helper calls and parameter values, without using labeled IDoFT identities for the inference step. It linked **40/40** individual old methods, and then agreed with **27/27** separately annotated IDoFT moved/renamed records. Only **one** repository and **one** developer commit were evaluated by this rule; the value 40/40 should never be presented as an external accuracy estimate.

Both original Git revisions compiled using Temurin JDK 8 to support the old Java 6 language level and were actually executed under the same Java 21/Maven 3.9.11/Surefire 3.2.5 host setup. We ran the target 40 JUnit instances **30 times per revision**, yielding 1,200 observed executions before and 1,200 after. Before the change, eleven instances of execution reported failure/error and five distinct test cases were flaky over their thirty repeats. After the change, six executions reported failure/error and six cases were flaky. Three case pairs were flaky on both revisions, two only before, and three only after.

We also joined the 27 independently annotated old IDs with authentic FTW execution history: 2,020 observed test-by-commit snapshots, of which 102 contained a mix of pass and fail across thirty repeats. The post-revision results came from our own local re-execution, **not** from a corresponding historical FTW post-refactor trace. The apparent eleven-to-six outcome difference is descriptive; there was no randomized treatment, control for shared socket-service scheduling, or observed actual quarantine transfer, so it is not a causal reduction.

## Threats to validity and implications

**External validity.** Only thirteen Python projects form the main candidate benchmark, with twenty true name changes in the competitive subset and a single Java parametrization commit. The Python dataset catalogs unittest-to-pytest *framework migration* and is enriched for preserving original test names; its strong name baseline could be an artifact of the event selection. Other forms of refactoring are underrepresented.

**Construct validity.** A curated before/after snippet pair is not equivalent to a logged CI test identity. Removing the true target to create a negative query does not establish a real deletion or semantic replacement. Semantic-change and split negative controls are authored, not historical. A pass/fail mixture in thirty repeated runs is an operational definition of flakiness rather than evidence of root cause.

**Causal validity.** The FTW run outcomes are genuine but reset/preserve decisions are hypothetical. The pre/post JUnit suites on different Git revisions may have different behavior for many reasons, and thirty repeated local runs do not establish the change's causal effect. No genuine quarantine action was recovered.

**Statistical validity.** Multiple candidates from the same commit, repeated random seeds, and the same projects create dependence. We use project-cluster confidence intervals and show per-project data, but only eight clusters are available for the outcome replay. Subgroups and the post-hoc hybrid were not preregistered. The risk budget was tuned on other projects, not controlled with a formal held-out risk guarantee.

**Novelty.** IDoFT's existing README already describes identifying moved/renamed tests by method-body equivalence. Therefore, body fingerprints or AST matching alone should not be claimed as new without a more precise and independently evaluated contribution.

**Paper outcome.** The executed experiments establish an important mechanism and negative primary benchmarking outcome. They do **not** meet the original proposal's 15 pp / ≤2% success threshold, nor the independent CI-quarantine evidence needed for an honest FSE Industry empirical-benefit claim. The project should either acquire external deployment traces and redesign its scope or report a narrower replication/negative result with explicit limitations.
