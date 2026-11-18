"""Experimental read-only owner-continuity exporter for one Deployment.

One process per Deployment/service and namespace. Uses actual Pod UID and
ReplicaSet -> Deployment UID relationships, recent rollout events, readiness,
and an independent health GET. Its output is consumed by native Prometheus
`for:` rules. NOT tested against a real cluster in this deliverable.

This polling prototype is NOT a production-grade informer, high-availability
service or universal Kubernetes owner resolver. It intentionally makes no
Kubernetes writes and fails safe on lost ownership / changed Deployment UID.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import re
import subprocess
import threading
import time
from typing import Any

try:
    from .audit import get_owner_uid, parse_time
    from .collector import curate_objects, http_probe, kubectl_json
except ImportError:
    from audit import get_owner_uid, parse_time
    from collector import curate_objects, http_probe, kubectl_json

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.simulator import Observation, Pod, Policy, Rollout  # noqa: E402


def prometheus_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def verified_event_present(objects: list[dict[str, Any]], owner_uid: str,
                           old_pod_uid: str, new_pod_uid: str,
                           *, observed_at: float, max_age_seconds: float = 120.0) -> bool:
    """Require a lifecycle event referencing this Deployment or involved Pod/RS."""
    relevant = {owner_uid, old_pod_uid, new_pod_uid}
    for obj in objects:
        if obj.get("kind") == "ReplicaSet" and any(
                r.get("uid") == owner_uid for r in obj.get("owner_references", [])):
            relevant.add(obj.get("uid"))
    for x in objects:
        if x.get("kind") != "Event" or x.get("event_reason") not in {
                "ScalingReplicaSet", "SuccessfulCreate", "Killing",
                "SuccessfulDelete", "Started", "Scheduled"}:
            continue
        if (x.get("related") or {}).get("uid") not in relevant:
            continue
        try:
            event_time = parse_time(x["event_at"])
        except (KeyError, TypeError, ValueError):
            continue
        if -10 <= observed_at - event_time <= max_age_seconds:
            return True
    return False


class OwnerExporter:
    def __init__(self, *, context: str, namespace: str, deployment: str,
                 service: str, probe_url: str, interval: float = 15.0,
                 timeout: float = 8.0) -> None:
        self.context = context
        self.namespace = namespace
        self.deployment = deployment
        self.service = service
        self.probe_url = probe_url
        self.interval = interval
        self.timeout = timeout
        self.lock = threading.Lock()
        self.owner_uid: str | None = None
        self.policy = Policy("owner_relink_v2", hold_ticks=40, grace=max(1, round(90 / interval)))
        self.tick = 0
        self.old_pods: dict[str, str | None] = {}
        self.recent_removed: dict[str, tuple[str, int]] = {}
        self.value = 0
        self.poll_success = False
        self.last_sample_timestamp = 0.0
        self.last_duration = 0.0

    def update_from_objects(self, deployment_uid: str, objects: list[dict[str, Any]],
                            probe_bad: bool | None, *, observed_at: float | None = None) -> None:
        """Pure policy update with externally obtained real Kube objects/probe."""
        with self.lock:
            observed_at = observed_at if observed_at is not None else time.time()
            if self.owner_uid != deployment_uid:
                # A name-reused Deployment with a different UID MUST NOT
                # inherit any previous outage history.
                self.owner_uid = deployment_uid
                self.policy = Policy("owner_relink_v2", hold_ticks=40,
                                     grace=max(1, round(90 / self.interval)))
                self.old_pods.clear()
                self.recent_removed.clear()
                self.tick = 0
            all_pods = [x for x in objects if x.get("kind") == "Pod" and x.get("uid")]
            current: dict[str, str | None] = {}
            observations = []
            for p in all_pods:
                owner = get_owner_uid(p, objects)
                if owner != deployment_uid and p["uid"] not in self.policy.pod_owner_cache:
                    continue
                if owner not in {None, deployment_uid}:
                    continue
                current[p["uid"]] = owner
                # Unknown/ambiguous readiness is not interpreted as a failure.
                if p.get("ready") is not None:
                    observations.append(Pod(p["uid"], owner, p["ready"] is False))
            for pod, owner in self.old_pods.items():
                if pod not in current and owner == deployment_uid:
                    self.recent_removed[pod] = (owner, self.tick)
            expire = max(1, round(90 / self.interval))
            self.recent_removed = {p: x for p, x in self.recent_removed.items()
                                   if self.tick - x[1] <= expire}
            new_pods = {p: owner for p, owner in current.items() if p not in self.old_pods
                        and owner == deployment_uid}
            rollouts: list[Rollout] = []
            for new_uid in new_pods:
                for old_uid, (old_owner, _) in self.recent_removed.items():
                    if verified_event_present(objects, deployment_uid, old_uid, new_uid,
                                              observed_at=observed_at):
                        rollouts.append(Rollout(old_uid, new_uid, old_owner,
                                                deployment_uid, True))
                        break
            self.policy.step(Observation(self.tick, tuple(observations),
                                         tuple(rollouts), probe_bad))
            self.value = int(deployment_uid in self.policy.last_condition)
            self.tick += 1
            self.old_pods = current
            self.poll_success = True
            self.last_sample_timestamp = observed_at

    def poll(self) -> None:
        started = time.perf_counter()
        try:
            deployment = kubectl_json(self.context,
                                      ["get", "deployment", self.deployment, "-n", self.namespace],
                                      self.timeout)
            uid = deployment.get("metadata", {}).get("uid")
            if not uid:
                raise ValueError("Deployment UID unavailable")
            objects = curate_objects(kubectl_json(
                self.context, ["get", "pods,replicasets,deployments,events", "-n", self.namespace],
                self.timeout))
            result = http_probe(self.probe_url, self.timeout)
            self.update_from_objects(uid, objects, result["unavailable"])
        except (ValueError, OSError, RuntimeError, json.JSONDecodeError,
                subprocess.TimeoutExpired):
            with self.lock:
                # Preserve no inferred success when evidence collection failed.
                # Consumers must inspect poll_success and freshness separately.
                self.poll_success = False
        finally:
            with self.lock:
                self.last_duration = time.perf_counter() - started

    def metrics(self) -> bytes:
        with self.lock:
            uid = self.owner_uid
            labels = (f'namespace="{prometheus_escape(self.namespace)}",'
                      f'service="{prometheus_escape(self.service)}",'
                      f'owner_uid="{prometheus_escape(uid or "")}"')
            # No candidate metric is exposed when the exporter is not healthy.
            lines = ["# HELP n06_owner_unavailable Experimental owner-level continuous unavailability",
                     "# TYPE n06_owner_unavailable gauge"]
            if uid and self.poll_success:
                lines.append(f"n06_owner_unavailable{{{labels}}} {self.value}")
            lines.extend(["# HELP n06_exporter_poll_success One if last read-only poll succeeded",
                          "# TYPE n06_exporter_poll_success gauge",
                          f"n06_exporter_poll_success {int(self.poll_success)}",
                          "# HELP n06_exporter_last_sample_timestamp_seconds Last successful sample unix seconds",
                          "# TYPE n06_exporter_last_sample_timestamp_seconds gauge",
                          f"n06_exporter_last_sample_timestamp_seconds {self.last_sample_timestamp:.3f}",
                          "# HELP n06_exporter_poll_duration_seconds Last polling duration seconds",
                          "# TYPE n06_exporter_poll_duration_seconds gauge",
                          f"n06_exporter_poll_duration_seconds {self.last_duration:.6f}"])
            return ("\n".join(lines) + "\n").encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context", required=True)
    parser.add_argument("--namespace", required=True)
    parser.add_argument("--deployment", required=True)
    parser.add_argument("--service", required=True)
    parser.add_argument("--probe-url", required=True)
    parser.add_argument("--interval", type=float, default=15)
    parser.add_argument("--timeout", type=float, default=8)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=19100)
    args = parser.parse_args()
    if args.interval <= 0 or args.timeout <= 0 or not 1 <= args.port <= 65535:
        parser.error("invalid interval, timeout or port")
    for name in (args.namespace, args.deployment, args.service):
        if not re.fullmatch(r"[a-z0-9]([-a-z0-9]*[a-z0-9])?", name):
            parser.error("namespace, deployment and service must be Kubernetes DNS labels")
    if args.host not in {"127.0.0.1", "localhost", "::1"}:
        parser.error("this experimental metrics server binds to loopback only")
    exporter = OwnerExporter(context=args.context, namespace=args.namespace,
                             deployment=args.deployment, service=args.service,
                             probe_url=args.probe_url, interval=args.interval,
                             timeout=args.timeout)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path != "/metrics":
                self.send_error(404)
                return
            payload = exporter.metrics()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, fmt: str, *args: Any) -> None:
            return

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"Experimental read-only N06 exporter on {args.host}:{args.port}/metrics", flush=True)
    next_tick = time.monotonic()
    try:
        while True:
            exporter.poll()
            next_tick += args.interval
            time.sleep(max(0, next_tick - time.monotonic()))
    except KeyboardInterrupt:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
