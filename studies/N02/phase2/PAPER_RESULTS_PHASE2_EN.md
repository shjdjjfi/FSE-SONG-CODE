# Phase-2 Results Supplement: External Controls and Evidence Boundaries

This is a factual supplemental Results draft, **not a camera-ready FSE Industry claim**.

**Registered family holdout.** The CID implementation and threshold were
frozen before acquiring eight new chart-version pairs. Six were evaluated:
Grafana, ingress-nginx, metrics-server, Vault, Traefik, and external-dns.
Loki's default rendering failed; the preregistered sealed-secrets repository
was unavailable. In each evaluable chart family, twelve string-valued old
values were selected using an old-chart-only deterministic procedure. All 72
explicit values were present in their respective new-chart rendered manifests.
CID alerted on none. Accordingly, the observed false positive fraction was
0/72 but **positive-case sensitivity is undefined**, because the holdout
contains no silent value-loss cases. All 72 cases also preserved user-supplied
strings when the old defaults were manually merged before real Helm rendering.
These states represent six chart-family upgrade events, not 72 independent
upgrades.

**Native plugin against reconstructed storage.** We created properly encoded
Helm v3 Release Secret records using the original chart metadata/defaults,
explicit user Config and an actual old-chart-rendered manifest. A read-only
loopback Kubernetes-API stub exposed the Secrets to the **unmodified
helm-diff v3.12.0** plugin. The genuine plugin executed 27/27 upgrade diffs.
A second 27/27 run normalized manifests and used three lines of diff context.
Median diff lengths were 1,535 and 628 lines, respectively, and the concise
plugin call took a median of 0.521 s. These are tool output and machine time,
not empirically observed engineer-review minutes. The Secrets were synthetic,
not actual installed Kubernetes Releases.

**Not yet established.** The runtime environment had no container runtime,
kubectl, cgroup v2 mount or kubeconfig. No Pods or actual in-cluster upgrades
were executed, leaving Argo CD RBAC and service behavior, namespace-limited
kube-state-metrics, and Prometheus live targets unverified. An executable,
guarded disposable-cluster replay harness is supplied for these checks.
A randomized paired human-review timing protocol was also implemented, but
the observed number of participants and decisions is currently zero.
Therefore no evidence yet supports the prespecified >=15 percentage-point
recall advantage at equal human-review minutes relative to the complete
helm-diff-plus-official-documentation baseline. The 8/8 result from the
deliberately curated five-family development set remains exploratory.

