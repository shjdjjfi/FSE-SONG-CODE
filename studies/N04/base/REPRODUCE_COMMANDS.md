# Exact experiment command log

Run from the `n04_experiments` folder after installing `requirements.txt`. Let `../inputs/` contain public Git clones and the Zenodo extraction as explained in `README.md`. **The ZIP includes completed results already; the commands below overwrite JSON files.** For first-look verification, use `python3 src/verify_results.py` instead.

Inputs are pinned by Git commit in `SOURCE_PROVENANCE.md` and `results/provenance.json`.

## 1. FTW ingestion and source chronology (all 11 tracks)

```bash
python3 src/ingest_histories.py \
  --input ../inputs/flaky_histories_dataset/simulated_rt_results \
  --output results/ftw_histories.json

python3 src/align_git.py \
  --histories results/ftw_histories.json \
  --repo apereo/java-cas-client ../inputs/java-cas-client \
  --repo eclipse-ee4j/tyrus ../inputs/tyrus \
  --repo feroult/yawp ../inputs/yawp \
  --repo fluent/fluent-logger-java ../inputs/fluent-logger-java \
  --repo spotify/helios ../inputs/helios \
  --repo javadelight/delight-nashorn-sandbox ../inputs/delight-nashorn-sandbox \
  --repo sonatype-nexus-community/nexus-repository-helm ../inputs/nexus-repository-helm \
  --repo TooTallNate/Java-WebSocket ../inputs/java-websocket \
  --output results/source_aligned.json
```

## 2. IDoFT public labels, 8 baselines/ablations and label audit

```bash
python3 src/build_idoft.py \
  --idoft ../inputs/idoft \
  --repo TooTallNate/Java-WebSocket ../inputs/java-websocket \
  --repo danfickle/openhtmltopdf ../inputs/openhtmltopdf \
  --repo zalando/riptide ../inputs/riptide \
  --repo jdereg/json-io ../inputs/json-io \
  --repo spring-cloud/spring-cloud-kubernetes ../inputs/spring-cloud-kubernetes \
  --repo Activiti/Activiti ../inputs/activiti \
  --repo graphhopper/graphhopper ../inputs/graphhopper \
  --output results/idoft_migrations.json

python3 src/evaluate_idoft.py --input results/idoft_migrations.json \
  --bootstrap 1500 --output results/idoft_evaluation.json

python3 src/audit_idoft.py --input results/idoft_migrations.json \
  --output results/label_audit.json

python3 src/statistical_audit.py --evaluation results/idoft_evaluation.json \
  --output results/statistical_audit.json
```

The evaluation's per-arm cluster bootstrap uses seeds 17/29/43 with 1500 draws *per seed*; the separate paired-difference script uses 3000 draws *per seed*. These are Monte Carlo descriptive intervals over migration events, not independent industrial deployments.

### Cross-project holdout feasibility audit

```bash
python3 src/build_idoft.py \
  --idoft ../inputs/idoft \
  --repo google/guava ../inputs/guava \
  --repo alibaba/druid ../inputs/alibaba-druid \
  --repo c2mon/c2mon ../inputs/c2mon \
  --repo apache/maven-doxia ../inputs/maven-doxia \
  --output results/idoft_heldout.json

python3 src/evaluate_idoft.py --input results/idoft_heldout.json \
  --bootstrap 300 --output results/idoft_heldout_evaluation.json
```

## 3. Manual source diff gold and real-result policy replay

```bash
python3 src/evaluate_source_gold.py \
  --gold evidence/source_events_gold.json \
  --repo apereo/java-cas-client ../inputs/java-cas-client \
  --repo javadelight/delight-nashorn-sandbox ../inputs/delight-nashorn-sandbox \
  --output results/source_gold_evaluation.json

python3 src/replay_history_policy.py \
  --histories results/ftw_histories.json \
  --aligned results/source_aligned.json \
  --gold evidence/source_events_gold.json \
  --output results/actual_history_policy.json
```

## 4. Real JUnit tests across parameterization (local Java 21, Maven 3.9.11)

```bash
python3 src/replay_maven.py \
  --repo ../inputs/java-websocket \
  --revisions '2ce6e6149d0ef44f4919e75326265c64c144a00f^' 2ce6e6149d0ef44f4919e75326265c64c144a00f \
  --maven ../inputs/apache-maven-3.9.11/bin/mvn \
  --test Issue256Test --repeats 3 --timeout 150 \
  --output results/maven_replay.json

python3 src/replay_maven.py \
  --repo ../inputs/java-websocket \
  --revisions '2ce6e6149d0ef44f4919e75326265c64c144a00f^' 2ce6e6149d0ef44f4919e75326265c64c144a00f \
  --maven ../inputs/apache-maven-3.9.11/bin/mvn \
  --test Issue580Test --repeats 3 --timeout 150 \
  --output results/maven_replay_issue580.json

python3 src/evaluate_junit_parameters.py \
  --migration results/idoft_migrations.json \
  --maven results/maven_replay.json \
  --maven results/maven_replay_issue580.json \
  --output results/junit_parameter_migration.json
```

The Maven runner performs **temporary build-only compatibility adaptations** to the historical Java sources, as documented in `src/replay_maven.py`. It preserves the target test classes and writes all Surefire testcase statuses to JSON. The Maven output logs are truncated in JSON to a reproducible diagnostic tail; no test failure is inferred from build/compile failures.

## 5. Pytest cache behavior, real CI availability audit, figures

```bash
python3 src/replay_pytest.py --seeds 17 29 43 \
  --output results/pytest_cache_replay.json

python3 src/audit_real_ci.py \
  --source ../inputs/flaky-test-dataset/data/PrefectHQ/prefect/main.json \
  --source ../inputs/flaky-test-dataset/data/PrefectHQ/prefect/main2026-06-26T08:07:27.257905.json \
  --source ../inputs/flaky-test-dataset/data/home-assistant/core/dev.json \
  --source ../inputs/flaky-test-dataset/data/home-assistant/core/dev-new2026-07-01T09:07:13.672728.json \
  --output results/real_ci_audit.json

python3 src/make_figures.py --results results --output figures
python3 -m unittest discover -s tests -v
python3 src/verify_results.py
```

## 6. Freeze provenance **after** the whole bundle is final

```bash
python3 src/record_provenance.py --inputs ../inputs \
  --output results/provenance.json
python3 src/verify_results.py
```

Running any subsequent command that rewrites a frozen result, figure, source, or documentation file will intentionally fail the integrity verifier until provenance is regenerated. Do not regenerate the manifest merely to conceal a changed result; retain the previous hash/commit in any paper artifact revision log.
