# N22 — Checking Data Contracts Across Converging Database Migration Paths

**FSE 2027 Industry Track experimental artifact — 2026-11-18, exploratory / not submission-ready.**

> 研究问题：当两条真实迁移路径的最终 schema 和迁移账本相同，是否仍可能丢失业务必需数据？怎样避免把用户合法修改误报成迁移缺陷？

This repository contains executable upstream-engine replays, case labels, raw observations, SQLite databases, metrics, and a candid submission-readiness assessment. **It does not claim that the original N22 preregistered hypothesis has passed.**

## 1. Evidence in one screen

| Evaluation (case-level, not per repeat) | Contract | Full baseline with the same contracts | Schema | Ledger | Completed status | Untyped row diff | Row count only |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2 confirmed real failure inputs detected | 2/2 | 2/2 | 0/2 | 0/2 | 0/2 | 2/2 | 2/2 |
| False alarms on 13 core negatives | 0/13 | 0/13 | 0/13 | 0/13 | 0/13 | 5/13 | 4/13 |
| Additional 30 correlated legitimate user-edits | 0/30 | — | 0/30 | 0/30 | 0/30 | 30/30 | 0/30 |

- **Django 6.0.0:** `RenameModel(Song, Son)` triggers a permission-rename signal that also rewrites an older `SongProfile.view_songprofile` grant into `view_son`; a clean install and staged upgrade have identical final schema and migration ledger. A Django 6.0.1 fix removes this regression. Maintainer ticket: [Django #36843](https://code.djangoproject.com/ticket/36843).
- **OpenCode v2.0.19:** an older V1 assistant-message row with no `agent` field is skipped by the unmodified V1→V2 migrator even though its checkpoint says `completed`. Same SQLite schema/ledger as a compatible input. Independent maintainer issue: [#52226](https://github.com/anomalyco/opencode/issues/52226).
- **Excluded from primary score:** an OpenCode session written by a legacy client after the V2 checkpoint. Reproduced, but concurrency / unsupported coexistence policy not established; therefore only conditional evidence ([#50130](https://github.com/anomalyco/opencode/issues/50130)).
- **Controls:** Django 5.1.8 `sites`, `redirects`, and `flatpages` initialized fresh or staged, user-owned `Site.domain/name` edits, intentionally added redirects, and a migration no-op. These are not defects.

**Scale:** 46 unique case inputs (2 positive + 13 core negative + 30 correlated stress variants + 1 conditional), 3 new-process repeats or isolated in-memory DB repeats each = **138 observations**, including **126 separate process invocations**. An additional 9 baseline runs are in `runs/baselines_complete`.

**Main negative result:** The full manual/test baseline, once given the same explicit data-contract assertions, detects exactly the same 2/2 real failures at equal replay budget. Incremental recall = **0 percentage points**, below the original ≥15pp requirement. The observed 0/13 false alarm rate has a one-sided 95% upper bound of 20.58% even under an optimistic independence assumption; thus the original ≤5% false-alarm criterion is **not statistically supported**. These cases were found and labeled retrospectively, not blind/preregistered. **Do not use these numbers as prospective performance or industrial ROI claims.**

## 2. Files

| Path | Purpose |
|---|---|
| `code/replay_django.py` | Django 6.0 / 6.0.1 real `manage.py migrate` vs app-level `User.has_perm` oracle |
| `code/replay_django_sites.py` | Django 5.1.8 official migrations and legitimate changes |
| `code/opencode_replay.test.ts` | In-memory real OpenCode v2.0.19 migration, five scenario fixtures |
| `code/baseline_django_test_migrations.py` | Django helper test-library semantics; note signal suppression |
| `code/run_all.py` | Reproducible orchestrator; pinned versions / commits; independent fresh databases |
| `code/run_baselines.py` | Three repeats of 26 upstream OpenCode tests plus migration helper comparisons |
| `code/analyze.py`, `tests/test_metrics.py` | Raw-evidence-only contract checks, controls, paired comparator metrics |
| `benchmarks/labels.json` | External issue-based retrospective adjudication and exclusion policy |
| `runs/full/observations.jsonl` | Full raw observation set; `provenance.json` includes source pins and hashes |
| `runs/full/databases/` | SQLite data generated for each Django experiment input and repeat |
| `runs/full/logs/`, `runs/full/raw_json/` | Commands, stdout, stderr, original JSON per process |
| `runs/baselines_complete/` | Raw helper / unchanged upstream suite baseline files |
| `reports/case_table.csv`, `reports/metrics.json` | Recomputed case-level statistics |
| `reports/RESULTS_AND_LIMITATIONS.md` | Comprehensive case descriptions, risk, and non-claims |
| `paper/experimental_results.tex` | Honest, paper-ready experiment subsection (not a complete paper) |

## 3. Reproduce without changing upstream migration code

Required: Linux x86_64, Python 3.12, `uv`, Bun **1.3.1**, SQLite, `git`; a network-connected install with sufficient disk space for the upstream OpenCode Bun monorepo. The recorded baseline used Python 3.12.14 and SQLite via Python. Re-run analyses using only Python standard library.

```bash
git clone --branch n22-fse-industry https://github.com/shjdjjfi/FSE-EXP-1.git FSE-EXP-1
cd FSE-EXP-1/N22/addenda/20261118_django_opencode

uv venv /tmp/n22_dj600 --python 3.12
uv venv /tmp/n22_dj601 --python 3.12
uv venv /tmp/n22_dj518 --python 3.12
uv pip install --python /tmp/n22_dj600/bin/python -r env/django600.txt
uv pip install --python /tmp/n22_dj601/bin/python -r env/django601.txt
uv pip install --python /tmp/n22_dj518/bin/python -r env/django518.txt

git clone https://github.com/anomalyco/opencode.git /tmp/n22_opencode
git -C /tmp/n22_opencode checkout 1fd016ef32286de9489b7b24f1029f52c49a27b3
(cd /tmp/n22_opencode && bun install --frozen-lockfile --ignore-scripts)
cp code/opencode_replay.test.ts /tmp/n22_opencode/packages/core/test/n22_contract_replay.test.ts

python code/run_all.py \
  --dj600 /tmp/n22_dj600/bin/python \
  --dj601 /tmp/n22_dj601/bin/python \
  --dj518 /tmp/n22_dj518/bin/python \
  --bun "$(command -v bun)" \
  --opencode /tmp/n22_opencode \
  --output runs/my_replay --repetitions 3 --user-variants 30 --jobs 6

python code/analyze.py --input runs/my_replay --output reports/my_replay
python -m unittest discover -s tests -v
python code/run_baselines.py \
  --dj600 /tmp/n22_dj600/bin/python --dj601 /tmp/n22_dj601/bin/python \
  --bun "$(command -v bun)" --opencode /tmp/n22_opencode \
  --output runs/my_baselines --repetitions 3
```

The target output directories **must not already exist**: replay scripts deliberately refuse to overwrite evidence. The script checks the exact OpenCode commit and harness hash. The replay install copies only a research test file into your disposable clone; upstream source implementation is unchanged.

`runs/full` and `runs/baselines_complete` are the executed datasets supplied in the downloadable artifact. The GitHub mirror can carry the smaller sources, processed results and observations without all disposable SQLite files; see the ZIP for full raw data.

## 4. Interpretation and readiness

This is a rigorous *failure-characterization artifact*, not validation of a new detection tool or prospective industrial impact. The industrial conference would need a practitioner setting, repeatable path selection with unseen projects, coverage vs full baselines at equal cost, confidence-aware error bounds, and operational ROI. Existing [Artemis migration consolidation checks](https://docs.artemis.tum.de/developer/guidelines/database-migration-consolidation/) already perform fresh/upgrade comparisons; this prior art must be cited. The [FSE 2027 Industry Track](https://conf.researchr.org/track/fse-2027/fse-2027-industry-papers) evaluates industrial relevance as well as methodological credibility.

See `reports/RESULTS_AND_LIMITATIONS.md` and `paper/experimental_results.tex` before making any scientific claims.

## License and ethics

Research harness and derived statistics are provided for reproducibility, without copied upstream source distributions. Do not run against production data; all generated databases are synthetic SQLite fixtures. Upstream Django and OpenCode retain their respective licenses. No confidential organization/user data was collected.
