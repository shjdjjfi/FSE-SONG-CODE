# Public-source provenance and pinned revisions

All third-party sources were accessed as public research records or Git repositories. No passwords, tokens, account-specific CI logs, proprietary test artifacts, or private source files are included. **Repositories, original datasets, downloaded Maven binaries, and the 510 MB original archive are not redistributed in the experiment ZIP.** Their license conditions remain those of the upstream owners.

## Research datasets

| Data | Original source | Frozen version / checksum | Role / important limitation |
|---|---|---|---|
| FTW regression history | [Zenodo record 10639030](https://zenodo.org/records/10639030) | Archive MD5 `00e3f51ddd8ae8f92b62ceafe1130cce`; SHA256 `c03d5c6954fe80b8592f765ad4805fb59a03d866cbeeb49388a002a5e1e7da70` | CC BY 4.0; repeated **offline** source-history executions, not production CI |
| IDoFT | [TestingResearchIllinois/idoft](https://github.com/TestingResearchIllinois/idoft) | `4903dc9233eead4e4191c66f9ed0b14eea091052` | Old-test statuses only, not complete successor-FQN oracle |
| Test Flare | [test-flare/flaky-test-dataset](https://github.com/test-flare/flaky-test-dataset) | `b872ed937b7b811938e58b1a13bb3144882fda21` | Real Actions failure candidates; lacks linked quarantine states |
| Flaky tests in CI replication | [tum-i4/flaky-tests-in-ci](https://github.com/tum-i4/flaky-tests-in-ci) | Public study reference; not imported into the main quantitative table | Coverage prospect, not evidence of present matched quarantine labels |

FTW analysis ingested **330 individual `.csv.xz`** CSVs extracted from the archived release, not the bundled Docker filesystem. The original release is approximately 510 MB; the individual parsed outcome fields are summarized in `results/ftw_histories.json`. Test-suite execution timestamps are 2023 replay times. Analysis reorders commits by Git ancestry.

## Source Git HEAD pins at analysis time

The following hashes refer to the **cloned repository HEAD used to access historical commits**. Individual before/after evidence SHA values are stored in `results/source_aligned.json`, `results/idoft_migrations.json`, `results/junit_parameter_migration.json`, and `evidence/source_events_gold.json`. A repository's present HEAD is *not* an experimental before/after test revision.

| Repository | Local clone directory | Repository HEAD |
|---|---|---|
| [apereo/java-cas-client](https://github.com/apereo/java-cas-client) | `java-cas-client` | `dfaa93aaf0e4776d8ea2b65e550196bdbe697fbd` |
| [javadelight/delight-nashorn-sandbox](https://github.com/javadelight/delight-nashorn-sandbox) | `delight-nashorn-sandbox` | `e9b3ebd48c46ec0843535becadf8b2055676ba42` |
| [TooTallNate/Java-WebSocket](https://github.com/TooTallNate/Java-WebSocket) | `java-websocket` | `afeacbf8c0f6f6a761c9d9daed8c813dd3b8ed7d` |
| [eclipse-ee4j/tyrus](https://github.com/eclipse-ee4j/tyrus) | `tyrus` | `d6dc66cd3e858f852872a53059699755e97dc2e9` |
| [feroult/yawp](https://github.com/feroult/yawp) | `yawp` | `a415710efce1aa25ad3bade754b8b57ed398f36e` |
| [fluent/fluent-logger-java](https://github.com/fluent/fluent-logger-java) | `fluent-logger-java` | `2e5fdf2dbed59cc5af88442ceae6cbe72f321060` |
| [spotify/helios](https://github.com/spotify/helios) | `helios` | `819e59493b502ddbf40cd96a4a7a0ea2a8af3edb` |
| [sonatype-nexus-community/nexus-repository-helm](https://github.com/sonatype-nexus-community/nexus-repository-helm) | `nexus-repository-helm` | `e9178160b16f5500a1e91b21ee98423a96968f65` |
| [danfickle/openhtmltopdf](https://github.com/danfickle/openhtmltopdf) | `openhtmltopdf` | `780ba564839f1ad5abfa5df12e4aebb9dd6782d2` |
| [zalando/riptide](https://github.com/zalando/riptide) | `riptide` | `fabb72952974bef818f958f559a26daaa67abc53` |
| [jdereg/json-io](https://github.com/jdereg/json-io) | `json-io` | `893e7dbed1b3f358e66a364fce3d3793c84f9f9b` |
| [spring-cloud/spring-cloud-kubernetes](https://github.com/spring-cloud/spring-cloud-kubernetes) | `spring-cloud-kubernetes` | `e102dc5730b3b3e45b8552ac0382f197e6277c83` |
| [graphhopper/graphhopper](https://github.com/graphhopper/graphhopper) | `graphhopper` | `9df847473a5e73e979ce194ca0fc9a0767a5bb36` |
| [Activiti/Activiti](https://github.com/Activiti/Activiti) | `activiti` | `e06f2b3f15f71a9387f4d8f12f6fbb5440324344` |
| [google/guava](https://github.com/google/guava) | `guava` | `fce80fd984c8227262a63972ccc68ae6f2ad0519` |
| [alibaba/druid](https://github.com/alibaba/druid) | `alibaba-druid` | `fa8dc9912637a2f729eef9f55356621fec18d40e` |
| [c2mon/c2mon](https://github.com/c2mon/c2mon) | `c2mon` | `c8d8edbd52162a76ea1e419bb60fadb7521bb617` |
| [apache/maven-doxia](https://github.com/apache/maven-doxia) | `maven-doxia` | `dbaf4dad39e2e473df8df8a9c89f6c2697e6dc0a` |

The case selection is deliberately nonrandom: a migration commit must be reachable and Java test files must parse. See the complete `excluded` counters in `results/idoft_migrations.json` and `results/idoft_heldout.json`.

## Toolchain and external baselines

- Python 3.12 at measurement; `pytest 8.4.2`, `tree-sitter 0.25.2`, `tree-sitter-java 0.23.5`, `numpy 2.3.5`, `scipy 1.17.0`, `matplotlib 3.10.8`. Exact package pins are in `requirements.txt` and `results/provenance.json`.
- Java 21, Apache Maven 3.9.11; the Maven binary was downloaded from the official distribution, not redistributed. Real Java tests were executed through the original public source's Surefire/JUnit reports, with the temporary **build-only** compatibility adjustments disclosed in `src/replay_maven.py` and individual JSON outputs.
- [Pytest cache/lastfailed documentation](https://docs.pytest.org/en/stable/how-to/cache.html) and [Codeframe issue #984](https://github.com/frankbria/codeframe/issues/984) motivated the controlled cache replay.
- [Gruber et al., ICST 2023, Practical Flaky Test Prediction](https://arxiv.org/abs/2302.09330) shows test-history-based flaky prediction predates this work; a fresh identity/quarantine outcome contribution must be independently demonstrated.
- [Microsoft Aspire documented quarantine](https://github.com/microsoft/aspire/blob/main/AGENTS.md) and [Apache Kafka KIP-1090](https://cwiki.apache.org/confluence/spaces/KAFKA/pages/321719036/KIP-1090%2BFlaky%2BTest%2BManagement) are example mechanisms, **not** counted as available matched transitions in this dataset.

## Citation and redistribution

Use dataset DOI/URLs and original publication citation in any submission, not just this document. Third-party project names, data snapshots and source excerpts retain their upstream ownership. This bundle contains derived scripts, aggregate/row-level metadata and small manual annotations only. The frozen data have not been silently corrected when conflicting with later source analysis.
