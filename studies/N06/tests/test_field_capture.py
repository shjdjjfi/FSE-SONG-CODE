"""Offline tests of evidence handling; NOT two-system production experiments."""

from __future__ import annotations

import json
from datetime import datetime, timezone
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from field_capture.alert_receiver import parse_webhook
from field_capture.analyze_delivery import alert_matches_incident
from field_capture.audit import audit_bundle, get_owner_uid, parse_time
from field_capture.collector import curate_objects
from field_capture.process_cost import process_values
from field_capture.export_real_cases import make_real_case
from field_capture.native_evidence import run_promtool
from field_capture.owner_exporter import OwnerExporter, verified_event_present


class FieldEvidenceTests(unittest.TestCase):
    def test_curator_does_not_copy_environment_or_annotations(self):
        raw = {"items": [{"kind": "Pod", "metadata": {"name": "p1", "namespace": "ns",
                      "uid": "pod-uid", "annotations": {"password": "LEAK"}},
                      "spec": {"containers": [{"env": [{"value": "SECRET"}]}]},
                      "status": {"conditions": [{"type": "Ready", "status": "False"}]}}]}
        rows = curate_objects(raw)
        self.assertEqual(rows[0]["ready"], False)
        self.assertNotIn("SECRET", json.dumps(rows))
        self.assertNotIn("LEAK", json.dumps(rows))

    def test_pod_to_replicaset_to_deployment_uid(self):
        pod = {"kind": "Pod", "uid": "p1", "owner_references": [
            {"kind": "ReplicaSet", "uid": "rs1", "controller": True}]}
        rs = {"kind": "ReplicaSet", "uid": "rs1", "owner_references": [
            {"kind": "Deployment", "uid": "dep1", "controller": True}]}
        self.assertEqual(get_owner_uid(pod, [pod, rs]), "dep1")
        self.assertEqual(get_owner_uid(pod, [pod]), None)

    def test_webhook_records_actual_receiver_timestamp_not_start_time(self):
        body = {"alerts": [{"status": "firing", "startsAt": "2026-01-01T00:00:00Z",
                             "labels": {"owner_uid": "dep", "alertname": "N06", "secret": "DONT_LOG"}}],
                "status": "firing", "receiver": "test"}
        rows = parse_webhook(body, cluster_id="hash", policy="n06",
                             received_at="2026-01-01T00:05:00Z")
        self.assertEqual(rows[0]["received_at"], "2026-01-01T00:05:00Z")
        self.assertNotIn("secret", rows[0]["labels"])
        self.assertEqual(rows[0]["delivery_hop"], "alertmanager_to_test_webhook")

    def test_match_by_full_owner_uid_not_reused_name(self):
        incident = {"cluster_id": "a", "owner_uid": "dep-a", "namespace": "shop", "service": "cart"}
        row = {"cluster_id": "a", "labels": {"owner_uid": "dep-b", "namespace": "shop", "service": "cart"}}
        self.assertFalse(alert_matches_incident(row, incident))
        row["labels"]["owner_uid"] = "dep-a"
        self.assertTrue(alert_matches_incident(row, incident))

    def test_bundle_without_two_real_cluster_identifiers_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "capture.jsonl").write_text("", encoding="utf-8")
            report = audit_bundle({"projects": [
                {"name": "A", "capture": "capture.jsonl"},
                {"name": "B", "capture": "capture.jsonl"}]}, root)
            self.assertEqual(report["status"], "BLOCKED")
            self.assertFalse(report["independent_cluster_identities"])

    def test_timestamp_parser(self):
        self.assertEqual(parse_time("2026-01-01T00:00:00Z"),
                         parse_time("2026-01-01T08:00:00+08:00"))

    def test_exporter_synthetic_unit_fixture_is_marked_only_as_test(self):
        # Values below are fabricated solely for a unit test of the converter.
        origin = parse_time("2026-01-01T00:00:00Z")
        labels = {"job": "n06-relink", "namespace": "shop", "service": "cart",
                  "owner_uid": "real-looking-but-synthetic-unit-uid"}
        shots = [{"prometheus_vectors": {"n06_owner_unavailable": {"series": [
            {"labels": labels, "value": [origin + 15 * i, "1"]}]}}}
                 for i in range(96)]
        incident = {"incident_id": "SYNTHETIC_UNIT_TEST", "namespace": "shop",
                    "service": "cart", "owner_uid": labels["owner_uid"],
                    "start": "2026-01-01T00:01:00Z", "end": "2026-01-01T00:19:00Z"}
        spec = make_real_case(shots, incident)
        self.assertEqual(spec["alert_rule_test"][0]["alertname"], "N06OwnerRelinkDown")
        self.assertIn("real-incident-SYNTHETIC_UNIT_TEST", spec["name"])

    def test_native_test_runner_reports_missing_binary_without_fake_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_promtool(Path(tmp), executable="missing-n06-promtool-test-executable")
            self.assertEqual(result["status"], "NOT_EXECUTED")
            self.assertFalse(result["real_project_samples"])
            self.assertEqual(result["exit_code"], 2)

    def test_experimental_exporter_owner_uid_veto_and_name_reuse(self):
        exporter = OwnerExporter(context="MOCK_ONLY", namespace="shop", deployment="cart",
                                 service="cart", probe_url="https://invalid.example")
        parent = lambda uid: {"kind": "Deployment", "uid": uid}
        rs = lambda uid: {"kind": "ReplicaSet", "uid": "rs-" + uid,
                          "owner_references": [{"kind": "Deployment", "uid": uid}]}
        pod = lambda puid, duid, ready: {"kind": "Pod", "uid": puid, "ready": ready,
                    "owner_references": [{"kind": "ReplicaSet", "uid": "rs-" + duid,
                                          "controller": True}]}
        now = parse_time("2026-01-01T00:02:00Z")
        old = [parent("dep-A"), rs("dep-A"), pod("pod-a", "dep-A", False)]
        exporter.update_from_objects("dep-A", old, True, observed_at=now)
        self.assertIn(b'owner_uid="dep-A"} 1', exporter.metrics())
        evt = {"kind": "Event", "event_reason": "ScalingReplicaSet", "event_at":
               datetime.fromtimestamp(now + 15, tz=timezone.utc).isoformat(),
               "related": {"uid": "dep-A"}}
        updated = [parent("dep-A"), rs("dep-A"), pod("pod-b", "dep-A", False), evt]
        exporter.update_from_objects("dep-A", updated, True, observed_at=now + 15)
        self.assertIn(b'owner_uid="dep-A"} 1', exporter.metrics())
        exporter.update_from_objects("dep-A", updated, False, observed_at=now + 30)
        self.assertIn(b'owner_uid="dep-A"} 0', exporter.metrics())
        fresh = [parent("dep-B"), rs("dep-B"), pod("pod-c", "dep-B", False)]
        exporter.update_from_objects("dep-B", fresh, True, observed_at=now + 45)
        self.assertIn(b'owner_uid="dep-B"}', exporter.metrics())
        self.assertNotIn(b'owner_uid="dep-A"}', exporter.metrics())

    def test_stale_rollout_events_cannot_certify_continuity(self):
        event = {"kind": "Event", "event_reason": "ScalingReplicaSet",
                 "event_at": "2026-01-01T00:00:00Z", "related": {"uid": "dep-A"}}
        observed = parse_time("2026-01-01T02:00:00Z")
        self.assertFalse(verified_event_present([event], "dep-A", "old", "new",
                                                observed_at=observed))

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux /proc only")
    def test_process_cpu_and_rss_read_only(self):
        cpu, rss, start = process_values(os.getpid())
        self.assertGreaterEqual(cpu, 0)
        self.assertGreater(rss, 0)
        self.assertGreater(start, 0)


if __name__ == "__main__":
    unittest.main()
