# Audit / protocol correction log, 2026-11-14

All deviations below are disclosed. The frozen `PREREGISTRATION.md` and
OSV sample remain unchanged; no projects are excluded because of an outcome.

## D1: macOS minor-version target mismatch (detected during first solver pass)

Pre-registration explicitly specified **macOS 11 arm64**, and `run.py` root
preflight correctly used `macosx_11_0_arm64` target tags. The first `uv` runner
pass used `--python-platform aarch64-apple-darwin` but omitted uv's
`MACOSX_DEPLOYMENT_TARGET` environment variable. According to the **uv official
CLI documentation**, its default target on macOS is **13.0**, not 11.0:
https://docs.astral.sh/uv/reference/cli/ . This was discovered by an
*apparent* root-gate false-negative on `scipy==1.8.0` for Python 3.8 and 3.10:
the available macOS-arm64 wheel is `macosx_12_0_arm64`, valid on macOS 13
but not 11. In the first-pass result, uv correctly found a solution for the
wrong (macOS 13) target.

**Correction:** Keep `uv_full.jsonl` as the **unaltered first-pass audit**;
run the **entire** macOS subset (all 120 projects × 4 Python versions = 480
cases) afresh in `uv_macos11.jsonl` with
`MACOSX_DEPLOYMENT_TARGET=11.0`. Use the corrected 480 macOS outcomes,
plus the original 960 Windows/Linux outcomes, for all primary analyses.
Publish the original/updated discrepancy count and every corrected case.
This is a simulator target-configuration correction and **not** an outcome-
dependent removal, metric-choice change, or attempt to improve a score.

The 1,440-case planned dataset stays constant; the original 480 macOS13
calls are additionally retained as sensitivity/audit evidence. No physical
macOS host is needed. `pip --platform macosx_11_0_arm64` provides an
independent version-specific wheel compatibility cross-check.

## D2: limitations known before full analysis

- uv `--python-platform` provides a best-effort target-platform resolution
  as documented at https://docs.astral.sh/uv/concepts/resolution/ .
- pip's cross-target environment markers may differ from uv's cross-target
  markers. Record disagreements instead of secretly choosing one answer.
- OSV event `fixed` values need not correspond to a published PyPI version.
  PyPI returned 404 for three sampled fixed versions; they remain in the
  sample and have explicit unavailable-metadata state.
- The special rule for yanked wheels excludes them from our policy. In this
  sample, **no** 120 selected versions contained yanked files; this rule
  therefore had no empirical effect.

## D3: documented resolver policy mismatch (found during full solver audit)

When inspecting first-pass `uv` results against fixed-release metadata, several
targets showed `uv` success despite a release `Requires-Python` **upper bound**
disallowing that target. These are *not* proof that the wheel is installable
under a strict interpreter specification. **uv intentionally ignores upper
bounds** in dependency resolution; see its official documentation:

- https://docs.astral.sh/uv/pip/compatibility/#requires-python-upper-bounds
- https://docs.astral.sh/uv/reference/internals/resolver/#requires-python

Examples include `streampipes==0.97.0` with `<3.12,>3.8.1` on Python 3.12
and `cg==60.2.12` with `<3.13,>=3.9` on Python 3.14. Independent pip
`--python-version` checks evaluate those declarations strictly.

**Supplemental falsification study added after observing this discrepancy:**
run a strict pip check **on every sampled target** in addition to the
preregistered 288 dual-mode checks. If root gate rejects a target, use
`pip --no-deps` to test the rejection independently; if pip confirms root
failure, infer full strict pip installability is false without needlessly
downloading transitive wheels. Otherwise invoke full pip. For all root-positive
or unknown targets, invoke full pip directly. All original `uv` outputs are
retained untouched. Store the exact per-target command, invoked or logically
implied status, and time in `pip_all.jsonl`.

Separate reported outcomes:

1. `uv` successful *resolution under its documented relaxed-upper-bound rule*.
2. `pip` successful wheel-only, target-constrained dry-run (strict Python
   upper bound; platform-dependent environment markers still approximate).
3. Unanimous success/failure and discordances. Never relabel `uv` cases or
   silently discard disagreements; never claim a semantic-constraint failure
   disproves the root-gate's strict-policy safety.

The extra pip study is explicitly **post-hoc methodological validation**, not
the preregistered primary outcome. It strengthens falsification coverage but
cannot retroactively turn these measurements into application-level CI tests.

## D4: cross-target pip environment markers are not a true target VM

The independent pip verifier's `--platform` and `--python-version` flags
constrain wheel selection and Python compatibility, but **do not uniformly
override the host's dependency environment-marker evaluation**. This issue
is documented by pip maintainers, including:

- https://github.com/pypa/pip/issues/11664
- https://github.com/pypa/pip/issues/12466

Thus even when pip strictly rejects an incompatible direct fixed release,
its **full transitive result on a foreign target OS or Python minor version
is a cross-target estimate**, not a true Windows/macOS/other-Python install.
Treat pip and uv agreement as stronger *tool-level* evidence, not definitive
runtime compatibility. The native Linux/Python 3.12 cell is closest to a
same-environment pip dry run; no installation, build or test occurred there.

The hard limit from this experiment is scientific, not cosmetic: without
actually running the target interpreter/OS (or controlling a standards-complete
cross-target marker resolver), we cannot claim to establish cross-platform
installability with a formally complete oracle. We will include that in the
paper-readiness verdict and suggest a VM validation study before submission.
