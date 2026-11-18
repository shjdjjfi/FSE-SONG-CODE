# Publication and reproduction notes

This Git mirror contains the research code, scripts, frozen evidence, reports,
and figures. The [archive inventory](PROVENANCE.md) identifies all twelve
supplied packages. Files kept outside Git and their exact SHA-256 digests are
listed in [EXTERNAL_INPUTS.tsv](EXTERNAL_INPUTS.tsv).

## Restore external inputs for a full replay

- **I01** — The unpacked CPU baseline is under `studies/I01/i01_full/`.
  To run both original strict verifiers, recover `previous_offline_study.zip`
  from the supplied I01 extension ZIP, and recover the baseline's raw OSV
  snapshot from inside that archive. Place them at the paths in the input
  inventory. The baseline's frozen case records, results, and parsed advisory
  identifiers are included here.
- **N02** — Recover the chart packages from the cumulative N02 ZIP or retrieve
  the pinned versions from upstream. Use the chart paths and hashes in the
  input inventory. The study's README lists the phase 1 package sources.
  `phase2/run_holdout.py` records the phase 2 chart repositories. Phase 3
  uses the same Loki, Traefik, and Vault sources and the Kong chart repository
  at `https://charts.konghq.com`. The historical kube-state-metrics 2.13.2
  chart was repackaged at the pinned commit, so its exact bytes are available
  in the original bundle.
- **N05** — The original crate URLs, versions, licenses, and checksums are in
  each cohort's `data/crates_manifest.json`. Place the archives under the
  corresponding `data/crates/` directories to run the archive-integrity
  tests. The collection commands in the study README also download official
  crates. Run regeneration in a separate checkout because it writes results.
- **N24** — The eight hosted runner artifacts, corrected aggregates, and
  experiment sources are included. The preliminary cross-study proposal
  files listed in the input inventory remain in the supplied N24 archive.

The original MIT license declaration is implemented by the repository's
[LICENSE](../LICENSE) for original research code. Upstream snapshots and
dependency materials remain subject to their original terms and attribution.

## Offline verification

Run each command in the indicated directory, using the Python version and
dependencies in the study guide. Some verifiers write a JSON report. Use a
disposable worktree when comparing their output with the archived files.

| Study directory | Check |
| --- | --- |
| `I01` | After restoring the inputs, run `python i01_industry/verify_industry.py` and `python i01_full/verify.py`. |
| `N02` | After restoring the charts, run `python scripts/verify_results.py`, `python phase2/verify_phase2.py`, and `python phase3/verify_phase3.py`. |
| `N04/base` | Install `requirements.txt`, then run `python -m unittest discover -s tests`. |
| `N04/expanded` | Run `python -m unittest discover -s tests` and, on POSIX, `python src/verify_frozen.py`. The original verifier uses native path separators to compare the POSIX checksum keys. |
| `N05` | After restoring the base crates, run `python -m unittest discover -s tests`. |
| `N06` | On Linux, install `requirements.txt` and run `python -m unittest discover -s tests`. Field capture uses the POSIX `resource` module. |
| `N08` | Run `python -m unittest discover -s tests`, `python -m unittest discover -s measurement -p 'test_*.py'`, and `python measurement/verify.py`. |
| `N21` | Copy the frozen `metadata/` JSON files into `runtime/metadata/`, then run `python validate_results.py`. The validator uses the runtime layout produced by the original prepare command. |
| `N22/addendum-20261118` | Run `python -m unittest discover -s tests` and `python code/verify_artifact.py`. The full replay starts from this directory in this repository. |
| `N24/source` | Run `python -m unittest discover -s n24_submission_experiments/tests`. The hosted SHA-256 inventory is in `N24_HOSTED_ARTIFACT_MANIFEST.md`. |

The frozen evidence preserves the study-level limitations. In particular,
controlled CI fault injection, simulated alert traces, public observational
signals, and model-assisted assessments each have the scope documented in
their study reports. An offline verification run confirms consistency of
archived evidence and results.
