# I01 industrial follow-up: frozen real-repository CPU evaluation

Study date: 2026-11-14. This protocol and fixed case list precede this
follow-up's resolver/install/test outcomes. It does not replace the preceding
1,440-condition preregistered wheel-resolution experiment.

## Primary questions

1. For **real publicly maintained consumer repositories**, does the repository's
   declared dependency constraint admit the first OSV-published fixed release?
   How does resolving the real **full declared requirement set** differ from
   resolving an isolated direct dependency?
2. When an upgrade is expressible, can an actual isolated CPU/Linux Python
   environment install prebuilt distribution wheels, and can selected existing
   project tests or source-level smoke checks execute? Distinguish resolution,
   installation, repository test execution, and test success.
3. Does the first upstream PyPI fixed release exhaust the remediation options?
   Analyze newer releases and **documented vendor security backports**.

## Fixed purposive case selection, before outcomes

Three target vulnerable-to-first-fixed transitions come directly from the
original 120-project OSV sample:

|Package|Original OSV advisory|Vulnerable comparison|First fixed release|
|---|---|---|---|
|python-jose|GHSA-cjwg-qfpm-7377|3.3.0|3.4.0|
|fastapi|PYSEC-2024-38|0.109.0|0.109.1|
|webob|PYSEC-2026-3943|1.8.10|1.8.11|

Seven independent public repository contexts, identified by their published
requirements, release announcements, or both. **Do not drop or replace cases
after seeing results**:

1. `openstack/skyline-apiserver`, `requirements.txt`: `python-jose<=3.3.0`.
2. `pyfa-org/Pyfa`, `requirements.txt`: `python-jose==3.3.0` (large desktop
   GUI application; inspect declared constraints without claiming full GUI CI).
3. `Tinkoff/overhave`, `pyproject.toml`: Poetry `python-jose = "^3.3.0"`
   (archived repository; not evidence of live production deployment).
4. `rainpaw/AI-NPC`, `requirements.txt`: `fastapi==0.109.0`.
5. `apache/allura`, `requirements.txt` plus `CHANGES`: upstream project
   records a `webob` upgrade from 1.8.10 to 1.8.11.
6. `pypiserver/pypiserver`, `pyproject.toml`, requirements/lock and `CHANGES`:
   published WebOb 1.8.10 → 1.8.11 migration.
7. `mozilla-services/pyramid_multiauth`, requirements/lock and CI workflow:
   public WebOb 1.8.10 → 1.8.11 update history.

All seven are cases regardless of whether a local reproduction proves feasible.
Repository default-branch commits and exact source files are frozen in a
machine-generated manifest **before** any follow-up `pip` experiment. A
requirement asserted by search but not present in the frozen source is reported
as *not verified at snapshot*, not retroactively reconstructed.

This sample is **purposeful, not random**: deliberately seeks hard upper
bounds, exact pins, compatible ranges, and prior visible remediation. It is
not suitable for extrapolating ecosystem-wide vulnerability prevalence.

## Test matrix and stopping policy

- Python: available native Python 3.12 on Linux x86-64, CPU only, no GPU,
  paid API, containers, elevated privilege, or large server.
- Version arms per applicable repo: `declared` (unchanged), `injected-first`
  (unchanged full declared constraints plus `package==first_fixed`),
  `replaced-first` (edit **only** the target direct constraint to first fixed),
  `replaced-latest` (edit only that constraint to highest final PyPI version
  on study date). For Poetry syntax, convert its explicit caret bound to PEP
  440, retaining other dependencies verbatim when possible. For migration-only
  repositories without an old constraint at HEAD, label the historical arm
  *historical evidence only*, never fabricate a synthetic old repo lock.
- Run pip `--dry-run --ignore-installed --only-binary=:all:` for the exact
  extracted project requirement file when syntactically supported; additionally
  run root-pair probes for each package to isolate direct incompatibility.
  Network/timeouts/invalid historical requirement formats are `unknown/error`,
  not `infeasible`. Store command, SHA, exit code, duration, excerpts.
- Real installation and tests: selected small repositories (`AI-NPC`,
  `pypiserver`, `pyramid_multiauth`) in separate ephemeral venvs, using
  prebuilt wheels and only local, safe, service-free tests. Try each studied
  first fixed vs alternative where one exists; compare any pre-fix baseline
  without executing exploit code. Keep per-test verdicts even when failure
  originates in project staleness / missing services. Do **not** claim full
  production CI or safe deployment.
- Only source-level code tests already shipped by the repository count as
  upstream project tests. New minimal integration smoke scripts are visibly
  marked `researcher_smoke`, never mislabeled as repository's existing tests.
- Time budget: cap each resolver/install subprocess at 60–120 seconds and
  each test subprocess at at most 120 seconds; abort individual very heavy
  dependency sets and retain the reason instead of downloading GPU frameworks
  or using external databases / remote credentials.

## Alternative fix and backport analysis

- Query fixed release, newest final PyPI release, OSV affected-range events,
  and published fix commits; verify both artifact availability and the original
  repository's constraint admission. A later release is *potentially patched
  for the specified advisory*, not automatically safe from every CVE.
- Distinguish upstream patched versions, explicitly OSV-listed maintenance
  branch fixes, downstream distro backports, and hypothetical source patches.
- For backports require primary vendor advisory with CVE, actual package
  version and fixed status. Such vendor-patched packages are **not** identical
  to upstream PyPI wheels. Evidence-only backports do not count as locally
  installed or CI-passing outcomes.
- Record open, unresolved, negative outcomes and provenance. No exploit
  payload generation or high-load security tests.

## Provenance and interpretation

Source raw snapshots, commit IDs and source-file hashes, pip package versions,
venv scripts, full command argv, status, durations and bounded logs will be
archived. No unstated cherry-picking, no fabricated CI green ticks, no
upgrading arbitrary other dependencies to make a comparison appear favorable.
Use the official FSE 2027 Industry CFP and existing HELP, PCREQ and VulnBump
as related work. This is a **bounded CPU industrial follow-up**, not a claim
of performing actual enterprise production remediation.
