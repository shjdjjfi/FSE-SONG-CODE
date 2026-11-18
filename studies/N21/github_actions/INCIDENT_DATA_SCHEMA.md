# Minimum evidence for a natural CI partial-output incident and denominator

Do not infer missing outputs from exit code, job status, cache hit status,
issue text or an absent artifact upload. The study must preserve an **output
integrity oracle**, a cache timeline, and the complete exposure population.

## Natural incident record (one row per eligible CI job)

- `repo_id` (stable pseudonym), `workflow_id`, `run_id`, `run_attempt`,
  `job_id`, `commit_sha`, `branch/ref`, `timestamp`, `runner_image`.
- `compiler_binary_sha256`, `compiler_version`, `node_version`, key
  environment inputs, lockfile digest, project graph/version.
- `cache_key`, `cache_hit`, `cache_restore_started_at`,
  `cache_restore_finished_at`, `cache_archive_bytes`, `restored_paths` and
  whether the complete trusted cache entry was available.
- All full stdout/stderr logs for **every attempt**, including the compiler
  command, exit code and complete `tsbuildinfo` path. Maintain the association
  between log, run, job, commit and cache key; remove secrets before sharing.
- `trusted_prior_output_manifest`: relative path + SHA-256 from a known-good
  build, with an input identity key; `post_restore_manifest` and
  `post_build_manifest` using the same exact path set, or an independent
  clean-build oracle on the same commit/lock/environment.
- `natural_incident`: true **only when the fault was observed without a
  researcher-injected deletion or corruption**, with investigator notes.
- `remediation` and re-run linkage, even when subsequent actions fixed it.

## Exposure denominator (one row per consecutive, pre-specified eligible run)

- Use a fixed time window and scope (one workflow, branch/event eligibility,
  project graph and caching condition) chosen **before** reading outcomes.
- Enumerate all attempts, including successful, failed, cancelled and timed
  out runs; explain exclusions and missing data explicitly.
- The relevant denominator is runs **with the risk condition and observable
  post-restore output verification**, not every repository workflow execution.
  Classify `verified_complete`, `verified_partial`, `cache_miss`,
  `not_exposed`, and `unknown_unobservable` separately.
- Compute `observed_partial / observable_at_risk` only if the classification
  is complete. Report the size of `unknown_unobservable`; do not silently
  count unknowns as successes or negatives.
- Collect repeated true job-level time/CPU/memory, cache transfer bytes,
  integrity scan I/O, false alarms, reruns and engineering interventions to
  estimate realized trade-offs; commercial costs require actual applicable
  runner rates and real incident/handling cost, not a guess.

## Privacy and permissions

Sanitize personal information, tokens, URLs with signed query credentials,
dependency registry secrets, and source code paths before sharing. Only share
CI logs and manifests you have the right to disclose. Access to organization
systems or production workflow changes must be explicitly authorized.

The currently archived 17 consecutive public Wireit jobs prove real runner
execution and dependency-cache activity, but no emitted-output manifest was
logged. All 17 must therefore remain `unknown_unobservable` for the N21
partial-restoration outcome; a 0/17 failure-rate claim is invalid.
