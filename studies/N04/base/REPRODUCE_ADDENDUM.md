# Reproduce the N04 three-gap follow-up

The original FTW/IDoFT/Java experiments are described in `REPRODUCE_COMMANDS.md`. This file covers only the new quarantine, labeling, and independent holdout experiments. No paid API or GPU is needed. The included frozen `results/*.json` already contain all per-row measurements; large Git trees and GitHub run logs are not inside the portable ZIP.

## 1. Python environment

From this ZIP's root:

```bash
python3 -m pip install -r requirements.txt
python3 -m unittest discover -s tests -v
python3 src/verify_results.py
python3 src/verify_addendum.py
python3 src/make_addendum_figures.py --results results --output figures
```

We used Python 3.12 and Tree-sitter Java from `requirements.txt`; all new algorithms are CPU-only. For full source reproduction, clone the public repositories to a sibling `../addendum_inputs` directory. The helper refuses to overwrite an existing checkout unless explicitly told to reuse it.

```bash
python3 src/fetch_addendum_public_sources.py \
  --oracle results/independent_refactoring_oracle.json \
  --output-root ../addendum_inputs
```

It downloads only Git metadata and on-demand historical Java/TestScript blobs. The `RefactoringMiner` oracle SHA and source Git commit hashes are in `results/independent_refactoring_oracle.json`; the script fetches source commits with their direct parents to make source-diff replay possible. Depending on repository and network availability, public history downloads can take a while. They are not needed merely to inspect frozen outcomes.

## 2. Rebuild independent source-label holdout

```bash
python3 src/build_refactoring_oracle.py \
  --oracle-repo ../addendum_inputs/refactoringminer \
  --rev bc89d3de19a7566e4c2ce76f34c3394735de8ae4 \
  --output results/independent_refactoring_oracle.recomputed.json

python3 src/evaluate_oracle_source.py \
  --oracle results/independent_refactoring_oracle.json \
  --repo https://github.com/apache/cassandra ../addendum_inputs/oracle_cassandra \
  --repo https://github.com/checkstyle/checkstyle ../addendum_inputs/oracle_checkstyle \
  --repo https://github.com/infinispan/infinispan ../addendum_inputs/oracle_infinispan \
  --repo https://github.com/google/closure-compiler ../addendum_inputs/oracle_closure-compiler \
  --output results/independent_source_validation.recomputed.json

python3 src/evaluate_oracle_discovery.py \
  --oracle results/independent_refactoring_oracle.json \
  --repo https://github.com/apache/cassandra ../addendum_inputs/oracle_cassandra \
  --repo https://github.com/checkstyle/checkstyle ../addendum_inputs/oracle_checkstyle \
  --repo https://github.com/infinispan/infinispan ../addendum_inputs/oracle_infinispan \
  --repo https://github.com/google/closure-compiler ../addendum_inputs/oracle_closure-compiler \
  --output results/independent_end_to_end_discovery.recomputed.json

python3 src/analyze_independent_generalization.py \
  --input results/independent_end_to_end_discovery.recomputed.json \
  --output results/independent_generalization_statistics.recomputed.json
```

The method uses the old test FQN and **the Git diff only** to generate successors. The oracle's independently validated new FQN and TP/FP annotations are never read during prediction. **RefactoringMiner FP is not an adjudicated nonidentical-test label**: do not use it as a false quarantine-inheritance denominator. The frozen report measures 54 positive refactoring edges, not 54 independent CI quarantines.

## 3. Rebuild real quarantine decisions and source-linked case

```bash
python3 src/mine_quarantine_ledger.py \
  --repo ../addendum_inputs/fusion \
  --ledger scripts/lib/test-quarantine.json \
  --output results/fusion_quarantine_ledger.recomputed.json

python3 src/mine_quarantine_ledger.py \
  --repo ../addendum_inputs/trycua \
  --ledger .github/flaky/quarantine.json \
  --output results/trycua_quarantine_ledger.recomputed.json

python3 src/audit_fusion_quarantine_migration.py \
  --repo ../addendum_inputs/fusion \
  --output results/fusion_identity_linked_quarantine.recomputed.json

python3 src/audit_riptide_git_renames.py \
  --repo ../addendum_inputs/riptide \
  --label-audit results/label_audit.json \
  --output results/riptide_git_rename_audit.recomputed.json
```

Each Fusion ledger version is loaded from an actual Git commit. Historically malformed JSON snapshots are recorded as parse errors and never silently repaired. Removing a quarantine entry has an **ambiguous cause** and is not automatically a successful rescue. The matched `b545083` case is a **file-level** TypeScript/Vitest split; it does not demonstrate a Java method-level N04 deployment.

## 4. Fetch real public GitHub Actions metadata

The following uses the **read-only public GitHub REST API** and does not need credentials. GitHub may impose unauthenticated rate limits and may change which archived runs remain accessible:

```bash
python3 src/fetch_fusion_ci_metadata.py \
  --repo ../addendum_inputs/fusion \
  --output results/fusion_real_ci_runs.recomputed.json
```

Required public run IDs are `28697507894` (the failure linked in the original and replacement quarantine records) and `28720367126` (a later Full Suite run whose head commit descends from the split). The public response supplies each workflow's outcome and job start/end timestamps. The run-log endpoint was HTTP 403 when accessed anonymously. Neither workflow is a controlled counterfactual; both had other failures, and this does **not** measure avoided reruns or saved CI bills.

## 5. Original and extended integrity records

`results/provenance_v1.json` preserves the original ZIP's SHA256 manifest. `results/provenance.json` covers the updated ZIP after edits and contains both original measurement files and the addendum. The original result JSON files were not overwritten. `src/verify_addendum.py` checks 142/81/61, 105/54/51, 40/54 vs 39/54, a real one-file quarantine split, the original 4/9, and the two actual CI runs before allowing any summary claim.

To refresh this ZIP's **updated** checksum manifest after intentional edits, use the documented script `src/record_addendum_provenance.py`; this is a bulk mechanical hash-generation operation and should not be used to tamper with underlying measured JSON values.
