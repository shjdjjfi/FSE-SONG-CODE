# Experimental section draft (extended pilot, **not** an FSE Industry Track-ready claims section)

**Working title:** Recovering Flaky Test History Across Test Identity Changes

The following text and tables describe only experiments actually performed. An updated public case study now links a real file-level quarantine decision to a test split, and an independent refactoring oracle supplies verified Java source-level successor labels. However, there is still no multi-project, causally identified production outcome for an N04 implementation, nor a validated ≤2% unsafe inheritance bound. These limitations preclude a claim of demonstrated industrial benefit. See `ADDENDUM_20261115_ZH.md` for the complete update.

## Experimental questions

We investigate four questions: (RQ1) how test-identity changes disrupt exact-ID history retrieval; (RQ2) whether structural/semantic guards improve test-lineage candidate quality; (RQ3) whether parameterization-aware mapping separates runtime instances from method-level groups; and (RQ4) whether these candidate links demonstrably improve observed quarantine decisions and resource consumption in real CI. The available evidence supports exploratory analyses of RQ1–RQ3 and **one real case of narrower file-level quarantine**, but **does not causally answer RQ4** for N04 deployment.

We prespecified a practical success condition in the screened idea: at false inheritance ≤2%, recovery of independently established histories must improve by ≥15 percentage points compared with the strongest appropriate baseline. We report failure to substantiate that criterion.

## Datasets and reproducibility

**Repeated historical test execution.** The FTW release (Zenodo record 10639030) contains results from repeated executions of historical source revisions. We parsed 330 compressed CSV segments, 11 histories from eight source repositories, and 4,654,230 test-status observations. Source revisions are sorted by Git ancestry; replay execution timestamps cannot establish the historical order of source commits. Tracks from the same repository are not independent projects. Source-controlled source-diff audit provides six identity-boundary cases from three unique transition commits in two repositories, of which three are transferable and three call for abstention (two deletions, one ambiguous split).

**Public migration statuses.** We used the IDoFT `MovedOrRenamed` and `Deleted` status annotations, pinned to Git SHA `4903dc9233eead4e4191c66f9ed0b14eea091052`. We resolved test-changing revisions cited by the annotations and parsed test methods in the before/after source versions. The resulting convenience sample comprises 74 old-test cases from 15 events in seven repositories: 34 positive examples with a unique source-derived successor target, 27 positive records that collapse into parameterized method groups, nine `Deleted` labels, and four positive examples without a reliable successor FQN. **This is not an independently annotated successor-FQN benchmark.** We retain source-derived targets and original status labels in separate fields, and record detected-vs-parent source SHA discrepancies.

**Real CI failure candidates.** Independent GitHub Actions failure-candidate records in the Test Flare repository contain 62 deduplicated run-attempts from Prefect and Home Assistant, 212 test IDs across the two projects, and four test IDs with mixed pass/fail results in local reproduction. This is evidence of real CI failures, but **this particular dataset** does not expose full passing-test histories or quarantine actions and cannot label the relevant old-to-new decision outcomes. Our later Fusion case does contain a linked quarantine migration, but not a replicated method-level industrial experiment.

**Reproduction environment.** All experiments used CPUs. The Python toolchain included pytest 8.4.2, Tree-sitter 0.25.2, Tree-sitter Java 0.23.5, NumPy 2.3.5, SciPy 1.17.0, and Matplotlib 3.10.8. The Java test replay used a local JDK 21 and Maven 3.9.11 with explicit temporary compiler-target and unrelated JDK-removed CORBA-suite compatibility adaptations. Source snapshots, candidate decisions, runner outputs, and all predictions are released in machine-readable JSON in this bundle.

## Baselines and quantitative comparison

We compare exact test ID; Git path change plus unchanged test method; name similarity; normalized exact body; method name and source context; a conservative lineage heuristic with unique candidate/one-to-many guards; and ablations without body or group checks. The conservative strategy refuses a single-new-method link shared by several old method IDs, because method-level identity does not imply instance-level quarantine identity. Similarity thresholds were exploratory and are **not** claimed to have been frozen on an independent tuning split.

| Method | Unique source-derived positive links (n=34) | Transfer on original deleted labels (n=9) | Unjustified method-to-instance links in parameterized groups (n=27) |
|---|---:|---:|---:|
| Exact node ID | 0 | 0 | 0 |
| Git path + same method | 14 | 4 | 0 |
| Name similarity | 33 | 8 | 27 |
| Exact body fingerprint | 11 | 2 | 27 |
| Name and context | 25 | 4 | 0 |
| Guarded lineage | **26** | **4** | **0** |
| Remove body guard | 33 | 8 | 27 |
| Remove group guard | 26 | 4 | 27 |

The guarded strategy recovers 26/34 (76.5%) candidate links versus 14/34 (41.2%) for Git-path/same-method, a paired difference of +35.3 percentage points (migration-event bootstrap 95% interval: +10.8 to +66.7 points; seven event clusters with evaluable positive instances, seeds 17/29/43, 3,000 draws per seed). However, the stronger name-and-context baseline recovers 25/34 (73.5%) at the same original-Deleted transfer rate, so the difference is only +2.9 percentage points (event-bootstrap interval: 0 to +14.3 points). The raw `Deleted` error is 4/9 for guarded lineage. Neither pair demonstrates the prespecified gain at ≤2% false inheritance.

### Label disagreement and safety bounds

Four of the nine original `Deleted` labels conflict with strong source-level evidence of a method retaining the same name and normalized implementation while its Java class file moves. **The new independent Git audit also finds R94–R98 test-file rename evidence for all four rows in one Riptide maintainer commit.** This does not justify unilaterally overwriting the original labels: fixture semantics or execution context can differ. On all nine original labels, the guarded false-inheritance rate is 4/9 (44.4%; exact binomial 95% interval 13.7–78.8%). On the five nonconflicting labels, it is 0/5, for which the exact 95% upper bound is 52.2%. The latter is not evidence of safety at a 2% level; event clustering further limits statistical precision. Approximately 183 independent zero-error negative examples would be required merely for a two-sided exact 95% upper bound below 2%, with more needed under meaningful clustering.

### Natural source-diff controls

For the six manually source-audited examples, a normalized body fingerprint and the guarded strategy each identify all three source-confirmed transferable candidates and abstain on all three known nontransferable or ambiguous cases. Name similarity successfully maps two transferable candidates but transfers on all three negative cases. The result validates a local conservative mechanism, not an incremental advantage over a simple body hash or a general deployment performance claim.

## Independently verified source successors and end-to-end discovery

Using RefactoringMiner's independent human-validated oracle, we extracted 142 candidate Java test-method refactoring edges from 22 projects and 30 commits: 81 validated refactoring true positives (TP) and 61 refactoring-detection false positives (FP). We obtained before/after source for four projects absent from the original IDoFT study: Apache Cassandra, Checkstyle, Closure Compiler, and Infinispan. They cover 105 source-inspectable proposals (54 TP, 51 FP).

The new experiment does **not** provide the successor FQN to the algorithm: it enumerates test methods in changed Java files, applies fixed name/body/context guards, and compares only the final prediction with the oracle. Exact ID recovers 0/54 TP refactoring edges; the strongest simple name-only baseline recovers **39/54 (72.22%)**; exact body recovers 17/54 (31.48%); and guarded lineage recovers **40/54 (74.07%)**. The guarded-over-name gain is only **+1.85 percentage points**, with descriptive event-bootstrap 95% interval **[0, +6.52 pp]** (six positive commit clusters) and project-bootstrap interval **[0, +4.35 pp]** (four project clusters). These 54 edges represent 53 distinct old test IDs: one Checkstyle old method has two independently confirmed new destinations and is correctly left unresolved by a single-target method. Among 52 unique-target old IDs, guarded recovers 40 and name-only 39.

Crucially, a RefactoringMiner `FP` means a proposed *method refactoring* was rejected; it is **not** an independently adjudicated negative logical-test-identity or quarantine-transfer label. A class relocation may preserve test behavior even when a particular Move Method inference is marked FP. The 51 FP rows **cannot be treated as false quarantine inheritance**. This independent benchmark improves source-label provenance, but neither establishes ≥15 percentage points of gain over the strongest simple baseline nor addresses runtime quarantine safety.

## Real quarantine migration and observed CI metadata

We reconstructed the public, source-controlled quarantine ledger of `Runfusion/Fusion`, obtaining **145 parseable historical revisions**, **264 observed add decisions**, **261 removals with unresolved cause**, **215 distinct identifiers ever added**, and **104 additions with linked GitHub Actions run URLs**. Two historical JSON versions were unparsable and are recorded. The independent `trycua/cua` ledger included three additions but no linked rename. Neither a removed ledger entry nor a changed quarantine ID necessarily constitutes a test rescue.

One Fusion commit (`b5450832494d24e4171acea606b4c022a5a8475b`) provided a uniquely matched real identity-changing quarantine decision. A flaky dist-barrel test was extracted from `extension.test.ts` into `extension-dist-barrel.test.ts`. Before the commit, the parent test file was listed as quarantined and excluded from the Vitest default lane; after the commit, only the new file remained excluded, while the old file was readmitted. Both old and new ledger reasons cited the same real failing Actions run #28697507894. The moved test retained its title and 13 matching assertion-source lines. Static source counts were 155 `it` declarations before, followed by 154 in the restored parent and one in the new file. The maintainer reported that approximately 68 stable tests had been collaterally excluded by the former file-level policy; this is a maintainer assertion, not an independently executed test count.

We retrieved public Actions workflow and job metadata. The linked pre-migration `Full Suite (non-blocking)` run #28697507894 took **522 seconds** with **1,609 seconds** of summed job elapsed times. A follow-up `Full Suite (non-blocking)` run #28720367126, whose source revision descends from the split, took **529 seconds** with **1,706 seconds** of summed job time. **Both failed** and include other source differences and failure causes. We did not obtain complete test-by-test logs, an equivalent rerun inventory, billing data, or a controlled N04-versus-baseline deployment. This evidence confirms a real *quarantine identifier transfer and narrower exclusion policy*, **not a measured or causal CI-cost improvement**.

## Actual test execution after a parameterization refactor

We reran both `Issue256Test` and `Issue580Test` in `TooTallNate/Java-WebSocket` at the parent of Git commit `2ce6e6149d0ef44f4919e75326265c64c144a00f` and at that commit, with three local repetitions of each test class per revision. The real test runners emitted 120 pre-change testcase outcomes (all passing) and 120 post-change outcomes (119 passing, one skipped). The test class code was not rewritten; build-only compatibility settings and exclusions for unrelated suites were disclosed.

Twenty-seven named old test instances identified in IDoFT can be paired to 27 *unique candidate* new JUnit runtime instances by source behavior family and the integer runtime parameter index. For example, `runReconnectScenario3` is a candidate predecessor of `runReconnectSocketClose[3]`; `runReconnectBlockingScenario3` is distinct from that family. Exact runtime node ID retains none of these 27 links. A method-only link without the parameter is an ambiguous group merge for all 27, whereas the source+parameter rule generates 27 unique candidate instance links. **These are not independent maintainer-certified labels**; all observed tests passed or skipped, and the run contains no inherited flaky failures or observed quarantine decisions. We therefore do not interpret 27/27 as validated lineage precision, flake prediction accuracy, or saved CI cost.

## Pytest lastfailed mechanism and policy feasibility

Using actual pytest 8.4.2, we create three isolated three-test fixtures containing one failing test and a persistent `lastfailed` cache. Each trial yields one selected test when the cached node remains resolvable; after renaming that test, the stale cache causes three tests to be collected; explicitly migrating the cached ID restores selection to one test. This reproduces selection behavior only; it does not measure field deployment impact.

A prespecified *hypothetical*, not production, quarantine policy would suggest isolation whenever the observed previous five source revisions exhibit at least 5% failed test outcomes. Across six source-confirmed boundaries, no old method has an observed pre-boundary mixed pass/fail signal; there are zero policy decision differences between exact-ID and inherited-history replay. The source does not log actual maintainer quarantine decisions. The correct inference is lack of identifiable treatment-effect evidence, not a claim of zero cost benefit.

## Threats to validity and decision

The main threats are (i) source-dependent target label leakage **in the original IDoFT benchmark** (mitigated by the new third-party refactoring benchmark), (ii) nonrandom Git-annotated sample construction, (iii) clustered group events, (iv) very few positive source migration commits even in the new four-project holdout, (v) source-equivalent method bodies but potentially different runtime fixtures, (vi) post hoc local builds that differ from historical CI, and (vii) only one real quarantine-linked split without a causal economic outcome. The initial IDoFT holdout had four records with no independently confirmed new targets; the new external sample remedies the existence of source-confirmed targets but yields only +1/54 recovery versus a strong name-based baseline.

The prespecified risk/benefit criterion is not met. The results can support a transparent pilot, a reproducer for `lastfailed` behavior, a real quarantine-split case study, an independent source-refactoring benchmark, and a measurement framework, but **not** the general claim that N04 improves an industrial quarantine policy. Before submission, further research would need independent negative *test-identity* labels, linked pre/post CI and quarantine records from multiple production projects, and a risk-calibrated comparison against the strongest baselines under project- and time-based holdouts.

## Suggested figure references

- `figures/lineage_tradeoff.pdf`: IDoFT source-derived recall and raw/filtered negative-label transfer.
- `figures/junit_parameter_instance_recovery.pdf`: real Java refactor runtime candidate ID pairs and ambiguous grouping.
- `figures/ftw_source_coverage.pdf`: offline test replay observations and observed flakiness by track.
- `figures/pytest_cache_mechanism.pdf`: real pytest cache mechanism in controlled fixtures.
- `figures/independent_holdout_recall.pdf`: independently oracle-verified source successor recall across four unseen repositories, including the strongest simple baseline.
- `figures/fusion_quarantine_split.pdf`: real Fusion before/after file-level quarantine identity transfer, with explicit causality caveat.
