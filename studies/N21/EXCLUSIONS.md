# Audited exclusions / exploratory mistakes

The final analysis is compiled solely from the 920 unique records under
`results/**/trials.jsonl` and from the separately named supplementary JSONs.

1. The original `andrewthauer/web/delete_dts/standard` attempted trial could
   not inject a `.d.ts` file because that native project did not emit one.
   It generated `results/andrewthauer/errors.jsonl` (one failed, **not an
   observation**). The runner then explicitly skipped unsupported suffixes;
   the expected grid was derived from clean-oracle output paths.
2. The first TypeScript native-subgraph run mistakenly regarded
   `.tsbuildinfo` stored *inside* `outDir` as a deployable compiler output.
   The first 12 trial records were quarantined at
   `quarantined/typescript_before_buildinfo_filter.jsonl` (excluded from
   analysis). The manifest logic was corrected to omit `.tsbuildinfo` from
   deployable artifacts while still tracking build state separately, and
   **all TypeScript main trials were re-executed**. The re-executed grid is
   the 84 observations in `results/typescript/trials.jsonl`, plus 12 guarded
   runs, with a clean independent oracle.
3. An initial artificial Turborepo fixture omitted explicit task inputs, so
   changing output files changed the computed cache key and the run missed
   instead of hitting the cache. Preserved in
   `results/turborepo/misconfigured_outputs_in_inputs.json`, **not used** in
   the properly configured available-cache 4/4 comparator. After fixing the
   task inputs and declared outputs, the eight final tool observations were
   collected in `results/turborepo/observations.json`.
4. The first *actual* GitHub Actions Attest comparison, remote run
   [44237397496](https://github.com/shjdjjfi/FSE-EXP-1/actions/runs/44237397496),
   mistakenly included generated `.d.ts` outputs when fingerprinting source
   inputs. Hence an output corruption could be misclassified as input drift
   and force a full rebuild, invalidating that pilot's selective-repair
   timing even though its SHA oracle verified final outputs. All 15 raw
   artifacts are preserved under
   `results/github_actions_run_44237397496/`; the audit explanation is in
   `EXCLUDED_PILOT.md`. After restricting inputs to explicit source/config
   paths, **three independent complete hosted matrices** (45 runner jobs,
   42 per-strategy records) were rerun and independently audited. No pilot
   timing is included in `results/github_actions_aggregate.*`.

These notes distinguish experimental setup debugging from reproducible
research-fault outcomes. No excluded observation is silently recoded as a
successful experiment; the main paper table contains only the audited grid.
