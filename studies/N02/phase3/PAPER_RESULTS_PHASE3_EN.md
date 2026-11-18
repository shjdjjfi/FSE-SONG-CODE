# Phase 3: Reporting-ready external challenge (with negative findings)

> **Study status:** Manifest-level, documentation-informed external challenge, NOT live Kubernetes deployment, real human-subject study, or production incident reconstruction. The unmodified CID scoring script had SHA-256 `64381bae392d703b7fbc20159dbaa02cf9cb6591412eb8249e6bf1f55fbf2b2e` (threshold 5.0).

## External historical Chart upgrades

We constructed a source-documented, positive-enriched challenge across Loki 5.47.2→6.0.0, Kong 2.1.0→2.2.0, Vault 0.25.0→0.26.0, Vault 0.28.1→0.29.0, and Traefik 24.0.0→25.0.0. Each alleged manifest-contract violation was tested on three actual released Chart packages/configurations: a historical original chart with operator values; the target chart with the unchanged operator values; and either a corrected operator-value mapping or a vendor-provided fixed Chart version. Of ten prespecified challenge states, six satisfied all three conditions, three preserved the specified behavior, and one was invalid due to a template-validation failure. Six manifest violations arose from three Chart families (three Loki cases, one Kong, two Vault). **These are not six independent production incidents.**

The frozen CID detector raised three of the six manifest-loss cases (50.0% sensitivity; Wilson 95% CI 18.8%–81.2%) with no false alarms on the three valid controls. The three misses were (i) a missing default PodDisruptionBudget constraint in Kong, (ii) a Vault HA replica-count regression, and (iii) a Vault configuration template-expansion regression. A simple missing-key baseline also retrieved 3/6 positives (0.0 pp recall advantage for CID) and flagged one of the three controls; CID did not flag that control. Combining the original 72 stability controls with these three controls yielded zero CID alerts over 75 negatively labeled configurations, but this highly selected corpus should not be used for population-level false-positive guarantees.

## Strong baseline and reviewer cost

We executed the genuine native helm-diff v3.12.0 code on correctly encoded synthetic historical Helm v3 Secret payloads via a loopback-only read-only Kubernetes API emulator. All nine evaluable trials completed and yielded 6,110 lines of normalized diffs. The relevant lost configuration field was visibly represented in the diff of **each** confirmed positive. In addition, official upstream release/upgrade notes supplied relevant migration or patch guidance for **all six** positives. This observation establishes **evidence availability**, not a measured human recognition rate. It particularly prevents claiming that CID detects previously unobservable failures missed by `helm-diff + official documentation` on these examples.

No real reviewer performed any trial and no user-level review durations were observed. The qualitative AI expert walk-through is explicitly non-human, unblinded, and excluded from human metrics. Human participants = 0; human minutes = not measured. Consequently, **the proposed ≥15 percentage-point improvement over the strongest industrial review baseline was not demonstrated**. Although a purely descriptive comparison of CID's 3/6 retrieval and the documents' 6/6 *availability* is −50 percentage points, these are different endpoints and cannot be treated as a measured accuracy difference between human review conditions.

## Supplementary automated discovery (exploratory, not pooled)

A separate documentation-independent screen enumerated old strings that disappeared from the new `values.yaml` schema for nine historical upgrade pairs. It logged all six eligible paths and found four preserved-in-old/lost-in-new sentinel probes. Two corresponded to previously validated Loki cases. Two post-screening verification cases with valid operator values confirmed a Canary DaemonSet `updateStrategy.type` contract (`OnDelete` → `RollingUpdate`, repaired to `OnDelete`) and an image registry contract (`quay.io` → `docker.io`, repaired to `quay.io`). Both are successfully signaled by CID. They are **exploratory and highly correlated with the same Loki upgrade**; they are intentionally excluded from the six-positive confirmatory denominator. The registry case only checks generated image references, not whether an image exists or starts.

## Threats to validity

1. Documentation-assisted, positive-enriched sampling and a small number of correlated upgrade events; cannot estimate overall prevalence or unbiased test sensitivity.
2. Test-only Loki schema setting, Helm template as the main oracle; no API-server validation, successful workload rollout, Pod health, or actual runtime effects.
3. Synthetic Helm Secret for authentic plugin execution; no native `helm install/upgrade` against a live cluster.
4. Chart-template regressions in Vault are not strictly value-key rename cases; report them as a separate subclass.
5. Absence of independently recruited, blind human operators makes time-saving and ≥15 pp incremental detection claims unsupported.

## Primary artifacts

- Full Mandarin report: `phase3/EXPERIMENT_REPORT_PHASE3_CN.md`
- Preregistered challenge: `phase3/PREDECLARED_CHALLENGE.md`
- Per-case oracle data: `phase3/results/challenge_cases.jsonl`
- Statistical audit: `phase3/results/challenge_statistical_audit.json`
- Native plugin transcripts: `phase3/results/helm_diff_transcripts/`
- Model desk review (non-human): `phase3/AI_EXPERT_DESK_AUDIT_CN.md`
- Blind schema sweep: `phase3/results/blind_schema_selection_all_attempts.jsonl`
- Post-screening validation: `phase3/results/exploratory_validated_discoveries.json`

All study scripts, chart-archive SHA-256 checksums and their exact versions are included in the corresponding reproduction archive.
