"""Fail-closed audit of independent cluster telemetry and alert deliveries.

The audit detects evidence shape, coverage and elementary temporal joins.
It does NOT certify authenticity, causal attribution or human delivery; those
must be checked against independent source records and paging-provider receipts.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


def parse_time(s: str) -> float:
    if not isinstance(s, str) or not s:
        raise ValueError("empty timestamp")
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc).timestamp()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def path_at(base: Path, filename: str) -> Path:
    path = Path(filename)
    return path if path.is_absolute() else base / path


def probe_failure_in_window(probe: dict[str, Any], start: float, end: float) -> bool:
    try:
        return (probe.get("unavailable") is True and
                start <= parse_time(probe["observed_at"]) <= end)
    except (ValueError, KeyError, TypeError):
        return False


def get_owner_uid(pod: dict[str, Any], objects: list[dict[str, Any]]) -> str | None:
    """Resolve direct owner or Pod->ReplicaSet->Deployment, retaining UIDs."""
    by_uid = {x.get("uid"): x for x in objects if x.get("uid")}
    refs = pod.get("owner_references", [])
    controller = next((x for x in refs if x.get("controller")), refs[0] if refs else None)
    if controller is None or not controller.get("uid"):
        return None
    if controller.get("kind") != "ReplicaSet":
        return controller["uid"]
    replica = by_uid.get(controller["uid"])
    if replica is None:
        return None
    parents = replica.get("owner_references", [])
    deployment = next((x for x in parents if x.get("kind") == "Deployment" and x.get("uid")), None)
    return deployment["uid"] if deployment else controller["uid"]


def audit_project(project: dict[str, Any], base: Path,
                  *, min_duration: float = 3600, min_samples: int = 120) -> dict[str, Any]:
    errors: list[str] = []
    name = project.get("name") or "unnamed"
    evidence: dict[str, Any] = {"project": name, "status": "BLOCKED", "errors": errors}

    def load_json(key: str) -> dict[str, Any] | None:
        try:
            return json.loads(path_at(base, project[key]).read_text(encoding="utf-8"))
        except (KeyError, OSError, ValueError, TypeError) as exc:
            errors.append(f"{key}: missing or invalid ({type(exc).__name__})")
            return None

    def load_jsonl(key: str) -> list[dict[str, Any]]:
        try:
            return read_jsonl(path_at(base, project[key]))
        except (KeyError, OSError, ValueError, TypeError) as exc:
            errors.append(f"{key}: missing or invalid ({type(exc).__name__})")
            return []

    manifest = load_json("manifest")
    snapshots = load_jsonl("capture")
    incidents = load_jsonl("incidents")
    cluster_id = manifest.get("cluster_uid_sha256") if manifest else None
    evidence["cluster_uid_sha256"] = cluster_id
    if not cluster_id or len(str(cluster_id)) != 64:
        errors.append("missing stable kube-system namespace UID hash")
    if not manifest or manifest.get("real_capture") is not True:
        errors.append("missing authentic collector manifest")
    snaps = [x for x in snapshots if x.get("kind") == "snapshot"]
    if len(snaps) < min_samples:
        errors.append(f"only {len(snaps)} snapshots (minimum {min_samples})")
    if any(x.get("cluster_id") != cluster_id or x.get("real_capture") is not True for x in snaps):
        errors.append("inconsistent cluster identity or capture provenance")
    times: list[float] = []
    for x in snaps:
        try:
            times.append(parse_time(x["captured_at"]))
        except (ValueError, KeyError, TypeError):
            errors.append("snapshot with missing or invalid timestamp")
    span = max(times) - min(times) if times else 0
    evidence["capture_duration_seconds"] = round(span, 3)
    if span < min_duration:
        errors.append(f"only {span:.1f} s of field capture (minimum {min_duration})")
    vectors_ok = sum(bool(x.get("prometheus_vectors")) for x in snaps)
    probes_ok = [x.get("probe", {}) for x in snaps if isinstance(x.get("probe"), dict)]
    if len(probes_ok) < min_samples or not any(p.get("unavailable") is True for p in probes_ok):
        errors.append("missing contemporaneous failed independent black-box probes")
    if not any(p.get("unavailable") is False for p in probes_ok):
        errors.append("missing healthy independent black-box probe controls")
    if vectors_ok < min_samples:
        errors.append("incomplete raw Prometheus instant-vector observations")

    owner_pods: dict[str, set[str]] = defaultdict(set)
    owner_events: set[str] = set()
    tracked_object_uids: set[str] = set()
    for snap in snaps:
        objects = snap.get("objects", [])
        if not isinstance(objects, list):
            errors.append("non-list Kubernetes objects")
            continue
        all_owners = {x["uid"] for x in objects if x.get("kind") in
                      {"Deployment", "StatefulSet", "DaemonSet"} and x.get("uid")}
        tracked_object_uids.update(x["uid"] for x in objects if x.get("kind") in
                                   {"Deployment", "StatefulSet", "DaemonSet", "ReplicaSet", "Pod"}
                                   and x.get("uid"))
        for obj in objects:
            if obj.get("kind") == "Pod" and obj.get("uid"):
                uid = get_owner_uid(obj, objects)
                if uid and uid in all_owners:
                    owner_pods[uid].add(obj["uid"])
            if obj.get("kind") == "Event" and obj.get("event_reason") in {
                    "ScalingReplicaSet", "SuccessfulCreate", "SuccessfulDelete", "Killing", "Started"}:
                event_uid = (obj.get("related") or {}).get("uid")
                if event_uid:
                    owner_events.add(event_uid)
    churn_owners = {owner for owner, pods in owner_pods.items() if len(pods) >= 2}
    evidence["churn_owner_count"] = len(churn_owners)
    evidence["pod_uid_count"] = sum(len(pods) for pods in owner_pods.values())
    if not churn_owners:
        errors.append("no observed real Pod-UID rotation under a stable owner UID")
    if not owner_events.intersection(tracked_object_uids):
        errors.append("no corresponding Kubernetes lifecycle/rollout event evidence")

    incident_intervals: list[tuple[float, float, dict[str, Any]]] = []
    for incident in incidents:
        try:
            a, b = parse_time(incident["start"]), parse_time(incident["end"])
            if b <= a:
                raise ValueError("non-positive incident duration")
            if incident.get("cluster_id") != cluster_id:
                errors.append("incident owner/project identity does not match capture")
            if incident.get("origin") not in {"operator_confirmed", "public_postmortem"}:
                errors.append("incident is not backed by a real independent operator/postmortem label")
            if not incident.get("source_url_or_ticket") or not incident.get("annotator"):
                errors.append("incident lacks independent reference and annotator")
            if incident.get("owner_uid") not in churn_owners:
                errors.append("incident not linked to a real observed rotating owner")
            incident_intervals.append((a, b, incident))
        except (KeyError, ValueError, TypeError):
            errors.append("incident has malformed start/end timestamps")
    evidence["independently_labeled_incidents"] = len(incident_intervals)
    if not incident_intervals:
        errors.append("no independently labeled real incident intervals")
    if incident_intervals and not any(
            probe_failure_in_window(p, a, b) for a, b, _ in incident_intervals for p in probes_ok):
        errors.append("real outage labels not corroborated by failed probes in their windows")

    delivered: dict[str, list[dict[str, Any]]] = {}
    for entry in project.get("deliveries", []):
        policy = entry.get("policy")
        try:
            delivered[policy] = read_jsonl(path_at(base, entry["path"]))
        except (OSError, KeyError, ValueError, TypeError):
            errors.append(f"missing Alertmanager receipt file for {policy}")
    if not delivered.get("n06"):
        errors.append("missing delivered N06 webhook receipts")
    strong = {"nextdoor_deployment", "kube_mixin_lookback"}
    if not any(delivered.get(x) for x in strong):
        errors.append("missing matched delivered strong Deployment-owner baseline receipts")
    evidence["first_hop_webhook_counts"] = {k: len(v) for k, v in delivered.items()}
    for policy, rows in delivered.items():
        for row in rows:
            if row.get("cluster_id") != cluster_id or row.get("policy") != policy:
                errors.append("Alertmanager receipt cluster/policy mismatch")
            if row.get("delivery_hop") != "alertmanager_to_test_webhook":
                errors.append("receipt is not a genuine webhook-receiver record")
            try:
                parse_time(row["received_at"])
            except (KeyError, TypeError, ValueError):
                errors.append("webhook missing actual arrival timestamp")
    # The first-hop webhook timestamp does not constitute a delivered on-call page.
    if not project.get("pager_receipts"):
        errors.append("missing authenticated external paging-provider delivery receipts")
    else:
        pager_rows = load_jsonl("pager_receipts")
        if not pager_rows:
            errors.append("empty on-call provider delivery receipts")
        pager_policies = set()
        for row in pager_rows:
            try:
                parse_time(row["delivered_at"])
                if not row.get("delivery_provider_id") or row.get("cluster_id") != cluster_id:
                    errors.append("provider receipt missing delivery ID or mismatched cluster")
                if row.get("status") not in {"firing", "resolved"}:
                    errors.append("provider receipt lacks firing/resolved status")
                pager_policies.add(row.get("policy"))
            except (ValueError, KeyError, TypeError):
                errors.append("invalid pager-provider receipt timestamp")
        if not {"n06", "nextdoor_deployment"}.issubset(pager_policies):
            errors.append("provider receipts missing matched candidate and published-owner baseline")

    native = load_json("native_replay")
    if not native or not (native.get("engine") == "Prometheus" and
                          native.get("exit_code") == 0 and native.get("real_project_samples") is True and
                          native.get("cluster_uid_sha256") == cluster_id and
                          native.get("stdout_sha256") and native.get("engine_version")):
        errors.append("missing successful native engine replay on this project's REAL recorded samples")
    cost_rows = load_jsonl("production_cost")
    cost_policies = {x.get("policy") for x in cost_rows if x.get("collector_kind") == "live_process"
                     and isinstance(x.get("cpu_seconds_per_interval"), (int, float))
                     and isinstance(x.get("resident_memory_mb"), (int, float))
                     and x.get("cluster_id") == cluster_id}
    if not {"n06", "nextdoor_deployment"}.issubset(cost_policies):
        errors.append("missing actual live-process CPU/RSS measurements for candidate and owner baseline")
    evidence["live_cost_sample_count"] = len(cost_rows)
    if errors:
        evidence["errors"] = sorted(set(errors))
    else:
        evidence["status"] = "EVIDENCE_SHAPE_PASS__MANUAL_AUTHENTICITY_REVIEW_REQUIRED"
    return evidence


def audit_bundle(config: dict[str, Any], base: Path,
                 *, min_duration: float = 3600, min_samples: int = 120) -> dict[str, Any]:
    projects = [audit_project(p, base, min_duration=min_duration,
                              min_samples=min_samples) for p in config.get("projects", [])]
    ids = [p.get("cluster_uid_sha256") for p in projects if p.get("cluster_uid_sha256")]
    independent = len(projects) >= 2 and len(ids) == len(projects) and len(set(ids)) == len(ids)
    complete = independent and all(p["status"].startswith("EVIDENCE_SHAPE_PASS") for p in projects)
    return {"status": "NEEDS_MANUAL_FIELD_REVIEW" if complete else "BLOCKED",
            "independent_cluster_identities": independent,
            "number_of_projects": len(projects), "project_evidence": projects,
            "manual_review_required": True,
            "manual_review_reason": "Data authenticity, trace-source independence, outage causality and human page delivery cannot be proven from JSON assertions alone."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    config = json.loads(args.bundle.read_text(encoding="utf-8"))
    report = audit_bundle(config, args.bundle.parent)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"],
                      "independent_cluster_identities": report["independent_cluster_identities"],
                      "out": str(args.out)}))
    return 0 if report["status"] == "NEEDS_MANUAL_FIELD_REVIEW" else 2


if __name__ == "__main__":
    raise SystemExit(main())
