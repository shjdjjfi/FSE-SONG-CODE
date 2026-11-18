# N04: Recovering Flaky Test History Across Test Identity Changes

> **2026-11-15 update:** The archive now also contains a full set of dated
> follow-up experiments addressing the previously listed three STOP gates:
> nine public merged CI quarantine-management changes (two independent projects),
> four real Python pre/post history cases run 10 times each (4,990 actual JUnit
> testcase outcomes), a 293-record independent rename-name stress probe, and
> new risk-controlled simple-baseline comparisons. Read
> **`EXTENSION_REPORT_2026_11_15_ZH.md`** and **`EXTENSION_PAPER_RESULTS_EN.md`**.
> The original pipeline's target **+15pp** remains mathematically unachievable;
> the new post-hoc method's +0.83pp versus a stronger simple baseline is *not*
> independently significant, and original CI test-level post-intervention
> outcomes remain unobserved. **Industrial deployment claim: still NO-GO.**

Reproducibility package for the **third topic in the supplied ordered list**
(N04, *Recovering Flaky Test History Across Test Identity Changes*).

**Research status: not yet defensible as a submission-ready FSE Industry paper.**
The strongest no-GPU baseline on the independently curated Python migration
benchmark already recovers 96.44% of identities at a 0.71% wrong-transfer
rate; the proposed semantic-anchor method performs substantially worse.
An observed real Java refactoring/parametrization case and a runnable bridge
prototype provide mechanism evidence, not independently observed quarantine
deployment gains. See `EXPERIMENT_REPORT_ZH.md` for measured results and
`UNRESOLVED_SUBMISSION_GAPS.md` for an explicit stop/go assessment.

## Contents

- `src/n04_benchmark.py`: independently curated source-code transition labels,
  leave-one-project-out calibration/test, eight arms including ablations, and
  project-cluster bootstrap confidence intervals.
- `src/history_replay.py`: 330 published Maven result-file replays containing
  real executions; ***only*** the identity interventions are counterfactual.
- `src/pytest_behavior.py`, `src/pytest_cache_bridge.py`: actual pytest
  7.4.4/8.4.2/9.0.1 cache behavior on five controlled changes and a strict,
  inspectable bridge prototype. Semantic changes and 1-to-N splits abstain.
- `src/idoft_case_study.py`: IDoFT label audit and the join of 27 labeled
  Java-WebSocket moved tests with authentic historical execution results.
- `src/java_param_lineage.py`: program-derived, source-only numbered-test to
  JUnit parameter identity mapping for one actual 2018 commit; labels used
  **only for verification after inference**.
- `src/run_maven_case.py`, `src/java_before_after.py`: real JUnit pre/post
  checkout replays; pinned build/runtime and per-case traces, not fault injection.
- `src/statistical_analysis.py`, `src/build_figures.py`: detailed evaluation,
  stress-subset tables and paper figure exports (PNG/PDF).
- `tests/`: deterministic pipeline tests with Python standard-library unittest.
- `results/`: frozen output JSON/CSV and sanitized JUnit outcomes.
- `figures/`: figure exports for papers/slides.
- `EXPERIMENT_REPORT_ZH.md`: Chinese, submission-oriented experimental report
  including all RQs, numerical outcomes, confidence intervals and limits.
- `PAPER_RESULTS_EN.md`: cautious English manuscript Results/Threats draft,
  without disguising negative findings as positive results.
- `UNRESOLVED_SUBMISSION_GAPS.md`: critical STOP/GO evidence gates for an
  honest Industry Track submission.
- `RESULT_CHECKSUMS.json`: SHA-256 digests of the 130 frozen code, test,
  figure and measured output files, independently verified on extraction.

### 2026-11-15 reproducibility extension

- `src/ci_event_audit.py`, `src/ci_event_chain.py`: public merged GitLab and
  Microsoft Aspire source quarantine records; one verified quarantine → fix →
  unquarantine timeline. Maintainer run counts are **not** raw CI execution logs.
- `src/cross_repo_real_replay.py`: actual historical `pallets/click` and
  `pallets/markupsafe` Python pytest before/after tests (80 invocations, 4,990
  cases); source AST audit including an actual 1→2 split and semantic extension.
- `src/strong_baseline_extension.py`, `src/hierarchical_history_linker.py`:
  exploratory methods and same-scenario name/body comparisons; project-cluster
  bootstrap, full per-query CSV and risk-weighted costs.
- `src/external_rename_probe.py`: the independent publicly annotated ICPC 2021
  293-method name-only challenge, explicitly *not* source-level CI ground truth.
- `results/real_ci_events/`, `results/cross_repo_pytest/`,
  `results/strong_baselines/`, `results/hierarchical_linker/`,
  `results/icpc2021_rename_probe/`: all new evidence and derived predictions.
- `EXTENSION_REPORT_2026_11_15_ZH.md`, `EXTENSION_PAPER_RESULTS_EN.md`:
  publication-safe RQ analyses and explicit remaining stop/go conditions.

All **151** new and retained source/test/result/figure files are covered by
`RESULT_CHECKSUMS.json`. Re-run `python3 src/verify_frozen.py` and
`python3 -m unittest discover -s tests -v` **without external downloads**.
Third-party Git trees and the CC BY 4.0 source XLSX are excluded from the ZIP.

No third-party source tree, unlicensed `TestMigrationsInPy` snippets, 534 MB
upstream tarball, compiler, Maven repo cache, or JDK binary are redistributed
in this ZIP. The original source versions, URLs and checksums appear in
`DATA_SOURCES_AND_LICENSES.md`.

## Reproduce on a Linux CPU machine

Python 3.12 (stdlib) suffices for the core benchmark and history replay;
`matplotlib` is only required for figures. The pytest experiments use `uv`
with their **explicit pinned pytest versions**. A GPU, paid API and cluster
are unnecessary.

**Run this first to verify all supplied results offline**, without downloading
the original public datasets:

```bash
python3 src/verify_frozen.py
python3 -m unittest discover -s tests -v
```

The independent verifier re-reads primary prediction and outcome CSVs, checks
2,400 real JUnit case outcomes, all 15 pytest mechanism scenarios, both Java
Git source locks, figure availability, and all 130 frozen SHA-256 digests.
This is a frozen release: regenerating results intentionally changes some
runtime/timestamp fields and requires a new checksum manifest.

From the extracted package root:

```bash
mkdir -p data/raw
git clone https://github.com/altinoalvesjunior/TestMigrationsInPy.git data/TestMigrationsInPy
git -C data/TestMigrationsInPy checkout d29ae2370ee5d7ef81e78421c1f1d7f7b753c04c
curl -fL https://raw.githubusercontent.com/TestingResearchIllinois/idoft/4903dc9233eead4e4191c66f9ed0b14eea091052/py-data.csv -o data/raw/idoft_py.csv
curl -fL https://raw.githubusercontent.com/TestingResearchIllinois/idoft/4903dc9233eead4e4191c66f9ed0b14eea091052/pr-data.csv -o data/raw/idoft_maven.csv
curl -fL https://raw.githubusercontent.com/TestingResearchIllinois/idoft/4903dc9233eead4e4191c66f9ed0b14eea091052/gr-data.csv -o data/raw/idoft_gradle.csv
python3 src/n04_benchmark.py --seeds 17 29 43 --max-candidates 12
python3 -m unittest discover -s tests -v
```

**Compare each download's SHA-256 with `DATA_SOURCES_AND_LICENSES.md` before
treating the outputs as a replication**. The archive contains frozen measured
outputs, so re-downloading is not necessary to inspect the findings.

For the 30-fold real outcomes, download the publisher's Zenodo record
`https://doi.org/10.5281/zenodo.10639030`, check its MD5, and extract only
`flaky_histories_dataset/simulated_rt_results` from the top-level tarball:

```bash
tar -xzf data/raw/flaky_histories_dataset.tgz -C data/raw flaky_histories_dataset/simulated_rt_results
python3 src/history_replay.py --seeds 17 29 43
python3 src/idoft_case_study.py
python3 src/statistical_analysis.py
python3 src/build_figures.py
```

For cache mechanics:

```bash
uv run --no-project --with pytest==7.4.4 python src/pytest_behavior.py
uv run --no-project --with pytest==8.4.2 python src/pytest_behavior.py
uv run --no-project --with pytest==9.0.1 python src/pytest_behavior.py
```

For the actual 2018 Java-WebSocket conversion, check out pinned Git commits
`27e26758...` and `2ce6e614...` in `data/javawebsocket_pre` and
`data/javawebsocket_post`. The author-era `pom.xml` requests Java 6 language
level, so compile both with Temurin JDK 8, then run only the two target JUnit
classes using the same Java 21 runtime. Maven 3.9.11 and an ordinary network
route for dependency retrieval were used. An example checkout:

```bash
git clone https://github.com/TooTallNate/Java-WebSocket.git data/javawebsocket_pre
git -C data/javawebsocket_pre checkout 27e26758d6604f5d078709233028bb87b4a39e16
git clone https://github.com/TooTallNate/Java-WebSocket.git data/javawebsocket_post
git -C data/javawebsocket_post checkout 2ce6e6149d0ef44f4919e75326265c64c144a00f
```

Install Maven 3.9.11 and Temurin JDK 8 (see hashes), then invoke the wrapper
once in `test` mode with `--java-home /absolute/path/to/JDK8` for **both**
revisions; the `test` goal also compiles test classes (an actual flaky test may
make the invocation exit nonzero without invalidating successful compilation).
Validate that both `target/test-classes` directories exist. Next ensure
`java -version` resolves to Java 21 for the following `surefire:test` calls.
The explicit Maven path can be supplied with `--maven /path/to/mvn`, or the
wrapper default is `data/tools/apache-maven-3.9.11/bin/mvn`. The 30-run
scripts are:

```bash
python3 src/java_param_lineage.py
python3 src/run_maven_case.py --source data/javawebsocket_pre --goal surefire:test --out results/java_pre_30_complete --repeat 30
python3 src/run_maven_case.py --source data/javawebsocket_post --goal surefire:test --out results/java_post_30_complete --repeat 30
python3 src/java_before_after.py
```

The parent/post targets must already be **compiled using JDK 8**; `surefire:test`
intentionally does not compile. See the Maven attempts and JSON environment
records to distinguish the build prerequisites from actual repeated executions.

## Experimental boundaries

1. `TestMigrationsInPy` supplies real human-curated isolated test conversions.
   Negative **target-absent** queries are constructed by removing the correct
   new snippet; they are not historical CI deletions.
2. The Python benchmark only evaluates snippets with one test on each side
   and unique source and target test identities *within the commit*. All
   exclusions are counted, not silently ignored.
3. The held-out unit is a **project**, not a random test. Candidate draws use
   seeds 17, 29, 43. Calibration targets 2% false transfers on other projects;
   it does **not** guarantee the same rate on held-out projects.
4. The 30× Maven repeated outcomes are real. Resetting an identity and copying
   quarantine state are interventions in analysis, not logged industry actions.
5. The source-derived Java rules are validated on **one commit only**; they
   must not be presented as an externally replicated Java matcher.

## Source ethics and licenses

FTW 2024 simulated regression-test selection results are CC BY 4.0; see
`DATA_SOURCES_AND_LICENSES.md` for author credit. The migration corpus has no
explicit reuse license in its GitHub repository, so this artifact excludes
its raw code and reproduces the data by upstream checkout only. All output
tables are generated from public-source evidence; they do not constitute an
endorsement by the original projects or employers.
