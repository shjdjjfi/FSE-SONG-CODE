"""Turn TIMESTAMPED, ACTUALLY CAPTURED N06 exporter samples into promtool fixtures.

Labels come from operator-confirmed incidents, NOT from a model oracle. A
failed native assertion is a real negative result and must be retained.
Synthetic and hand-authored data MUST NOT be passed off as this export.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any

import yaml

try:
    from .audit import parse_time, read_jsonl
except ImportError:
    from audit import parse_time, read_jsonl


LABEL_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def promql_labelset(labels: dict[str, str]) -> str:
    if not all(LABEL_RE.fullmatch(str(k)) for k in labels):
        raise ValueError("bad Prometheus label name")
    inside = ",".join(f"{key}={json.dumps(str(value))}" for key, value in sorted(labels.items()))
    return "{" + inside + "}"


def make_real_case(snapshots: list[dict[str, Any]], incident: dict[str, Any],
                   *, interval: int = 15, hold: int = 600) -> dict[str, Any]:
    begin = parse_time(incident["start"])
    end = parse_time(incident["end"])
    if end - begin < hold + interval * 4:
        raise ValueError("incident too short for independent held-out timing assertion")
    # Pad to include pre-failure controls and post-recovery behavior.
    origin = math.floor((begin - 2 * interval) / interval) * interval
    last = min(end + 4 * interval, origin + 4 * 3600)
    count = math.ceil((last - origin) / interval) + 1
    if count < 30 or count > 1000:
        raise ValueError("replay length out of supported bounds")
    values_by_series: dict[tuple[tuple[str, str], ...], list[str]] = {}
    for shot in snapshots:
        candidate = (shot.get("prometheus_vectors") or {}).get("n06_owner_unavailable")
        if not candidate:
            continue
        for series in candidate.get("series", []):
            labels = series.get("labels") or {}
            if any(labels.get(key) != incident.get(key) for key in ("namespace", "service", "owner_uid")):
                continue
            if labels.get("__name__") not in {None, "n06_owner_unavailable"}:
                continue
            pair = series.get("value")
            try:
                t, v = float(pair[0]), str(float(pair[1]))
            except (ValueError, IndexError, TypeError):
                continue
            index = round((t - origin) / interval)
            if not 0 <= index < count or abs(t - (origin + index * interval)) > interval * 0.49:
                continue
            label_tuple = tuple(sorted((str(k), str(vv)) for k, vv in labels.items()
                                       if k != "__name__"))
            values = values_by_series.setdefault(label_tuple, ["_"] * count)
            values[index] = v
    if not values_by_series:
        raise ValueError("no authentic exporter series matching incident owner UID and service")
    # An independent ground-truth label requires a true alert once the rule's
    # hold duration has elapsed. Native promtool checks whether this happened.
    evaluate = math.ceil((begin + hold + 2 * interval - origin) / interval) * interval
    if evaluate > (end - origin - interval):
        raise ValueError("no valid in-incident evaluation time after hold")
    if len(values_by_series) != 1:
        raise ValueError("ambiguous N06 owner series; collapse exporter scrape targets before native replay")
    source_labels = dict(next(iter(values_by_series)))
    if source_labels.get("job") != "n06-relink":
        raise ValueError("N06 samples must come from a job=n06-relink scrape")
    alert_labels = {**source_labels, "severity": "test"}
    testcase = {
        "name": f"real-incident-{incident['incident_id']}", "interval": f"{interval}s",
        "input_series": [{"series": "n06_owner_unavailable" + promql_labelset(dict(k)),
                          "values": " ".join(v)} for k, v in sorted(values_by_series.items())],
        "alert_rule_test": [{"eval_time": f"{evaluate}s", "alertname": "N06OwnerRelinkDown",
                             "exp_alerts": [{"exp_labels": alert_labels}]}],
    }
    # Recovery is a distinct control; merely having a true onset assertion
    # does not prove false-resolution behavior. Replayed only if window covers it.
    after = math.ceil((end + 2 * interval - origin) / interval) * interval
    if after < count * interval:
        testcase["alert_rule_test"].append(
            {"eval_time": f"{after}s", "alertname": "N06OwnerRelinkDown", "exp_alerts": []})
    return testcase


def export(capture: Path, incidents: Path, manifest: Path, output: Path,
           *, interval: int = 15) -> dict[str, Any]:
    metadata = json.loads(manifest.read_text(encoding="utf-8"))
    if metadata.get("real_capture") is not True or not metadata.get("cluster_uid_sha256"):
        raise ValueError("not an approved real collector manifest")
    shots = read_jsonl(capture)
    if not shots or any(s.get("cluster_id") != metadata["cluster_uid_sha256"] or
                        s.get("real_capture") is not True for s in shots):
        raise ValueError("inconsistent or empty genuine field capture")
    observed = read_jsonl(incidents)
    cases = []
    for incident in observed:
        if incident.get("origin") not in {"operator_confirmed", "public_postmortem"}:
            raise ValueError("cannot assert native alert outcomes from simulated ground truth")
        if incident.get("cluster_id") != metadata["cluster_uid_sha256"]:
            raise ValueError("incident belongs to different cluster")
        cases.append(make_real_case(shots, incident, interval=interval))
    if not cases:
        raise ValueError("no real independently adjudicated incidents to test")
    output.parent.mkdir(parents=True, exist_ok=True)
    spec = {"rule_files": ["alert_rules.yml"], "evaluation_interval": f"{interval}s", "tests": cases}
    output.write_text(yaml.safe_dump(spec, sort_keys=False), encoding="utf-8")
    audit = {"fixture_origin": "real_collector_and_independent_incident_labels__manual_verification_required",
             "created_at": datetime.now(timezone.utc).isoformat(),
             "cluster_uid_sha256": metadata["cluster_uid_sha256"],
             "source_capture_sha256": sha256(capture), "source_incidents_sha256": sha256(incidents),
             "source_manifest_sha256": sha256(manifest), "exported_fixture_sha256": sha256(output),
             "case_count": len(cases), "interval_seconds": interval}
    (output.parent / (output.stem + ".evidence.json")).write_text(
        json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", required=True, type=Path)
    parser.add_argument("--incidents", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path,
                        help="For native promtool, output next to alert_rules.yml")
    parser.add_argument("--interval", type=int, default=15)
    args = parser.parse_args()
    if args.interval <= 0:
        parser.error("interval must be positive")
    print(json.dumps(export(args.capture, args.incidents, args.manifest,
                            args.out, interval=args.interval)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
