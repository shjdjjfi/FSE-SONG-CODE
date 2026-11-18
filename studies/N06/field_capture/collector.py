"""Capture authentic Kubernetes ownership, Prometheus vectors, and HTTP probes.

This program does not deploy, scale, kill, patch, or restart Kubernetes objects.
It cannot turn an existing public dataset into a real-world N06 validation.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import resource
import subprocess
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def owner_refs(obj: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"kind": x.get("kind"), "name": x.get("name"),
         "uid": x.get("uid"), "controller": bool(x.get("controller", False))}
        for x in obj.get("metadata", {}).get("ownerReferences", [])
    ]


def curate_objects(raw: dict[str, Any]) -> list[dict[str, Any]]:
    """Remove specs, container env, annotations, messages and other secrets."""
    allowed = {"Pod", "ReplicaSet", "Deployment", "StatefulSet", "DaemonSet", "Event"}
    output: list[dict[str, Any]] = []
    for item in raw.get("items", []):
        kind = item.get("kind", "")
        if kind not in allowed:
            continue
        meta = item.get("metadata", {})
        row: dict[str, Any] = {
            "kind": kind, "namespace": meta.get("namespace"),
            "name": meta.get("name"), "uid": meta.get("uid"),
            "created_at": meta.get("creationTimestamp"),
            "deleted_at": meta.get("deletionTimestamp"),
            "generation": meta.get("generation"),
            "owner_references": owner_refs(item),
        }
        if kind == "Pod":
            conditions = item.get("status", {}).get("conditions", [])
            row["ready"] = next(
                (c.get("status") == "True" for c in conditions if c.get("type") == "Ready"), None
            )
            row["phase"] = item.get("status", {}).get("phase")
        elif kind in {"Deployment", "StatefulSet", "DaemonSet", "ReplicaSet"}:
            status = item.get("status", {})
            row["ready_replicas"] = status.get("readyReplicas", 0)
            row["available_replicas"] = status.get("availableReplicas", 0)
            row["observed_generation"] = status.get("observedGeneration")
        elif kind == "Event":
            related = item.get("involvedObject") or item.get("regarding") or {}
            row["event_reason"] = item.get("reason")
            row["event_type"] = item.get("type")
            row["event_at"] = (item.get("eventTime") or item.get("lastTimestamp") or
                               item.get("firstTimestamp") or meta.get("creationTimestamp"))
            row["related"] = {k: related.get(k) for k in ("uid", "kind", "name", "namespace")}
        output.append(row)
    return output


def kubectl_json(context: str, args: list[str], timeout: float) -> dict[str, Any]:
    command = ["kubectl", "--context", context, *args, "-o", "json", "--request-timeout", f"{timeout:g}s"]
    proc = subprocess.run(command, capture_output=True, text=True, timeout=timeout + 8,
                          check=False)
    if proc.returncode:
        # kubectl error text may contain URLs/tokens; redact in logs.
        raise RuntimeError(f"kubectl command failed with exit status {proc.returncode}")
    return json.loads(proc.stdout)


def cluster_uid(context: str, timeout: float) -> str:
    obj = kubectl_json(context, ["get", "namespace", "kube-system"], timeout)
    uid = obj.get("metadata", {}).get("uid")
    if not uid or not isinstance(uid, str):
        raise RuntimeError("Cannot establish cluster identity from namespace kube-system UID")
    return uid


def prom_query(url: str, query: str, stamp: float, timeout: float,
               max_series: int = 20000) -> dict[str, Any]:
    endpoint = url.rstrip("/") + "/api/v1/query?" + urlencode({"query": query, "time": stamp})
    before = utc_now()
    started = time.perf_counter()
    req = Request(endpoint, headers={"Accept": "application/json"})
    with urlopen(req, timeout=timeout) as response:
        body = json.load(response)
    if body.get("status") != "success" or body.get("data", {}).get("resultType") != "vector":
        raise RuntimeError("Prometheus query did not return a successful instant vector")
    if len(body["data"]["result"]) > max_series:
        raise RuntimeError("Prometheus query exceeds configured safe series cap")
    return {"query": query, "queried_at": before,
            "duration_ms": round(1000 * (time.perf_counter() - started), 3),
            "series": [{"labels": x.get("metric", {}), "value": x.get("value")}
                       for x in body["data"]["result"]]}


def http_probe(url: str, timeout: float, failed_status: int = 500) -> dict[str, Any]:
    started = time.perf_counter()
    stamp = utc_now()
    status: int | None = None
    error: str | None = None
    try:
        req = Request(url, method="GET", headers={"User-Agent": "N06-field-probe/1.0"})
        with urlopen(req, timeout=timeout) as resp:
            status = resp.status
            resp.read(1)
    except HTTPError as exc:
        status = exc.code
    except (URLError, TimeoutError, OSError) as exc:
        error = type(exc).__name__
    return {"observed_at": stamp, "http_status": status,
            "unavailable": status is None or status >= failed_status,
            "duration_ms": round(1000 * (time.perf_counter() - started), 3),
            "error_type": error}


def total_cpu_seconds() -> float:
    parent = resource.getrusage(resource.RUSAGE_SELF)
    children = resource.getrusage(resource.RUSAGE_CHILDREN)
    return sum((parent.ru_utime, parent.ru_stime, children.ru_utime, children.ru_stime))


def sample(*, context: str, namespace: str, prometheus_url: str, query_map: dict[str, str],
           probe_url: str, cluster_id: str, timeout: float, max_series: int = 20000) -> dict[str, Any]:
    start = time.perf_counter()
    cpu_start = total_cpu_seconds()
    captured_at = utc_now()
    objects = curate_objects(kubectl_json(context,
                                           ["get", "pods,replicasets,deployments,statefulsets,daemonsets,events",
                                            "-n", namespace],
                                           timeout))
    stamp = time.time()
    queried: dict[str, Any] = {}
    for name, expression in query_map.items():
        queried[name] = prom_query(prometheus_url, expression, stamp, timeout, max_series)
    independent_probe = http_probe(probe_url, timeout)
    return {"kind": "snapshot", "real_capture": True, "cluster_id": cluster_id,
            "captured_at": captured_at, "completed_at": utc_now(),
            "objects": objects, "prometheus_vectors": queried,
            "probe": independent_probe,
            "collection_cost": {
                "elapsed_ms": round((time.perf_counter() - start) * 1000, 3),
                "cpu_seconds_self_and_kubectl": round(total_cpu_seconds() - cpu_start, 6),
                "objects": len(objects),
                "vector_series": sum(len(x["series"]) for x in queried.values()),
            }}


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as dest:
        dest.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context", required=True, help="Explicit kubectl context, read-only RBAC")
    parser.add_argument("--namespace", required=True, help="Limit collection to one authorized app namespace")
    parser.add_argument("--prometheus-url", required=True, help="Existing authorized Prometheus URL")
    parser.add_argument("--probe-url", required=True, help="Independent HTTP read-only GET health probe")
    parser.add_argument("--queries", required=True, type=Path, help="JSON mapping of query name to PromQL")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--seconds", type=int, default=1800, help="Maximum capture duration")
    parser.add_argument("--interval", type=float, default=15)
    parser.add_argument("--timeout", type=float, default=8)
    parser.add_argument("--max-series", type=int, default=20000)
    args = parser.parse_args()
    if args.seconds <= 0 or args.interval <= 0 or args.timeout <= 0 or args.max_series <= 0:
        parser.error("seconds, interval, timeout and max-series must all be positive")
    if not re.fullmatch(r"[a-z0-9]([-a-z0-9]*[a-z0-9])?", args.namespace):
        parser.error("namespace must be a valid lowercase Kubernetes DNS label")
    query_map = json.loads(args.queries.read_text(encoding="utf-8"))
    if not isinstance(query_map, dict) or not query_map or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in query_map.items()):
        parser.error("queries must be a nonempty JSON object of strings")
    query_map = {k: v.replace("__NAMESPACE__", args.namespace) for k, v in query_map.items()}
    uid = cluster_uid(args.context, args.timeout)
    # A hash of the namespace UID avoids putting context credentials in logs.
    identity = hashlib.sha256(uid.encode("utf-8")).hexdigest()
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = {"schema_version": 1, "real_capture": True,
                "cluster_uid_sha256": identity, "context_label": args.context,
                "application_namespace": args.namespace,
                "probe_url_sha256": hashlib.sha256(args.probe_url.encode()).hexdigest(),
                "prometheus_url_sha256": hashlib.sha256(args.prometheus_url.encode()).hexdigest(),
                "interval_seconds": args.interval, "started_at": utc_now(),
                "collection_method": "kubectl read-only snapshots + Prometheus HTTP instant queries + HTTP GET probe"}
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    started = time.monotonic()
    next_tick = started
    count = 0
    error_count = 0
    while time.monotonic() - started < args.seconds:
        try:
            row = sample(context=args.context, namespace=args.namespace,
                         prometheus_url=args.prometheus_url,
                         query_map=query_map, probe_url=args.probe_url,
                         cluster_id=identity, timeout=args.timeout,
                         max_series=args.max_series)
            append_jsonl(args.out / "capture.jsonl", row)
            count += 1
        except (RuntimeError, OSError, ValueError, json.JSONDecodeError,
                subprocess.TimeoutExpired, URLError) as exc:
            append_jsonl(args.out / "capture_errors.jsonl",
                         {"kind": "collection_error", "at": utc_now(),
                          "type": type(exc).__name__})
            error_count += 1
        next_tick += args.interval
        delay = next_tick - time.monotonic()
        if delay > 0:
            time.sleep(min(delay, max(0, args.seconds - (time.monotonic() - started))))
    print(json.dumps({"records": count, "errors": error_count,
                      "cluster_uid_sha256": identity, "out": str(args.out)}))
    return 0 if count else 2


if __name__ == "__main__":
    raise SystemExit(main())
