#!/usr/bin/env bash
# Complete reproduction in a fresh, dedicated temporary directory. This does
# NOT overwrite the archived experimental results supplied with this release.
# Requires public GitHub/npm access, Node/npm, Python 3.12+, and several GB free.
set -euo pipefail

N21_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
N21_REPRO_ROOT="$(mktemp -d -t n21_reproduce_XXXXXXXX)"
N21_WORK_DIR="$N21_REPRO_ROOT/n21_submission_experiments"
mkdir -p "$N21_WORK_DIR"
cp "$N21_SCRIPT_DIR"/*.py "$N21_SCRIPT_DIR"/*.cjs "$N21_WORK_DIR/"
cd "$N21_WORK_DIR"
echo "Reproducing into $N21_WORK_DIR"

N21_FAULTS="delete_nested_js,delete_entry_js,delete_dts,corrupt_js,corrupt_dts,extra_stale,erase_dist,intact,buildinfo_missing"
N21_TS_FAULTS="delete_dts,corrupt_dts,extra_stale,intact"
N21_MAIN_ARMS="standard,selective_path,selective_hash,invalidate_all,clean_all,force_all,full_cache"
N21_SENS_ARMS="standard,selective_path,guarded_hash,clean_all,full_cache"

python3 run_n21.py prepare --cases libraries,andrewthauer,quramy,typescript
for N21_CASE in libraries andrewthauer quramy; do
    python3 run_n21.py run --cases "$N21_CASE" --results "results/$N21_CASE" \
        --faults "$N21_FAULTS" --arms "$N21_MAIN_ARMS" --seeds 17
    python3 run_n21.py run --cases "$N21_CASE" --results "results/guarded_$N21_CASE" \
        --faults "$N21_FAULTS" --arms guarded_hash --seeds 17
done
python3 run_n21.py run --cases typescript --results results/typescript \
    --faults "$N21_TS_FAULTS" --arms "$N21_MAIN_ARMS" --seeds 17
python3 run_n21.py run --cases typescript --results results/guarded_typescript \
    --faults "$N21_TS_FAULTS" --arms guarded_hash --seeds 17

python3 run_n21.py run --cases libraries \
    --projects libraries:ts-pattern,libraries:zod --results results/sensitivity_libraries \
    --faults delete_nested_js,corrupt_js,extra_stale --arms "$N21_SENS_ARMS" --seeds 29,43
python3 run_n21.py run --cases andrewthauer \
    --projects andrewthauer:api --results results/sensitivity_andrewthauer \
    --faults delete_nested_js,corrupt_js,extra_stale --arms "$N21_SENS_ARMS" --seeds 29,43
python3 run_n21.py run --cases quramy \
    --projects quramy:x-cli --results results/sensitivity_quramy \
    --faults delete_nested_js,corrupt_js,extra_stale --arms "$N21_SENS_ARMS" --seeds 29,43

python3 strong_baselines.py
python3 turbo_baseline.py
python3 run_api_probe.py
python3 input_drift_probe.py
python3 version_holdout.py
python3 audit_public_issues.py
python3 validate_results.py
python3 analyze_n21.py
python3 paper_tables.py
python3 robustness_stats.py
python3 figures_n21.py

echo "Complete. Fresh results are under $N21_WORK_DIR/results"
