# Field-validation kit — N06 (not yet run on independent clusters)

**Purpose:** capture the specific observables needed to test identity churn on
**two different real Kubernetes systems**. Scripts do not install software,
change alerts, or inject faults. Running locally against synthetic inputs does
not count as field evaluation. A running, source-independent N06 exporter and
an isolated Prometheus/Alertmanager are prerequisites, not things silently
provided by these scripts.

## Inputs / permissions that are genuinely necessary

1. Two independent Kubernetes API servers, each with read-only access to
   namespace `kube-system` and list permission in the chosen application
   namespace for pods, ReplicaSets, Deployments, DaemonSets, StatefulSets and
   Events. Distinct `kube-system`
   namespace UID hashes should be recorded in each project manifest.
2. A running native Prometheus instance or Prometheus `promtool`, the included
   **experimental** `owner_exporter.py` (or a production-equivalent validated
   informer) producing `n06_owner_unavailable`, and the **actual** strong
   baseline rules (not their paper-only proxies).
3. An independently probed HTTP endpoint for the service. The probe must
   represent end-user availability and not merely restate pod readiness.
4. A genuine deploy/failure/recovery sequence with independent operator
   annotations and at least one same-owner replacement and one healthy
   rollout per system. Use naturally occurring events if injection is not
   approved. **Never run disruptive injections on production by default.**
5. Consent/authorization for log processing; Alertmanager webhook forwarding
   to an **isolated** receiver and export of test pager-provider delivery logs.

The collection path is read-only. It can create high-cardinality snapshots or
expose service names/labels; review it before capture, secure the output,
and do not publish real cluster logs without an access and privacy review.

An optional minimally executable N06 owner-continuity exporter is included:

```bash
python3 field_capture/owner_exporter.py \
  --context CONTEXT_A --namespace shop --deployment cart --service cart \
  --probe-url https://SERVICE_A/health --port 19100
```

Its `/metrics` endpoint is loopback-only. In an **isolated** Prometheus with
`job_name: n06-relink`, configure a scrape of `127.0.0.1:19100` and load
`promtool/alert_rules.yml`. This prototype uses repeated read-only API
snapshots, not production-grade Kubernetes informers; its measured expense
includes the kubectl subprocesses. The exact service→Deployment association
is an explicit operator hypothesis that must be checked against live routing.
No actual cluster execution has occurred here. Do not alter production alerts
without a separate change review.

## 1. Install and verify

In the package root:

```bash
python3 -m pip install -r requirements.txt
python3 -m unittest discover -s tests -v
kubectl --context CONTEXT_A -n shop auth can-i list pods
kubectl --context CONTEXT_B -n shop auth can-i list pods
```

The script collects Kubernetes owner references as `uid` rather than relying
on reused names. It records Prometheus vector sample timestamps, independent
probe responses and the collection overhead per tick. Environment variables,
Kubernetes annotations, object specs, and Event messages are NOT exported by
`collector.py`.

## 2. Collect each independent system without modifying it

Use separate outputs; the service probe must be reachable from the machine
running the collector. The URL is stored only as a SHA-256 digest in the
manifest. Example: run for one hour (a longer trace with multiple real incidents
is necessary for meaningful confidence intervals).

```bash
python3 field_capture/collector.py \
  --context CONTEXT_A --namespace shop \
  --prometheus-url http://127.0.0.1:9090 \
  --probe-url https://SERVICE_A/health \
  --queries field_capture/queries.example.json \
  --out field_data/system_A --seconds 3600 --interval 15

python3 field_capture/collector.py \
  --context CONTEXT_B --namespace shop \
  --prometheus-url http://127.0.0.1:9091 \
  --probe-url https://SERVICE_B/health \
  --queries field_capture/queries.example.json \
  --out field_data/system_B --seconds 3600 --interval 15
```

`queries.example.json` includes the candidate metric query, but the collector
itself does not create `n06_owner_unavailable`. Run the separate experimental
exporter (or production equivalent) and arrange native Prometheus to scrape it
under `job_name: n06-relink`. Missing series must remain missing in the raw
record and block native field export.

For each incident, supply a separate `operator_incidents.jsonl`, with one
original independently corroborated entry per line, for example the following
schema (illustrative ONLY, not a recorded incident):

```json
{"incident_id":"ticket-001","cluster_id":"SHA256_OF_REAL_KUBE_SYSTEM_UID","namespace":"shop","service":"cart","owner_uid":"REAL_DEPLOYMENT_UID","start":"2026-11-15T01:00:00Z","end":"2026-11-15T01:20:00Z","origin":"operator_confirmed","source_url_or_ticket":"INTERNAL_APPROVED_TICKET_ID","annotator":"verified-human-reviewer"}
```

Outage labels should come from operator evidence and independent requests,
not from matching N06's own alert expression.

## 3. Observe actual Alertmanager webhook arrival

Launch *separate* local receivers for candidate and strong baselines; isolate
the test Alertmanager from live paging routes. Set the cluster ID to the
collector's recorded `cluster_uid_sha256` (from `manifest.json`).

```bash
python3 field_capture/alert_receiver.py \
  --cluster-id CLUSTER_UID_SHA256 --policy n06 \
  --port 19093 --out field_data/system_A/n06_webhooks.jsonl

python3 field_capture/alert_receiver.py \
  --cluster-id CLUSTER_UID_SHA256 --policy nextdoor_deployment \
  --port 19094 --out field_data/system_A/nextdoor_webhooks.jsonl
```

Point the **isolated** Alertmanager webhook receiver at
`http://127.0.0.1:19093/alertmanager`. If forwarding from another host, put
the local endpoint behind an authenticated reverse proxy; the script refuses
non-loopback binding without `--bearer-env`. `received_at` records the actual
receipt wall clock, not the earlier rule `startsAt` timestamp. A webhook is
only a first hop; obtain the provider's authenticated delivered-to-oncall
receipt separately before claiming a human notification time.

Provider receipt JSONL fields required for true delivery analysis:

```json
{"delivery_provider_id":"REAL_PROVIDER_EVENT_ID","cluster_id":"SHA256_OF_REAL_KUBE_SYSTEM_UID","policy":"n06","status":"firing","delivered_at":"2026-11-15T01:11:30Z","labels":{"namespace":"shop","service":"cart","owner_uid":"REAL_DEPLOYMENT_UID"}}
```

All metric and paging clocks must be synchronized and their drift recorded.
Otherwise, even a genuine first-hop measurement cannot support subminute
time comparisons.

## 4. Native Prometheus tests on real captured series

The package includes hand-authored and synthetic `promtool` tests. Only the
actual official native binary can run these tests. On a machine with it:

```bash
python3 field_capture/native_evidence.py --out results_field/native_real_machine
```

To replay **genuine owner metric samples** in the official engine after an
independent operator has annotated incidents:

```bash
python3 field_capture/export_real_cases.py \
  --capture field_data/system_A/capture.jsonl \
  --incidents field_data/system_A/operator_incidents.jsonl \
  --manifest field_data/system_A/manifest.json \
  --out promtool/real_A_cases.yml

python3 field_capture/native_evidence.py \
  --field-cases promtool/real_A_cases.yml \
  --out field_data/system_A/native_evidence
```

Use the same approach separately for system B. A failed assertion against
independently labeled real failure **must not be removed**. Source hashes and
native stdout hashes are saved. This exercises the official rule engine on
series derived from real captured samples. It does not replace a separate
live Prometheus + Alertmanager comparison under realistic traffic.

On GitHub, `.github/workflows/n06-native-promtool.yml` runs native tests in
the official `prom/prometheus:v3.16.0` image when an authorized maintainer
uploads the source into a repository and triggers it. The workflow's existence
is **not** a passing native result.

## 5. Actual live-process overhead

Run alongside the deployed candidate and baseline PIDs separately, both under
the same traffic and sampling conditions:

```bash
python3 field_capture/process_cost.py --pid N06_PID \
  --cluster-id CLUSTER_UID_SHA256 --policy n06 \
  --out field_data/system_A/production_process_cost.jsonl --seconds 3600

python3 field_capture/process_cost.py --pid BASELINE_PID \
  --cluster-id CLUSTER_UID_SHA256 --policy nextdoor_deployment \
  --out field_data/system_A/production_process_cost.jsonl --seconds 3600
```

If the strong baseline is purely PromQL without a separate process, compare
the Prometheus process's rule evaluation CPU/latency/cardinality under equal
workloads and provide matching provider metrics. **Do not attribute all
Prometheus RSS to one rule.** The included process sampler alone cannot make
a meaningful incremental-cost claim for an embedded recording rule.

## 6. Field eligibility and matched outcome metrics

Configure a copy of `bundle.example.json` with real paths for both clusters.
Paths are relative to the bundle file. For each project the gate requires:

- 1h and 120 recorded samples, UID-verified stable ownership with 2+ Pod UIDs,
  corresponding lifecycle events, actual independent probes, raw Prom vectors;
- independently sourced outage labels and an incident-window failed probe;
- N06 and published owner-baseline webhook arrivals, authentic paging-provider
  receipts for both, native real-series test pass, and observed CPU/RSS costs.

```bash
python3 field_capture/audit.py \
  --bundle field_data/bundle.json \
  --out field_data/field_gate.json

python3 field_capture/analyze_delivery.py \
  --bundle field_data/bundle.json \
  --out field_data/delivery_comparison.json
```

The gate is intentionally fail-closed, and then requires a final manual audit
of source authenticity and outage causality. Analysis reports per-project
missed incidents, first actually delivered on-call page delays, repeat and
false pages per 24h, premature resolutions, recovery delays, and per-process
CPU/RSS, with explicit separation between webhook arrival and provider receipt.

## 7. What these scripts **do not** achieve by themselves

They do not provide two accessible independent clusters, a tested production
N06 exporter, a real fault/rollout, authentic incident ground truth,
native `promtool` installed on this execution machine, delivered on-call
receipts, or SRE economic impact. Without those external inputs, the 4 real
experiment requirements remain open. See `paper/NEW_FIELD_EVIDENCE_AUDIT.md`.
