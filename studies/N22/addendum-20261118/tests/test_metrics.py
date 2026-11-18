"""Tests of analysis independence, false-positive controls, and aggregation."""

import importlib.util
import json
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("n22_analyze", BASE / "code/analyze.py")
ANALYZE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ANALYZE)


class DetectorTests(unittest.TestCase):
    def test_permission_missing_only_if_grant_absent(self):
        data = {"family": "django_permissions", "evidence": {
            "contract_input": {"granted_permission_before_or_after_migration":
                               ["app", "songprofile", "view_songprofile"]},
            "user_grants": [["app", "songprofile", "view_son"]]}}
        self.assertTrue(ANALYZE.contracts(data))
        data["evidence"]["user_grants"].append(["app", "songprofile", "view_songprofile"])
        self.assertFalse(ANALYZE.contracts(data))

    def test_user_modified_site_is_legitimate(self):
        data = {"family": "django_sites", "evidence": {
            "contract_input": {"site_id": 1, "user_owned_domain": "user.example",
                               "user_owned_name": "Not a default", "expected_redirect_count": 0},
            "site_rows": [[1, "user.example", "Not a default"]], "redirect_rows": []}}
        self.assertFalse(ANALYZE.contracts(data))
        data["evidence"]["site_rows"][0][1] = "example.com"
        self.assertTrue(ANALYZE.contracts(data))

    def test_completed_marker_does_not_imply_all_rows_copied(self):
        data = {"family": "opencode", "evidence": {
            "migration_status": "completed", "checkpoint": '{"phase":"completed"}',
            "source_messages": ["msg1", "msg2"], "projected_messages": ["msg1"],
            "source_sessions": ["s1"], "projected_sessions": ["s1"]}}
        self.assertFalse(ANALYZE.status_only(data))
        self.assertTrue(ANALYZE.contracts(data))

    def test_main_run_metrics_are_case_level(self):
        results = BASE / "reports/metrics.json"
        if not results.exists():
            self.skipTest("Only available when run_all.py and analyze.py have executed")
        summary = json.loads(results.read_text(encoding="utf-8"))
        self.assertEqual(summary["primary_positive_cases"], 2)
        self.assertEqual(summary["primary_negative_cases"], 13)
        self.assertEqual(summary["separately_reported_correlated_negative_stress_cases"], 30)
        self.assertEqual(summary["scores"]["full_manual_contract_baseline"],
                         summary["scores"]["contract_detector"])
        self.assertFalse(summary["original_hypothesis_gate"]["gate_passed"])


if __name__ == "__main__":
    unittest.main()
