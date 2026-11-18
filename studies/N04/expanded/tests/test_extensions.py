"""Regression tests for the dated external-evidence extensions."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ci_event_audit import gitlab_change_summary
from external_rename_probe import polarity_changed, score, stem
from hierarchical_history_linker import fallback
from n04_benchmark import Snippet
from strong_baseline_extension import score_top


class QuarantineAuditTests(unittest.TestCase):
    def test_gitlab_annotation_counts_and_issue_url(self):
        patch = {
            "old_path":"tests/spec.rb", "new_path":"tests/spec.rb",
            "diff":"@@ -1,1 +1,1 @@\n- it 'abc', quarantine: 'https://gitlab.com/gitlab-org/gitlab/-/issues/123'\n+ it 'abc'\n",
        }
        item = gitlab_change_summary(patch)
        self.assertEqual(item["quarantine_lines_added"], 0)
        self.assertEqual(item["quarantine_lines_removed"], 1)
        self.assertEqual(item["removed_test_descriptions"], ["abc"])
        self.assertEqual(item["issue_refs_in_quarantine_removals"], [
            "https://gitlab.com/gitlab-org/gitlab/-/issues/123"])


class PublicRenameTests(unittest.TestCase):
    def test_name_normalization_only_when_appropriate(self):
        self.assertEqual(stem("testHandleAlert"), stem("test_handle_alert"))
        self.assertNotEqual(stem("test_foo"), stem("test_bar"))

    def test_polarity_reversal_warning(self):
        self.assertTrue(polarity_changed("shouldFailIfInvalid", "shouldNotFailIfInvalid"))
        self.assertFalse(polarity_changed("testGetValue", "getValue"))
        self.assertEqual(score("testGetValue", "getValue", "exact_method_name"), 0)


class LinkerTests(unittest.TestCase):
    def test_tiebreak_equal_method_names_from_source(self):
        old=Snippet("old","p","sha","a.py","test_foo","", "def test_foo():\n    assert 3 == 3\n")
        right=Snippet("right","p","sha","b.py","test_foo","", "def test_foo():\n    assert 3 == 3\n")
        wrong=Snippet("wrong","p","sha","c.py","test_foo","", "def test_foo():\n    assert 2 == 7\n")
        self.assertEqual(score_top(old,[wrong,right],"name_body_tiebreak")[2],"right")

    def test_conservative_case_fallback(self):
        old=Snippet("old","p","sha","a.py","testHandleAlert","", "def testHandleAlert():\n    assert True\n")
        right=Snippet("right","p","sha","a.py","test_handle_alert","", "def test_handle_alert():\n    assert True\n")
        wrong=Snippet("wrong","p","sha","a.py","test_other","", "def test_other():\n    assert False\n")
        self.assertEqual(fallback(old,[right,wrong],False)[0],"right")
        self.assertEqual(fallback(old,[wrong],False)[0],"")


if __name__ == "__main__":
    unittest.main()
