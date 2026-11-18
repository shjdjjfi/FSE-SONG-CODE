"""Reproducibility invariants and negative controls for the evidence protocol."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))

from audit_real_ci import audit
from replay_history_policy import counts
from statistical_audit import clopper_pearson


class ProtocolTests(unittest.TestCase):
    def test_missing_from_actions_failed_candidates_is_not_a_pass(self):
        self.assertEqual(counts(None)["passed"],0)
        self.assertEqual(counts(None)["failed"],0)

    def test_duplicate_real_ci_snapshot_runs_are_deduplicated(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)/"owner"/"project"
            root.mkdir(parents=True)
            run={"run_id":100,"run_attempt":1,"created_at":"2026-01-01T01:00:00Z",
                 "failed_tests":{"t.py::test_a":{"passes":1,"failures":1}}}
            a=root/"main.json"; b=root/"main-duplicate.json"
            a.write_text(json.dumps([run]))
            b.write_text(json.dumps([run]))
            result=audit([a,b])
            self.assertEqual(result["overall"]["unique_repository_run_attempts"],1)
            self.assertEqual(result["overall"]["unique_failed_test_ids_per_repo_summed"],1)
            self.assertEqual(result["overall"]["duplicate_run_attempts_across_snapshots"],1)

    def test_zero_of_five_is_not_proof_of_two_percent(self):
        lo,hi=clopper_pearson(0,5)
        self.assertEqual(lo,0.0)
        self.assertGreater(hi,.5)
        self.assertLessEqual(clopper_pearson(0,183)[1],.02)


if __name__=="__main__":unittest.main()
