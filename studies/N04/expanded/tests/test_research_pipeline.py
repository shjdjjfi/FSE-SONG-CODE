"""Safety and reproducibility checks using only Python's standard library."""

from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from n04_benchmark import Snippet, accept, choose_candidates, extract_test, load_pairs, score
from history_replay import is_flaky, outcome
from pytest_cache_bridge import build_mapping, rewrite_cache


class TestDataIntegrity(unittest.TestCase):
    def test_single_test_extraction(self):
        result=extract_test("class TestCase:\n    def test_run(self):\n        assert 1 == 1\n")
        self.assertEqual(result[0],"test_run")
        self.assertEqual(result[1],"TestCase")

    def test_ambiguous_multi_test_rejected(self):
        result=extract_test("def test_a():\n    pass\n\ndef test_b():\n    pass\n")
        self.assertIsNone(result)

    def test_top_tie_abstains(self):
        self.assertEqual(accept((1., 0., "target"),0.5,0.),"")

    def test_direct_exact_link_and_negative(self):
        src=Snippet("old","demo","a","test_a.py","test_d","TestFoo","def test_d():\n assert True")
        tgt=Snippet("new","demo","a","test_a.py","test_d","TestFoo","def test_d():\n assert True")
        unrelated=Snippet("wrong","demo","a","test_b.py","test_other","TestFoo","def test_other():\n assert False")
        self.assertEqual(score(src,tgt,"exact_node_id"),1.)
        self.assertEqual(score(src,unrelated,"exact_node_id"),0.)

    def test_flaky_requires_two_outcomes(self):
        self.assertTrue(is_flaky(["P","P","F"]))
        self.assertFalse(is_flaky(["F","F","F"]))
        self.assertFalse(is_flaky(["P","P","P"]))
        self.assertEqual(outcome("failed"),"F")


class TestStrictBridge(unittest.TestCase):
    def test_safe_function_rename(self):
        old="def test_old():\n    assert False\n"
        new="def test_new():\n    assert False\n"
        links,audit=build_mapping(old,new)
        self.assertEqual(links,{"test_old":"test_new"})
        self.assertEqual(audit["safe_links"],1)

    def test_semantic_change_abstains(self):
        old="def test_old():\n    assert False\n"
        new="def test_old():\n    assert True\n"
        links,audit=build_mapping(old,new)
        self.assertEqual(links,{})
        self.assertEqual(audit["changed_semantics"],1)

    def test_split_abstains(self):
        old="def test_old():\n    assert False\n"
        new="def test_old_part_a():\n    assert False\n\ndef test_old_part_b():\n    assert True\n"
        links,audit=build_mapping(old,new)
        self.assertEqual(links,{})
        self.assertEqual(audit["split_ambiguous"],1)

    def test_unambiguous_parameter_relabel(self):
        head="import pytest\n@pytest.mark.parametrize('x',[0,1],ids={})\ndef test_x(x):\n    assert x > 0\n"
        old=head.format("['alpha','beta']")
        new=head.format("['one','two']")
        links,audit=build_mapping(old,new)
        self.assertEqual(links,{"test_x[alpha]":"test_x[one]", "test_x[beta]":"test_x[two]"})
        self.assertEqual(audit["param_id_pairs"],2)

    def test_rewrites_only_target_cache(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            p=root/".pytest_cache/v/cache/lastfailed"
            p.parent.mkdir(parents=True)
            p.write_text(json.dumps({"test_before.py::test_old":True,
                                     "other.py::test_keep":True}))
            out=rewrite_cache(root,"test_before.py","test_after.py",
                              "def test_old():\n assert False", "def test_new():\n assert False")
            new=json.loads(p.read_text())
            self.assertEqual(out["transferred"],1)
            self.assertIn("test_after.py::test_new",new)
            self.assertIn("other.py::test_keep",new)


if __name__ == "__main__":
    unittest.main()
