# N02 Phase 2: pre-registered out-of-family probe

Frozen before fetching or inspecting any of the Phase-2 chart archives. Date:
2026-11-15 (Asia/Shanghai). This is a **manifest-intent-preservation** test,
not a Kubernetes runtime/production-failure study.

## Fixed method

- CID is exactly `../scripts/run_study.py` at SHA-256
  `64381bae392d703b7fbc20159dbaa02cf9cb6591412eb8249e6bf1f55fbf2b2e`.
- Do not train, modify, or tune the original CID or its threshold (score >= 5).
- Primary comparator: user-value-literal preservation and a direct changed-resource
  magnitude; secondary comparator: fixed missing-key-in-new-values signal.
- Random source seed: `20261115`.
- Do not replace unavailable chart pairs with more favorable examples.
- Never treat absence of a new-chart value string as proof of outage: it is
  a narrower, specified manifest-preservation contract failure.
- New families are assessed independently; ties and within-family configuration
  interventions are not independent installations.

## Prespecified collection mechanism

The eight external chart families and versions below were chosen before any
Phase-2 chart download. In each old `values.yaml`, enumerate scalar string
leaves, excluding secret-bearing path names and empty values. Deterministically
sort these candidates by SHA-256 of `<seed>/<family>/<path>`.

For each path in that order, insert a unique `n02-<hex>-probe` sentinel, with
simple syntax-aware replacements for URLs, domains, image registries and
storage classes. Keep the first 12 successful old-version render experiments
**whose exact sentinel occurs in the generated YAML**. Record attempted,
rejected and unavailable inputs; cap at 150 attempts per family. No result
of the new-version render may influence inclusion.

For every retained state, render the new chart with the **same** explicit
values, plus old/new default charts. Primary outcome is whether the exact
operator-supplied sentinel survives in the new manifest. Secondary: CID
selection using frozen old-versus-new counterfactual scores. This tests a
specific and limited expectation (preservation of explicit output values),
not native application behavior.

No chart family is in the 5-family discovery cohort. A positive label is
assigned mechanically from sentinel disappearance, never from CID itself.
The 12-state cap and 150-attempt cap are fixed before data retrieval.

## Holdout chart family/version registry

| Family | Chart | Old -> new | Repository |
|---|---|---|---|
| grafana | grafana | 7.3.12 -> 8.0.0 | https://grafana.github.io/helm-charts |
| ingress-nginx | ingress-nginx | 4.10.0 -> 4.11.0 | https://kubernetes.github.io/ingress-nginx |
| metrics-server | metrics-server | 3.11.0 -> 3.12.0 | https://kubernetes-sigs.github.io/metrics-server |
| vault | vault | 0.27.0 -> 0.28.0 | https://helm.releases.hashicorp.com |
| traefik | traefik | 24.0.0 -> 25.0.0 | https://traefik.github.io/charts |
| loki | loki | 5.47.2 -> 6.0.0 | https://grafana.github.io/helm-charts |
| external-dns | external-dns | 1.14.4 -> 1.15.0 | https://kubernetes-sigs.github.io/external-dns |
| sealed-secrets | sealed-secrets | 2.14.2 -> 2.15.0 | https://bitnami-labs.github.io/sealed-secrets |

## Statistical unit and stop rule

Report every chart family, including failures/unavailable and zero-positive
families. Report exact numerator and denominator, no "100%" where denominator
is zero, and bootstrap only at chart-family level. This cannot substantiate the
original >=15 pp vs **helm-diff + documentation at equal human minutes** goal,
which requires separate live-cluster and human-subject experiments.

