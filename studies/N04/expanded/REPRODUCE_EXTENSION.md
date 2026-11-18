# Reproducing the 2026-11-15 extension

Run these commands from the extracted archive root. All observed metrics are
already frozen in the ZIP, and the **first two lines need no network**:

```bash
python3 src/verify_frozen.py
python3 -m unittest discover -s tests -v
```

The verification checks the original 2,526-query-per-arm migration benchmark,
actual repeated histories, Java JUnit outcomes, actual pytest cache behavior,
new GitLab/Aspire public action evidence, 4,990 new historical Python JUnit
test-case outcomes, the external 293-name corpus, and 151 SHA-256 digests.

## A. Re-run Python historical revisions (CPU only)

Python 3.12 and pytest 8.4.2 are used. Git checkouts **must** be at the exact
old and new SHAs; the script aborts on a mismatch. Installing the third-party
projects into the global interpreter is neither necessary nor recommended.

```bash
mkdir -p data
git clone https://github.com/pallets/click.git data/click_history
git -C data/click_history worktree add --detach ../click_pre_case_split 92129c552da88ac30b578132031efa4b003ecc46
git -C data/click_history worktree add --detach ../click_post_case_split 7c7ec36354f49d1a092cb077fa4881ea4d70ba01
git -C data/click_history worktree add --detach ../click_pre_types 87f7a316f482d88d7ef45660da12cdcc5a5c14f6
git -C data/click_history worktree add --detach ../click_post_types 7ecc8d7ee4a2e5c0732d6551baeb7597b7a73ade
git -C data/click_history worktree add --detach ../click_pre_utils df2e5ed8c4e89f51ff4eddb9600d913083613e62
git -C data/click_history worktree add --detach ../click_post_utils 9ab346f6b57f2c99388b4e9db58a0961bc3027c8
git clone https://github.com/pallets/markupsafe.git data/markupsafe_history
git -C data/markupsafe_history worktree add --detach ../markupsafe_pre_strip 0e366be90424816156802b41997b37b5dadd0851
git -C data/markupsafe_history worktree add --detach ../markupsafe_post_strip e49d257126d09937b1bf5e2b2173238df729fb13
python3 src/cross_repo_real_replay.py --repeats 10
```

The last command writes CSV and JSON into `results/cross_repo_pytest/`. It
replaces that directory's output files, changes the frozen manifest, and may
vary in timestamps/durations. **Re-run in a disposable copy** if preserving
the supplied checksums matters. The script always sets `PYTHONPATH` to each
checked-out `src` directory via an absolute path, rather than inadvertently
using the globally installed Click/MarkupSafe package. It disables automatic
external pytest plugin loading, as done in the frozen experiments.

## B. Re-run the source-based method comparisons

```bash
git clone https://github.com/altinoalvesjunior/TestMigrationsInPy.git data/TestMigrationsInPy
git -C data/TestMigrationsInPy checkout d29ae2370ee5d7ef81e78421c1f1d7f7b753c04c
python3 src/strong_baseline_extension.py
python3 src/hierarchical_history_linker.py
```

`src/hierarchical_history_linker.py` deliberately reports **post-hoc,
exploratory** improvement. It does not make the original +15pp target
possible; it does not cover production split outcomes or implement the
published TestRefactoringMiner. Its project-cluster bootstrap includes the
zero-difference boundary versus the stronger name+body baseline.

## C. Re-run the ICPC 2021 name-only stress benchmark

```bash
curl -fL https://zenodo.org/api/records/4608143/files/ICPC2021-Public.xlsx/content -o data/ICPC2021-Public.xlsx
sha256sum data/ICPC2021-Public.xlsx
python3 src/external_rename_probe.py
```

The expected source checksum is
`029c7c46c56bdb157076b67a91f7505b718d5e75216e30418ca0b294b64e4969`.
Read-only spreadsheet extraction uses `openpyxl`. The 1.8GB SQLite file from
the same study was **not** used. This probe has no runtime test bodies,
developer CI chronology or project-disjoint evaluation unit.

## D. Re-fetch real public CI management records

```bash
python3 src/ci_event_audit.py
python3 src/ci_event_chain.py
```

The first command accesses documented public GitHub/GitLab API routes and
records response hashes and merge/diff metadata. Public API rate limits can
produce HTTP 403 on some requests; these are explicitly marked unavailable.
It never opens a private dashboard or modifies the projects. The GitLab
independent fix chain requires a successful public API fetch. The frozen
results can be validated offline even if today's APIs are temporarily
unavailable. Current run dates, API response hashes and timings may change.

## E. Original Java repeat-execution experiment

The earlier Java-WebSocket Maven 3.9.11/Temurin JDK 8 real pre/post experiment
can be regenerated following the `README.md` frozen-case instructions. Its
2,400 case outcomes are included in the verifier alongside the 4,990 new
Python test-case outcomes. Both experiments use real versioned upstream
source, **not** upstream historical CI execution streams.

## Integrity and rights

The source ZIP intentionally excludes Git repository source trees, the ICPC
Excel input, the FTW 534MB archive, JDK/Maven binaries, and private credentials.
Source ownership and licensing details are in `DATA_SOURCES_AND_LICENSES.md`.
The 2026-11-15 experiments are designed to run without a GPU or paid API.
