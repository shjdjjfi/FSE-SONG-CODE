"""Compare policy effects using independently labeled incidents and REAL pager receipts.

An Alertmanager test webhook is a FIRST-HOP receipt, not a human page.
The input here must be separately collected, authorized paging-provider
delivery telemetry and independent operator-confirmed outages.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
from statistics import median
from typing import Any

try:
    from .audit import audit_bundle, parse_time, path_at, read_jsonl
except ImportError:
    from audit import audit_bundle, parse_time, path_at, read_jsonl


def alert_matches_incident(row: dict[str, Any], incident: dict[str, Any]) -> bool:
    labels = row.get("labels") or {}
    return (row.get("cluster_id") == incident.get("cluster_id") and
            labels.get("owner_uid") == incident.get("owner_uid") and
            labels.get("namespace") == incident.get("namespace") and
            labels.get("service") == incident.get("service"))


def describe_project(project: dict[str, Any], base: Path,
                     *, capture_duration_seconds: float) -> list[dict[str, Any]]:
    incidents = read_jsonl(path_at(base, project["incidents"]))
    receipts = read_jsonl(path_at(base, project["pager_receipts"]))
    cost = read_jsonl(path_at(base, project["production_cost"]))
    by_policy: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in receipts:
        if row.get("status") not in {"firing", "resolved"}:
            continue
        if not row.get("delivery_provider_id"):
            raise ValueError("provider receipt missing delivery_provider_id")
        parse_time(row["delivered_at"])
        by_policy[row["policy"]].append(row)
    summaries = []
    for policy, rows in sorted(by_policy.items()):
        hit_delays = []
        misses = 0
        repeats = 0
        recoveries = []
        premature = 0
        for incident in incidents:
            start, end = parse_time(incident["start"]), parse_time(incident["end"])
            matched = [r for r in rows if alert_matches_incident(r, incident)]
            firings = sorted((parse_time(r["delivered_at"]) for r in matched
                              if r["status"] == "firing" and
                              start <= parse_time(r["delivered_at"]) <= end))
            if firings:
                hit_delays.append(firings[0] - start)
                repeats += max(0, len(firings) - 1)
            else:
                misses += 1
            resolutions = sorted(parse_time(r["delivered_at"]) for r in matched
                                 if r["status"] == "resolved" and
                                 parse_time(r["delivered_at"]) >= start)
            premature += sum(t < end for t in resolutions)
            recoveries.extend(t - end for t in resolutions if t >= end)
        false_pages = 0
        for receipt in rows:
            if receipt["status"] != "firing":
                continue
            arrival = parse_time(receipt["delivered_at"])
            if not any((parse_time(x["start"]) <= arrival <= parse_time(x["end"])) and
                       alert_matches_incident(receipt, x) for x in incidents):
                false_pages += 1
        proc_rows = [x for x in cost if x.get("policy") == policy and
                     x.get("collector_kind") == "live_process"]
        summary = {
            "project": project["name"], "policy": policy,
            "incident_count": len(incidents), "delivered_first_page_count": len(hit_delays),
            "missed_incident_count": misses,
            "first_page_delay_seconds_median": median(hit_delays) if hit_delays else None,
            "repeated_page_count": repeats, "false_page_count": false_pages,
            "false_pages_per_24h": round(false_pages * 86400 / capture_duration_seconds, 4)
                                    if capture_duration_seconds else None,
            "premature_resolution_count": premature,
            "recovery_notification_lag_seconds_median": median(recoveries) if recoveries else None,
            "cpu_seconds_per_interval_median": median(x["cpu_seconds_per_interval"] for x in proc_rows)
                                                if proc_rows else None,
            "resident_memory_mb_median": median(x["resident_memory_mb"] for x in proc_rows)
                                         if proc_rows else None,
            "measurement_type": "authenticated_real_pager_delivery_if_sources_verified",
        }
        summaries.append(summary)
    return summaries


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.bundle.read_text(encoding="utf-8"))
    gate = audit_bundle(config, args.bundle.parent)
    if gate["status"] != "NEEDS_MANUAL_FIELD_REVIEW":
        print("BLOCKED: independent real source evidence has not passed automated checks")
        return 2
    results = []
    for project, project_gate in zip(config["projects"], gate["project_evidence"]):
        results.extend(describe_project(
            project, args.bundle.parent,
            capture_duration_seconds=project_gate["capture_duration_seconds"]))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"manual_authenticity_review_required": True,
                                    "per_project_policy": results}, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE preliminary receipt-based results for {len(results)} project/policy pairs; MANUAL REVIEW REQUIRED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
