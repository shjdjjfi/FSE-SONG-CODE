"""Minimal Alertmanager webhook for first-hop delivery observations.

IMPORTANT: A webhook accepted here is not proof that an on-call phone, SMS,
PagerDuty integration or human operator actually received a page. The latter
needs the corresponding external paging provider's authenticated delivery log.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import threading
import time
from typing import Any


ALLOWED_LABELS = frozenset({"alertname", "cluster", "namespace", "service",
                            "deployment", "workload", "owner_uid", "severity", "policy"})


def parse_webhook(payload: dict[str, Any], *, cluster_id: str, policy: str,
                  received_at: str | None = None) -> list[dict[str, Any]]:
    """Extract all alert deliveries, including repeats and resolved notices."""
    if not isinstance(payload, dict) or not isinstance(payload.get("alerts"), list):
        raise ValueError("not an Alertmanager JSON webhook")
    seen_at = received_at or datetime.now(timezone.utc).isoformat(timespec="microseconds")
    out = []
    for alert in payload["alerts"]:
        if not isinstance(alert, dict) or alert.get("status") not in {"firing", "resolved"}:
            raise ValueError("missing alert status")
        labels = alert.get("labels", {})
        if not isinstance(labels, dict):
            raise ValueError("alert labels must be a mapping")
        out.append({
            "kind": "webhook_delivery", "cluster_id": cluster_id,
            "policy": policy, "received_at": seen_at,
            "status": alert["status"], "starts_at": alert.get("startsAt"),
            "ends_at": alert.get("endsAt"), "fingerprint": alert.get("fingerprint"),
            "labels": {k: v for k, v in labels.items() if k in ALLOWED_LABELS},
            "group_key": payload.get("groupKey"), "receiver": payload.get("receiver"),
            "notification_status": payload.get("status"),
            "delivery_hop": "alertmanager_to_test_webhook",
        })
    return out


def make_handler(*, out: Path, cluster_id: str, policy: str,
                 token: str | None) -> type[BaseHTTPRequestHandler]:
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            if self.path != "/alertmanager":
                self.send_error(404)
                return
            if token and not secrets.compare_digest(
                    self.headers.get("Authorization", ""), "Bearer " + token):
                self.send_error(401)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 1_048_576:
                    self.send_error(413)
                    return
                received_at = datetime.now(timezone.utc).isoformat(timespec="microseconds")
                body = json.loads(self.rfile.read(length))
                rows = parse_webhook(body, cluster_id=cluster_id, policy=policy,
                                     received_at=received_at)
            except (ValueError, json.JSONDecodeError):
                self.send_error(400)
                return
            with lock:
                with out.open("a", encoding="utf-8") as stream:
                    for row in rows:
                        stream.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
                    stream.flush()
                    os.fsync(stream.fileno())
            self.send_response(200)
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"ok")

        def log_message(self, fmt: str, *args: Any) -> None:
            # Avoid logging bearer tokens and potentially sensitive payloads.
            return

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--cluster-id", required=True, help="Collector's cluster_uid_sha256")
    parser.add_argument("--policy", required=True, help="n06, kube_mixin, nextdoor, etc")
    parser.add_argument("--host", default="127.0.0.1", help="Use loopback unless behind auth proxy")
    parser.add_argument("--port", type=int, default=19093)
    parser.add_argument("--bearer-env", help="Optional environment variable containing a bearer token")
    args = parser.parse_args()
    if args.port < 1 or args.port > 65535:
        parser.error("invalid port")
    token = os.environ.get(args.bearer_env) if args.bearer_env else None
    if args.bearer_env and not token:
        parser.error("requested bearer token variable is not configured")
    if args.host not in {"127.0.0.1", "localhost", "::1"} and not token:
        parser.error("non-loopback binding requires --bearer-env")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((args.host, args.port), make_handler(
        out=args.out, cluster_id=args.cluster_id, policy=args.policy, token=token))
    print(f"Alertmanager first-hop receiver started at {args.host}:{args.port}", flush=True)
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
