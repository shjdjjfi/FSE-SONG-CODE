"""CPU-only unit tests. Run with `python -m unittest discover -s tests -v`."""

import json
import lzma
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))

from java_source import method_nodes, normalize
from ingest_histories import ingest
from evaluate_idoft import select_one, evaluate


class SourceTests(unittest.TestCase):
    def test_name_only_rename_preserves_body(self):
        a=method_nodes(b"package a; class T { @Test public void testA(){assertEquals(1,2);} }","T.java")
        b=method_nodes(b"package a; class T { @Test public void testB(){assertEquals(1,2);} }","T.java")
        self.assertEqual(a[0].body_hash,b[0].body_hash)
        self.assertNotEqual(a[0].fqn,b[0].fqn)

    def test_assertion_literal_change_breaks_hash(self):
        a=method_nodes(b"package a; class T { @Test public void testA(){assertEquals(1,2);} }","T.java")
        b=method_nodes(b"package a; class T { @Test public void testB(){assertEquals(1,3);} }","T.java")
        self.assertNotEqual(a[0].body_hash,b[0].body_hash)

    def test_no_false_test_failure_from_absence(self):
        with tempfile.TemporaryDirectory() as folder:
            f=Path(folder)/"a_123_test_results_1.csv.xz"
            row=("Slug,module name,commit hash,timeStamp,test suite name,total time of test suite,"
                 "test case name,total time of test case,test result,message type,test result message\n"
                 "https://github.com/a/b,.,aaaaaaa,100,T,0.1,testX,0.05,passed,.,.\n"
                 "https://github.com/a/b,.,bbbbbbb,101,T,0.1,testY,0.05,passed,.,.\n")
            with lzma.open(f,"wt",encoding="utf-8") as handle:handle.write(row)
            d=ingest(Path(folder))
            self.assertEqual(d["summary"][0]["n_flaky_test_ids"],0)
            self.assertEqual(d["summary"][0]["n_status_observations"],2)

    def test_group_collision_not_individual_gold(self):
        common={"event_id":"r@c","repository":"r","old_id":"A.a",
                "target":"B.b","idoft_status":"MovedOrRenamed",
                "target_certainty":"parameterized_group_only",
                "many_old_to_one_method":True,"candidates":[{
                    "target":"B.b","body_equal":True,"name_similarity":.4,
                    "file_rename":False,"body_similarity":1,"assertion_similarity":1}]}
        c1=dict(common)
        c2=dict(common,old_id="A.other")
        self.assertEqual(select_one(c1,"exact_body"),"B.b")
        output=evaluate({"benchmark":"fixture","labeling_caution":"fixture","cases":[c1,c2]},
                        seeds=(17,),bootstrap=4)
        base=next(x for x in output["summary"] if x["arm"]=="exact_body")
        guard=next(x for x in output["summary"] if x["arm"]=="guarded_lineage")
        self.assertEqual(base["unjustified_instance_links_on_groups"],2)
        self.assertEqual(guard["unjustified_instance_links_on_groups"],0)


if __name__=="__main__":
    unittest.main()
