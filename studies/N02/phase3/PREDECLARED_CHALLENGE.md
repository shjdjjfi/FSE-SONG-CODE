# N02 Phase 3: external positive-enriched challenge (predeclared before new renders)

Date: 2026-11-15 Asia/Shanghai. This is a **documentation-informed,
positive-enriched** test. Researchers consulted upstream migration notes first.
It must NOT be described as a random or outcome-blind sample of upgrade
incidents. Loki and Vault existed in the previous family-negative cohort;
the version transitions and positive-intent contracts below are new to CID's
original five-family development cohort.

## Frozen method and inclusion/labels

- CID scorer is exactly ../scripts/run_study.py at SHA-256
  64381bae392d703b7fbc20159dbaa02cf9cb6591412eb8249e6bf1f55fbf2b2e.
- No threshold tuning: 5.0; identical feature weights; no model training.
- The oracle is the specified old/new/migrated **rendered manifest/application
  configuration** field, not CID score or a source key name.
- Count as a positive ONLY if old Helm successfully renders and satisfies the
  contract, unmodified user values with new Helm successfully render and FAIL
  it, and a prespecified migrated/new-version override recovers it.
- Count old/new render failures or a failed repair separately, even when
  this invalidates a hoped-for positive. No selective deletion.
- The upstream migration guide can inform the candidate (by design);
  the comparator therefore MUST include the guide in the baseline, and a
  documented positive alone cannot prove superiority.
- Real runtime and real production incidents are out of scope for this phase.

## Source-pinned upgrade families and candidate contracts

### Grafana Loki 5.47.2 -> 6.0.0

Charts already archived. Both arms use the SAME testing-only context
{loki: {useTestSchema: true}}, which is not a real storage deployment.
Official upgrade source:
https://grafana.com/docs/loki/latest/setup/upgrade/upgrade-to-6x/

- L01: Old monitoring.lokiCanary.enabled=false should omit Canary DaemonSet;
  new old-key reuse should keep it omitted; proposed repair:
  lokiCanary.enabled=false. Native behavior check requires a deployed Loki.
- L02: Old monitoring.lokiCanary.labelname=<unique string> should preserve
  that canary CLI flag or other output representation; repair:
  lokiCanary.labelname=<same string>.
- L03: Old monitoring.lokiCanary.image.repository=<unique repository>
  should preserve the canary image registry/repo; repair:
  lokiCanary.image.repository=<same repository>.
- L04: Old loki.externalConfigSecretName=<unique name> should continue to
  be referenced by config volume; repair: loki.configObjectName=<same name>.

### Kong Kong 2.1.0 -> 2.2.0

Official upgrade source:
https://github.com/Kong/charts/blob/main/charts/kong/UPGRADE.md

- G01: Old podDisruptionBudget.enabled=true inherits old maxUnavailable=50%;
  the new deployment should preserve explicit old behavior. Proposed repair:
  explicitly set podDisruptionBudget.maxUnavailable="50%". PDB object fields
  are the only ground truth for this scenario.
- G02 negative: Config unchanged with podDisruptionBudget.enabled=false;
  PDB remains absent under both old and new.

### HashiCorp Vault 0.25.0 -> 0.26.0

Official regression/fix in Vault Helm CHANGELOG:
https://github.com/hashicorp/vault-helm/blob/main/CHANGELOG.md

- V01: server.ha.enabled=true and server.ha.replicas=2 should keep the
  StatefulSet replica count 2. Chart 0.26.0 is reported to ignore file-based
  overrides in this setting; 0.26.1 provides a repaired target chart. This is
  a chart regression, not necessarily a values-key migration.
- V02 negative: server.ha.replicas left at old default=3; contract is 3.

### HashiCorp Vault 0.28.1 -> 0.29.0

- V03: templated server configuration should be resolved in old chart and may
  fail in 0.29.0 according to official GH-1072. Independent oracle is an
  old-rendered templated value becoming unresolved literal; 0.29.1 is a
  repaired target. Exclude if actual charts or output do not support it.

### Traefik 24.0.0 -> 25.0.0 (a negative-control challenge)

- T01: old experimental.kubernetesGateway.gateway.enabled=true produced no
  Gateway in the initial old-only diagnostic, so it must not become a positive
  merely because the key is missing in new values. Include as a known
  old-version no-effect control.

## Causal interpretation and stop conditions

Positive contracts from Loki, Kong and Vault would demonstrate manifest-level
out-of-family coverage on deliberately sought breaks. Real failure and real
operator intent still need Kubernetes/production validation.

Apply the *unchanged* CID score, missing-new-default, manifest-diff magnitude,
and official-docs indicator to every evaluable scenario. Report sensitivity
and false positives with correct event/family denominators. Do not claim
>=15 pp over docs+native-diff absent actual reviewers or strong comparator
decisions. An AI role-playing a reviewer is explicitly not a human subject.
