"""Tests for new frozen-evidence integrity and independent-label isolation."""

from __future__ import annotations
import json
from pathlib import Path
import sys
import unittest


ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from build_refactoring_oracle import parse_description  # noqa: E402
from evaluate_oracle_discovery import pick_unique  # noqa: E402
from verify_addendum import check  # noqa: E402


class RefactoringOracleTests(unittest.TestCase):
    def test_realistic_rename_is_parsed(self):
        r=parse_description("Rename Method public void testOld() renamed to public void testNew() in class a.FooTest",
                            "Rename Method")
        self.assertEqual((r["old_id"],r["new_id"]),
                         ("a.FooTest.testOld","a.FooTest.testNew"))

    def test_non_test_rejected(self):
        r=parse_description("Rename Method public void process() renamed to public void processV2() in class a.Service",
                            "Rename Method")
        self.assertIsNone(r)

    def test_non_unique_successor_forces_abstention(self):
        class M:
            def __init__(self,name):self.fqn=name
        pool=[M("one.FooTest.testA"),M("two.FooTest.testA")]
        self.assertIsNone(pick_unique(pool,lambda m:m.fqn.endswith(".testA")))


class ProvenanceTests(unittest.TestCase):
    def test_all_new_evidence_is_internally_consistent(self):
        result=check()
        self.assertEqual(result["end_to_end_recovery"],"40/54")
        self.assertFalse(result["ready_to_claim_fse_industry_benefit"])

    def test_fp_refactoring_label_never_claimed_quarantine_truth(self):
        data=json.loads((ROOT/"results/independent_end_to_end_discovery.json").read_text())
        self.assertTrue(data["not_quarantine_oracle"])
        self.assertTrue(all(r["test_identity_transfer_ground_truth"] is None
                            for r in data["records"]))


if __name__=="__main__":
    unittest.main()
