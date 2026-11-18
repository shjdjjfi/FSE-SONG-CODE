# I01 Full Follow-Up: Fixed Security Releases Across Python Runtime/OS Frontiers

This folder contains an independently sampled, **actual CPU-only experiment**
expanding the preregistered 88-scenario pilot of idea I01. It is **not** a full
real-application security remediation benchmark. Every result must be read under
the wheel-only, **exact OSV-stated fixed release**, public-PyPI assumptions.

## 1. Research question

For a package whose OSV advisory says its vulnerability was fixed in version
`F`, how does the ability to resolve **exactly F plus transitive dependencies**
vary across Python runtime and operating-system targets? Can a cheap root-wheel
compatibility gate identify impossible targets before a full dependency solver?

## 2. Scope and sources

- Open vulnerability records: OSV official PyPI database snapshot, file
  `raw/osv-pypi-20261114.zip`, SHA-256
  `305dbca79abb7dc1bf52c8466c1be9e7c134b25ec67975c2d395f5259041d22e`.
- Public fixed-release metadata: PyPI `/pypi/{project}/{version}/json`, with
  preserved raw API responses and response SHA-256 in `metadata_index.json`.
- Frame: 26,915 OSV JSON entries, 1,364 distinct projects with a published
  record and at least one valid ECOSYSTEM `fixed` event.
- Sample: 120 unique projects, 40 each from OSV latest-advisory published
  `<=2023`, `2024–25`, and `2026`; fixed SHA-256-based project selection.
- Tests: 4 CPython versions × 3 platforms = 1,440 target cases.
- Operating systems: Linux x86-64/glibc >=2.17 (`manylinux2014`), Windows
  AMD64, macOS 11 arm64. Python versions: 3.8, 3.10, 3.12, 3.14.
- Resolver: `uv pip compile --python-version ... --python-platform ...
  --only-binary :all: --no-python-downloads` (full transitive closure).
- Preregistered replication on 20% of cases: pip 26.2.2 cross-target
  `install --dry-run` with all dependencies, plus a separate `--no-deps` root
  oracle. **Post-hoc supplemental falsification:** strict pip direct/full
  analysis of all 1,440 targets, recording root-only logical short-circuits.
  pip cross-target marker evaluation need not equal uv; disagreement is audited.
- Machine: x86-64 CPU, Python 3.12.14, glibc 2.41; uv 0.13.6;
  packaging 26.3; NumPy 2.3.5; Matplotlib 3.10.8; SciPy 1.17.0.

No GPU, model, paid API, source-package build, package import/installation or
application CI. Network access is only to public OSV/PyPI metadata and indexes.

## 3. Reproduce and verify

Use a clean Linux machine with internet access and a working Python 3.12+,
pip and uv. The supplied `raw/` snapshot is sufficient to reproduce sampling
and root preflight without network. Transitive resolver results require PyPI
access, and **may change with index drift**, despite the frozen OSV snapshot.

```bash
# Run from this folder
python3 -m pip install -r requirements-analysis.txt

python3 inventory_osv.py        # corpus/frame descriptive counts
python3 sample.py               # deterministic 120-project OSV sample
python3 fetch_metadata.py       # fetch only absent PyPI API responses
python3 run.py preflight        # binary root gate, 1,440 cases
python3 run.py uv --workers 4   # real complete resolver on all 1,440
python3 run.py pip_all --workers 4  # strict pip audit of all 1,440;
                                    # writes 288 frozen dual-mode checks
python3 analyze.py              # exact tables, figures, bootstrap CIs
python3 write_report.py         # complete Chinese scientific report from results
python3 verify.py               # require ALL provenance/integrity checks to pass
python3 package.py              # zip with manifest (after verify succeeds)
```

`run.py` resumes JSONL outputs by `case_id` and flushes after every outcome.
For the supplied study, see `DEVIATIONS_AND_AUDIT.md`: an initial macOS pass
used uv's default macOS 13 instead of the preregistered macOS 11. The corrected
macOS 11 pass is in `uv_macos11.jsonl`; to reproduce that exact audit rerun,
use `python3 run.py uv_macos11 --workers 4`. The analyzer replaces only those
480 macOS outcomes with the entire independently rerun subset. A fresh
`run.py uv` now specifies macOS 11 correctly from the outset.
To independently rerun rather than resume, copy the folder and remove the
copied `uv_full.jsonl`/`pip_validation.jsonl` first; **do not overwrite the
original archived experimental observations**.

## 4. File guide

| File/directory | Purpose |
|---|---|
| `PREREGISTRATION.md` | Sampling and endpoints frozen before oracle results |
| `inventory_osv.py`, `osv_inventory.json` | Official OSV corpus inventory |
| `sample.py`, `sampling_summary.json`, `osv_sample120.json` | Project-diverse deterministic selection |
| `fetch_metadata.py`, `metadata_index.json`, `raw/pypi_responses` | Version-specific PyPI API payloads, SHA-256 |
| `run.py`, `all_1440_cases.json`, `preflight_summary.json` | Baselines, compatibility gates and case manifest |
| `uv_full.jsonl` | All 1,440 **actual** uv outcomes, exit codes, durations, stdout/stderr SHA-256 and bounded text excerpts; long streams are not archived verbatim |
| `uv_macos11.jsonl`, `DEVIATIONS_AND_AUDIT.md` | Corrected 480 macOS 11 cases, plus transparent first-pass audit |
| `pip_validation_ids.json`, `pip_validation.jsonl` | Frozen 20% pip cross-check, both full and no-deps |
| `pip_all.jsonl` | Every target audited with strict pip; actual full calls vs independently justified root-only short circuits, exit codes and output hashes distinguished |
| `analyze.py`, `analysis_results.json`, `TABLES.md`, `figures/` | Recomputed results, stratified project bootstrap and visualizations |
| `write_report.py`, `I01_完整实验报告.md` | Recomputed Chinese report; no manually edited outcome percentages |
| `verify.py`, `verification_results.json`, `package.py`, `ARTIFACT_MANIFEST.json` | Artifact consistency checks, file digests and deterministic ZIP |

## 5. Definitions that matter

- `root gate false` means this **particular OSV-declared fixed version** has
  no compatible, non-yanked wheel or declares incompatible Python. It does
  *not* mean no safe release or backport exists.
- `full solver unsat` means no wheel-only transitive resolution for the pinned
  fixed version and target metadata; it does *not* establish any import/build/
  test/API compatibility, security audit, or production deployment result.
- `unknown` means metadata or solver could not decide within the bounds.
- `planner` invokes full uv only for root-positive/unknown cases; final
  agreement and saved calls are evaluated against full uv on **all** targets.
  This is a necessary-condition gate, not a replacement for a dependency solver.
- Independent `pip --no-deps` is the principal validation of root predictions;
  `pip` full cross-platform markers may differ from uv's target markers.
- uv deliberately ignores `Requires-Python` **upper bounds**; therefore an
  `uv` compile success is not synonymous with strict wheel installability.
  The full strict-pip audit is a **post-hoc** check, with the unaltered uv
  results preserved; see `DEVIATIONS_AND_AUDIT.md`.
- Per-project/bootstrap uncertainty accounts for repeated 12 cases per
  project; year strata were sampled equally, not by natural frame frequency.

## 6. Publication caveat

FSE 2027 Industry Track accepts research motivated by real industry problems,
even without an industrial coauthor, but this study alone does not reproduce
the production project's constraints or demonstrate functioning repair. An
industry-ready paper should add real-repository constraints, a remediation
decision task, evidence that missing root wheels cause genuine developer
friction, and direct comparison with `VulnBump` (arXiv:2610.17374).

## 7. Sources

- OSV database: https://google.github.io/osv.dev/data/
- OSV schema: https://ossf.github.io/osv-schema/
- PyPI release JSON: https://github.com/pypi/warehouse/blob/main/docs/user/api/json.md
- uv resolution: https://docs.astral.sh/uv/concepts/resolution/
- pip dry run: https://pip.pypa.io/en/stable/cli/pip_install/
- VulnBump 2026: https://arxiv.org/abs/2610.17374
- FSE 2027 Industry track: https://conf.researchr.org/track/fse-2027/fse-2027-industry-papers
