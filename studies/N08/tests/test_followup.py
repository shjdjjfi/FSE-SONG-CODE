"""Non-inferential sanity checks for new N08 follow-up methods."""

import sys
import unittest
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))

from augment_evidence import summarize_patch  # noqa: E402
from experiment_cv import best_param, scores_for, DEFAULT  # noqa: E402


class FollowupTests(unittest.TestCase):
    def test_patch_logic_and_other_files_not_conflated(self):
        patch=b'''diff --git a/old/a.ts b/new/a.ts
@@ -1,1 +1,1 @@
-if (foo) return true;
+if (bar) return false;
diff --git a/other/b.ts b/other/b.ts
@@ -1,1 +1,1 @@
-return false;
+return true;
'''
        s=summarize_patch(patch,'new/')
        self.assertEqual(s['target_code_changed_lines'],2)
        self.assertEqual(s['target_files'],['new/a.ts'])
        self.assertEqual(s['automated_code_semantic_signal_only'],'present')

    def test_no_code_false_substance_proof(self):
        patch=b'''diff --git a/new/README.md b/new/README.md
@@ -1,1 +1,1 @@
-old docs
+new docs
'''
        s=summarize_patch(patch,'new/')
        self.assertEqual(s['target_code_changed_lines'],0)
        self.assertEqual(s['automated_code_semantic_signal_only'],'undetermined')

    def test_cross_path_scores_exclude_target_author(self):
        f={'decay':1., 'source_review':Counter({'author':100,'legacy':2}),
           'target_review':Counter({'new':3}),
           'source_requests':Counter(), 'target_requests':Counter(),
           'source_commits':Counter(), 'target_commits':Counter(),
           'global_pop':Counter({'author':100,'legacy':2,'new':3}),
           'pr_author':'author'}
        self.assertEqual(scores_for(f,(1.,0.,0.)),['new','legacy'])
        self.assertNotIn('author',scores_for(f,(1.,0.,0.)))

    def test_expires_source_in_hybrid(self):
        f={'decay':0., 'source_review':Counter({'legacy':30}),
           'target_review':Counter({'new':3}),
           'source_requests':Counter({'legacy':10}), 'target_requests':Counter(),
           'source_commits':Counter({'legacy':10}), 'target_commits':Counter(),
           'global_pop':Counter({'legacy':5,'new':3,'pool':1}),
           'pr_author':'someauthor'}
        self.assertEqual(scores_for(f,(2.,1.,1.)),['new','legacy'])

    def test_unseen_no_training_defaults(self):
        self.assertEqual(best_param([]),DEFAULT)


if __name__=='__main__': unittest.main()
