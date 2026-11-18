# Data provenance, source locks and redistribution

Date of retrieval: 2026-11-14/15. Data are from public repositories and one
peer-reviewed research dataset; no proprietary systems or private CI logs.

## 1. TestMigrationsInPy (real developer test conversions)

- Original authors: Altino Alves and Andre Hora, *TestMigrationsInPy: A Dataset
  of Test Migrations from Unittest to Pytest*, MSR 2025 Data and Tool Showcase.
- Publisher: https://github.com/altinoalvesjunior/TestMigrationsInPy
- Frozen commit: `d29ae2370ee5d7ef81e78421c1f1d7f7b753c04c`.
- Publication: https://andrehora.github.io/pub/2025-msr-testmigrationsinpy.pdf
- Readme calls the data 923 isolated migrations. The checked-out directory has
  932 `mig*-before-*` entries, as counted in the experiment. This discrepancy
  is reported explicitly, and parsing/exclusion audits are saved in JSON.
- Redistribution: the GitHub repository did not expose an explicit LICENSE
  in this snapshot; the ZIP **does not contain its source code excerpts**.
  Reproduce using a separate checkout and respect the publisher's terms.

## 2. IDoFT (real flaky test identities and annotated renamings)

- Project/maintainer: Testing Research Illinois, Wing Lam et al., *International
  Dataset of Flaky Tests*.
- Repository: https://github.com/TestingResearchIllinois/idoft
- Frozen repository commit: `4903dc9233eead4e4191c66f9ed0b14eea091052`.
- `pr-data.csv` (Maven): SHA-256
  `4d9a8b9a0cbb597792efe328f4bf29300de585681b77d97fdaa98c90d96f93fb`.
- `gr-data.csv` (Gradle): SHA-256
  `ad10192d4c691aad89fcbbf532aa5db1823f157f97720b036d55079875ed1ae9`.
- `py-data.csv` (pytest): SHA-256
  `a1cf7425cd23096ae653af275fbba6c82d7d72ce5e17bb3db754e46e0e4c3c32`.
- Important existing precedent: IDoFT's own README **already specifies** when
  a moved/renamed test should retain its identity based on whether its method
  body changes. This reduces the novelty of body-fingerprint-only proposals.
- We count 245 Maven, one Gradle and two Python rows marked
  `MovedOrRenamed`, using exact case-sensitive status strings. The 245 Maven
  rows span 34 repositories; 216 provide explicit Git commit links.

## 3. Authentic repeated test outcomes (FTW 2024)

- Authors: Philipp Wendler and Stefan Winter; conference: 1st International
  Flaky Tests Workshop (FTW 2024).
- Paper: https://www.sosy-lab.org/research/pub/2024-FTW24.Regression-Test_History_Data_for_Flaky_Test_Research.pdf
- Data DOI: https://doi.org/10.5281/zenodo.10639030
- Publisher's file: `flaky_histories_dataset.tgz`, 534,249,001 bytes,
  MD5 `00e3f51ddd8ae8f92b62ceafe1130cce`.
- Parsed files: `flaky_histories_dataset/simulated_rt_results/*.csv.xz`;
  330 files, 4,654,230 result rows, eight unique parent projects (with
  multiple modules/FIC cohorts), and 30 repeats per test/commit.
- **License:** `simulated_rt_results/LICENSE` explicitly states Creative
  Commons Attribution 4.0 International, copyright 2023 Qingyu Li and Stefan
  Winter. Credit and CC BY 4.0 terms apply to derived result tables.
- Input results are real repeated developer test executions across actual
  commits. The paper's simulation concerns the **selection/replay of possible
  regression histories**; this package additionally simulates the identity
  handoff or loss. Neither source records real CI quarantine decisions.

## 4. Java-WebSocket real parametrization case

- Project: https://github.com/TooTallNate/Java-WebSocket
- Pre-refactoring **parent**: `27e26758d6604f5d078709233028bb87b4a39e16`.
- Post-refactoring commit: `2ce6e6149d0ef44f4919e75326265c64c144a00f`
  (author commit message: `Uses parameters`, Nov 8, 2018).
- https://github.com/TooTallNate/Java-WebSocket/commit/2ce6e6149d0ef44f4919e75326265c64c144a00f
- Source license: MIT, copyright 2010–2018 Nathan Rajlich, `LICENSE` in the
  pinned source tree. No source tree is packaged here.
- `Issue256Test.java` and `Issue580Test.java` convert forty former numbered
  runnable test methods into four methods with ten JUnit parameter instances
  each. Source-only matching against the helper call and index links 40/40.
  IDoFT supplies independent `MovedOrRenamed` labels for 27 of these 40.
- Real JUnit replay: both Git revisions compiled with Temurin JDK 8
  `1.8.0_512-b09` (because the original Maven compiler targets Java 6); the
  isolated Surefire executions used OpenJDK 21.0.13 on the same Linux host,
  Maven 3.9.11, plugin 3.2.5, and fixed targets `Issue256Test,Issue580Test`.
- Maven binary tarball SHA-256:
  `4b7195b6a4f5c81af4c0212677a32ee8143643401bc6e1e8412e6b06ea82beac`.
- Temurin 8 binary tarball SHA-256:
  `fb3bfa869012419b562bb4235d0d83ec4f8c1dda62ae432ba20c6c3a7e43f7e4`.
- The class names, test case IDs, outcomes and timing are extracted from
  Surefire JUnit XML to **sanitized CSV**, excluding build-system environment
  properties and private configuration.

## 5. pytest cache behavior and motivating issue

- Official pytest documentation: https://docs.pytest.org/en/stable/how-to/cache.html
- Public report: https://github.com/frankbria/codeframe/issues/984
- Real tool versions used in isolated Python fixtures: pytest 7.4.4,
  8.4.2 and 9.0.1. Python 3.12.14.
- Controlled fixtures are authored in this research package; they are not
  falsely attributed to public project maintenance histories.

## Integrity and no-leakage note

The main model's inputs are only the before snippet, candidate after snippets
and shared commit grouping. Dataset-provided before/after pairing indices are
held out as evaluation labels. Random candidate draws operate on the same
original commit and exclude the observed correct candidate for the no-target
counterfactual. Project-held-out calibration never reads target-project labels.
The source-derived Java parameter matcher reads only the two Git source
snapshots and is validated **after** mapping against the independent IDoFT
rows; it should nevertheless be treated as a single-case mechanism, not a
cross-project model evaluation.
# Source extension dated 2026-11-15

The following independently used sources underpin the appended experiments;
the package contains derived metadata/results only, not upstream Git trees or
the downloaded XLSX. This section is additional to the frozen sources below.

1. GitLab publicly merged MR/diff evidence: `gitlab-org/gitlab` MRs
   [!162803](https://gitlab.com/gitlab-org/gitlab/-/merge_requests/162803),
   [!163832](https://gitlab.com/gitlab-org/gitlab/-/merge_requests/163832),
   [!164022](https://gitlab.com/gitlab-org/gitlab/-/merge_requests/164022),
   !149942, !155883, !195179, and !228726. GitLab official public API
   `https://gitlab.com/api/v4/projects/gitlab-org%2Fgitlab/merge_requests/`
   with source URL + SHA-256 of every successful API response recorded in
   `results/real_ci_events/`; a source change is not a CI per-test outcome.
2. Microsoft Aspire, `https://github.com/microsoft/aspire`: merged PRs
   [#13874](https://github.com/microsoft/aspire/pull/13874),
   [#14040](https://github.com/microsoft/aspire/pull/14040),
   [#9023](https://github.com/microsoft/aspire/pull/9023). Each public
   GitHub API `pulls/{number}/files` and PR metadata response digest is
   preserved. Maintainer textual run counts are not independently acquired
   JUnit or workflow logs.
3. `https://github.com/pallets/click`: genuine historical Git revisions
   `7c7ec36354f49d1a092cb077fa4881ea4d70ba01`,
   `7ecc8d7ee4a2e5c0732d6551baeb7597b7a73ade`,
   `9ab346f6b57f2c99388b4e9db58a0961bc3027c8` and their direct
   first parents, locally executed with pinned source environment paths.
4. `https://github.com/pallets/markupsafe`: genuine historical Git revision
   `e49d257126d09937b1bf5e2b2173238df729fb13` and first parent
   `0e366be90424816156802b41997b37b5dadd0851`.
5. Peruma, Hu, Chen, Alomar, Mkaouer, Newman, **Using Grammar Patterns to
   Interpret Test Method Name Evolution**, ICPC 2021 public dataset,
   [Zenodo record 4608143](https://zenodo.org/records/4608143), DOI
   `10.5281/zenodo.4608143`, **CC BY 4.0**. `ICPC2021-Public.xlsx` 195,265
   bytes, SHA-256
   `029c7c46c56bdb157076b67a91f7505b718d5e75216e30418ca0b294b64e4969`.
   The 1.8 GB SQLite linked by the same authors was **not** downloaded or
   treated as evaluated data. Duplicate refactoring IDs are resolved before
   metrics are computed; only derived annotations/predictions are saved.
6. TestRefactoringMiner, `https://github.com/arieslab/TestRefactoringMiner`,
   existing published source/AST lineage prior art. We inspected its official
   repository/validation results to prevent an unjustified novelty claim,
   but did **not** execute it on the Python-only benchmark.

---

