# N24: Evidence-Based Repair of Cross-Platform npm Lockfiles

**FSE 2027 Industry Track — reproducible experiment report**  
Evidence date: 18 November 2026 (UTC).  
Code: [`n24-fse-benchmark`](https://github.com/shjdjjfi/FSE-EXP-1/tree/n24-fse-benchmark).  
Hosted workflow: [run 44245392156](https://github.com/shjdjjfi/FSE-EXP-1/actions/runs/44245392156).

## Decision up front

The original N24 algorithm-superiority claim **does not survive a current strong baseline**. On all five controlled package families, **npm 12.2.3 in-place** and a conservative targeted donor repair both restore complete platform-variant coverage without changing any unrelated locked versions. The same equivalence is observed for the original committed Ollama JS lock on Linux. In contrast, npm 11.4.2 does not repair those locks in place, and full regeneration can change unrelated versions. The credible contribution is an **empirical taxonomy of failure modes, discriminating tests, and repair trade-offs**, not a newly invented general-purpose npm repair algorithm.

## Sources, units, and provenance

| Component | Scope | Independent observation | Evidence classification |
|---|---|---|---|
| Earlier supplied B0001 | 3 families, 3 arms, seeds 17/29/43 | Prior pilot, seeds not new projects | Exploratory; excluded from confirmatory denominators |
| Controlled npm-generated defects | Rollup 4.18.1, esbuild 0.25.2, Biome 1.9.4, SWC 1.10.14, Lightning CSS 1.29.3 | Family × actual runner OS × fault condition | Published real packages; triggered defect, **not natural CI** |
| Frozen GitHub audit | 17 unique repositories; 39 target parent-package instances | Repository with an immutable source commit | Convenience sample of public committed locks |
| Retrospective project replay | Cloudreve frontend, Google clasp, Ollama JS | 3 original committed manifests/locks × 3 runner OSs × 5 strategies; 9 unique project–host units and 15 native parent–host units | Genuine lockfile data, **today's replay**, not original CI logs |
| Guardrail tests | 11 separate deterministic tests | Different repair and aggregation invariants | Synthetic safety/negative-control tests |

All npm test installations use `--ignore-scripts --no-audit --no-fund`. The pinned npm implementations are 10.9.2 (bug generation), 11.4.2 (historical comparator), and 12.2.3 (registry-latest strong baseline). Node.js 24 is used for the current replays. In particular, `npm ci` exit code 0 is **not** conflated with successful execution of an optional native binary.

### Methods and outcomes

For each controlled package, a fresh lock is generated from the registry. npm 10.9.2 then performs the known defective sequence: install packages, retain `node_modules`, remove only `package-lock.json`, and regenerate the lock. We compare **unmodified**, **npm11-in-place**, **npm12-in-place**, **strict-donor**, and **clean-regenerate**. The clean/intact lock is included as an independent negative control. The donor consists of a separate exact-version parent lock; the repair adds only optional leaves with version, integrity, OS and CPU metadata, and refuses ambiguous/non-leaf cases.

Define **version churn** as the count of non-target lockfile package paths for which the original and result both carry *different pinned versions*. Newly added or removed non-target paths are separately recorded rather than silently folded into version churn. Portable coverage counts the declared platform variants represented in `packages`. The definitive functional outcome is a native build/transform/CLI call actually executed on the host OS. All method comparisons are paired within the same source, project, and operating system.

## RQ1 — Is the npm10 regeneration defect reproducible?

**Yes in all five controlled package families on Linux x64**, including a real hosted Ubuntu runner. Before repair, one current-host platform variant remains per parent, compared with 8–25 variants in independently generated complete locks. Cross-platform failure requires **transferring the broken Linux lock to another host**: the producer's own Linux binary usually remains installable. Never treat the missing foreign-platform entries alone as proof of a Linux runtime failure. The three-host controlled experiment covers 150 observations: 5 families × 3 hosts × 2 lock conditions × 5 strategies.

| Family | npm10 warm regenerated | Complete/donor reference | npm11.4.2 in place | npm12.2.3 in place | Strict donor |
|---|---:|---:|---:|---:|---:|
| Rollup | 1 | 16 | 1 | 16 | 16 |
| esbuild | 1 | 25 | 1 | 25 | 25 |
| Biome | 1 | 8 | 1 | 8 | 8 |
| SWC | 1 | 10 | 1 | 10 | 10 |
| Lightning CSS | 1 | 10 | 1 | 10 | 10 |

All five strict-donor and npm12 modifications preserve the non-target pinned version map (**0 changed versions in all 5**). Clean regeneration repairs coverage but changes exactly **1 unrelated pinned version in each** under the preregistered widening of an otherwise frozen `picocolors` constraint. The intact-lock controls show that both in-place methods and strict-donor make zero lock entries changes when nothing is missing; full regeneration still changes one unrelated version per controlled example.

## RQ2 — Are the gaps present in genuine public project lockfiles?

The frozen convenience sample contains **17/17 successfully parsed public repositories**, including **39 platform-parent instances**. Five instances across three repositories lack **59 declared variant references** from every `packages` entry:

| Repository and immutable commit | Missing declared variants | Affected parent packages |
|---|---:|---|
| [cloudreve/frontend `c7b6fa52`](https://github.com/cloudreve/frontend/tree/c7b6fa5288ed0490a5589ddff4f56ea1f96a5315) | 43 | Rollup, esbuild, SWC |
| [google/clasp `e9441e57`](https://github.com/google/clasp/tree/e9441e57b0ae398fdb8524dada9372c1ed8590e0) | 7 | Biome |
| [ollama/ollama-js `c276d078`](https://github.com/ollama/ollama-js/tree/c276d078eee37a0df003b9ee2120ec70327f32e9) | 9 | SWC |

This is a **non-random, search-discovered sample**. These figures describe observable structural gaps in the selected locks; they are *not* an estimate of how often all npm projects fail. Some existing entries have incomplete metadata and are tracked separately; the count 59 reflects entirely absent declared paths.

## RQ3 — Can these real locks cause observable failures today?

The original Ollama JS commit was replayed with its **unaltered `package.json` and `package-lock.json`** on hosted Linux. The original and npm11-modified locks each permit a successful `npm ci` but the actual `@swc/core.transformSync` fails with **`Error: Bindings not found`**. Npm12 and strict-donor restore the native SWC transform, without collateral version changes. Full regeneration also restores it but changes **176** non-target versions.

| Ollama JS (Linux replay) | `npm ci` | Native SWC transform | Non-target version churn |
|---|---|---|---:|
| Unmodified committed lock | Pass | Fail | 0 |
| npm11-in-place | Pass | Fail | 0 |
| npm12-in-place | Pass | Pass | 0 |
| Strict-donor | Pass | Pass | 0 |
| Clean regeneration | Pass | Pass | 176 |

For Cloudreve, the committed lockfile exhibits **both missing platform variants and broader dependency/peer inconsistencies**. The unmodified lock and strict-donor repair cannot complete `npm ci`, even after a separately recorded `--legacy-peer-deps` retry. Npm11 in-place updates **87** non-target pinned versions, makes Rollup and esbuild execute, but SWC remains broken on Linux; npm12 in place updates the same **87** versions and restores all three; full regeneration updates **135** versions and restores all three. The strict-donor failure is a **correctly identified boundary** of leaf-only repair, not evidence that it damages existing lock records.

Google clasp is a negative control for the distinction between a structural gap and a demonstrated failure: its Biome lock lacks seven foreign-platform variants, but the Linux original already has a working native CLI. Do not count that structural defect as a Linux application failure.

## RQ4 — Actual cross-platform verification

The [completed GitHub-hosted workflow (run 44245392156)](https://github.com/shjdjjfi/FSE-EXP-1/actions/runs/44245392156) produced npm10 locks on Ubuntu 22.04 x64 and transferred those *same lock bytes* to Windows 2022 x64 and macOS 15 arm64. Its four jobs (Linux, Windows, macOS, aggregation) all passed. The per-run `runs.json` artifacts, **not merely job success**, yield the following results on the **defective** condition. Each denominator is five families per host; every controlled `npm ci` exits successfully, including cases in which the native loader fails.

| Actual host | Original/native pass | npm11/native pass | npm12/native pass | Strict donor/native pass | Clean regen/native pass |
|---|---:|---:|---:|---:|---:|
| Ubuntu 22.04, Linux x64 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| Windows 2022, x64 | 0/5 | 0/5 | 5/5 | 5/5 | 5/5 |
| macOS 15, ARM64 | 0/5 | 0/5 | 5/5 | 5/5 | 5/5 |
| **Pooled (descriptive)** | **5/15** | **5/15** | **15/15** | **15/15** | **15/15** |

Across all 15 defective family–host pairs, npm12 and strict donor have **zero non-target version changes**, whereas clean regeneration changes **15** unrelated pinned versions in total. All 75 intact-condition native executions succeed; npm11, npm12, and strict donor leave those intact locks unchanged, while clean regeneration still changes 15 pinned versions. These are repeated test cases of **five package families**, not 150 independent software projects, and should never be analyzed as 150 independent industrial samples.

### Genuine historical locks on three hosts

The same hosted run also replayed the *original committed* manifests and locks from the three repositories in RQ2 on all three real hosts, with original failure logs and each strategy's treatment/`npm ci` log retained. The complete data comprise **45 project–host–strategy runs** (3 projects × 3 hosts × 5 strategies). Some projects have several native parents, so there are **75 parent–host–strategy native checks**; the stronger observational unit for project-level pass/fail and version churn is the **9 unique project–host lockfiles**, not each parent separately.

| Treatment | Projects with all audited native parents usable (of 9 project–host units) | Individual native parents usable (of 15 parent–host units) | Non-target pinned-version changes, counted once per project–host lock |
|---|---:|---:|---:|
| Original lock | 2/9 | 2/15 | 0 |
| npm11-in-place | 3/9 | 9/15 | 261 |
| npm12-in-place | **9/9** | **15/15** | 261 |
| Strict donor | 6/9 | 6/15 | 0 |
| Clean regeneration | **9/9** | **15/15** | 1,113 |

The historical outcome is not simply a controlled-case replay. In Cloudreve, npm12 changes **87 unrelated pinned versions per host**, and strict donor cannot resolve the inconsistent package graph; in Clasp and Ollama, npm12 recovers native loaders without changing unrelated versions. These different costs preclude any honest claim of universal zero-churn recovery. Cloudreve and the clean regeneration of other projects can require a separately identified `npm ci --legacy-peer-deps` retry; those results are **not** default `npm ci` successes. For the intact original Ollama lock on macOS, the SWC loader already succeeds: this illustrates a concrete **platform-dependent** failure, not a universal defect in every host environment.

The first hosted historical summary mistakenly counted a Cloudreve lockfile's 87 changed versions **once for each of its three native parent packages**. The checked-in `analyze_history.py` correction and regression test count each unique (source commit, OS, strategy) exactly once. The canonical figures in the table above come from `N24_CORRECTED_HISTORICAL_AGGREGATES.json` recomputed from the unmodified downloaded per-run results, which are preserved in the evidence archive. No original observations were edited. Confidence intervals calculated from repeated parent package checks are not valid estimates of ecosystem-wide effect or prevalence; project-level sample size is only three, with nine correlated project–host replays.

## Practical implications

1. A passing `npm ci` is an insufficient platform-portability oracle when a loader depends on optional native packages.
2. Audit `package-lock.json` platform completeness *before* diagnosing failures; also distinguish missing metadata, broken peer graph, unavailable packages and ignored optional dependencies.
3. First test a current npm in-place lock-only update. Npm 12.2.3 already matches the specialized strict-donor strategy in the controlled cases and the Ollama JS replay.
4. Do not delete the entire lockfile reflexively: an apparently successful fresh install may change many unrelated versions, depending on root constraints.
5. If the original lock violates unrelated dependency constraints (as in Cloudreve), simply restoring platform leaves is not a correct general-purpose recovery mechanism.

## Prior art, threats, and submission readiness

- An *existing Next.js implementation already repairs platform-specific SWC lock entries*: [source](https://github.com/vercel/next.js/blob/canary/packages/next/src/lib/patch-incorrect-lockfile.ts). Do **not** claim targeted leaf repair itself is new.
- npm issue [#4828](https://github.com/npm/cli/issues/4828) and [#7961](https://github.com/npm/cli/issues/7961) document warm-regeneration portability defects; issue [#9342](https://github.com/npm/cli/issues/9342) discusses a distinct proxy-registry/incomplete-metadata failure. Our public-registry experiments do not validate private Azure Artifacts configurations.
- [Gamage et al., 2025](https://arxiv.org/abs/2505.04834) studies the broader design space of lockfiles and provides essential related-work context.
- [StrykerJS #5522](https://github.com/stryker-mutator/stryker-js/issues/5522) reports actual developer workflow disruption and eventual toolchain migration. The publicly scanned Stryker snapshot is not labeled a failure because this experiment did not identify matched CI logs and original failure labels for that exact lock.
- All samples and source versions are public; no private company dependency graph, access, financial costs, or hidden CI incidents were used. Node 24 replays of historical package versions may differ from original historical runtimes. Disabling lifecycle scripts controls security risks but is not a full application test.
- There is no defensible observation of **natural CI incident prevalence, developer labor minutes, monetary savings, or production adoption**. Inventing such figures would invalidate the paper.

The [FSE 2027 Industry Track call](https://conf.researchr.org/track/fse-2027/fse-2027-industry-papers) allows industry-relevant research even without an industrial partner, but still evaluates novelty, rigor, industrial improvement, and lessons learned. It offers **short (5+1 pages)** and **long (10+2 pages)** categories. A short, precisely scoped empirical case-study framing is more credible than a 10-page claimed general repair algorithm given the equivalence to npm12 and the remaining evidence gaps.

## Reproducibility and audit checklist

- [x] Exact releases and tools pinned; source commit SHAs and SHA-256 retained
- [x] Old defect generated by real npm in isolated directories; five published families
- [x] Latest available npm strong baseline included **before** its result was observed
- [x] Intact-lock negative controls and conservative repair refusal tests
- [x] Real Linux x64, Windows x64, and macOS ARM64 native execution; command and stderr evidence captured
- [x] 17-repository immutable source audit; all fetch failures disclosed (none)
- [x] Three real committed-lock projects × three actual hosts; independently failing installation steps retained
- [x] Four GitHub-hosted jobs passed, all eight runner/aggregation artifacts downloaded, per-host outcomes independently recomputed
- [x] Historical per-project version-churn deduplication corrected, with regression test
- [ ] Matched genuine historical CI incident/notification traces and occurrence denominator
- [ ] Independent industrial impact measured from real engineering/production operations

**Bottom line:** the publicly runnable experiments are valuable, but the evidence is a study of **failure modes and remedy boundaries**, not proof of a novel universally better repair method or a completed production ROI study.
