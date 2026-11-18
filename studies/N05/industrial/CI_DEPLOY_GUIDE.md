# Optional non-blocking CI integration — not an observed production deployment

Run the included `consumer_gate.py` against a **published** crate, not source
from an uncommitted working tree. The release archive and Cargo diagnostics are
recorded. A single external consumer crate is used to compile each selected
snippet under default and documentation feature configurations. Missing flags
are searched with eight additional checks; all artifacts are kept locally.

## Standalone

Prerequisites: Python 3.10+, Rust/Cargo 1.91.0, network access to crates.io.

```bash
python3 industrial/consumer_gate.py --crate tower-http --version 0.6.6 --limit 12
```

## GitHub Actions

`industrial/github_actions_gate.yml` is an advisory workflow template. Move it
to `.github/workflows/consumer-examples.yml` in a repository **you control**,
after reviewing the permissions and minutes/usage costs. Trigger it manually
with package and version inputs. It will not fail the build on an automatically
detected mismatch, because a documentation page may already disclose the
required feature. No modification to any upstream repository or Actions
deployment is represented by this release package.

### Evidence necessary for independent industrial ROI

Before claiming an empirical reduction in CI failures/developer time, obtain
at least two independently operated projects that integrate the gate and share
timestamped real job records. Use a preregistered comparator that compiles the
same release/docs examples with native Rustdoc and feature-power-set tooling.
Measure true-positive developer-confirmed actionable defects, false positives,
developer triage minutes, incremental CI runner minutes, and time-to-repair
across the same released versions. An advisory workflow template and local
counterfactual checks are not substitutes for that deployment evidence.
