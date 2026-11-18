"""Unittest-style checks of measurement-method identifiability semantics."""

import itertools
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent))

from run_measurement import sharp_delta_bounds,sharp_coverage_bounds
from harvest_issue_events import select_pairs


class MeasurementMath(unittest.TestCase):
    def test_single_expert_worlds_flip_sign(self):
        U={'a','b','c'};A={'a','b'};B={'b','c'}
        self.assertEqual(sharp_delta_bounds(U,A,B,1),[-1.,1.])

    def test_two_experts_shrink_extrema(self):
        U={'a','b','c'};A={'a','b'};B={'b','c'}
        self.assertEqual(sharp_delta_bounds(U,A,B,2),[-.5,.5])

    def test_identical_policies_point_identify_zero(self):
        self.assertEqual(sharp_delta_bounds({'a','b','c'},{'a','b'},{'a','b'},1),[0.,0.])

    def test_observed_reviewer_only_no_suggestion_hit(self):
        self.assertEqual(sharp_coverage_bounds({'z'},{'a','b'},1),[0.,0.])

    def test_actual_candidate_subset_exact_bounds(self):
        self.assertEqual(sharp_coverage_bounds({'a','b','c'},{'a','b'},2),[.5,1.])

    def test_missingness_no_false_point_identification(self):
        self.assertIsNone(sharp_delta_bounds(set(),{'a'},{'b'},1))
        self.assertIsNone(sharp_delta_bounds({'a'},set(),set(),2))

    def test_api_selection_is_reproducible_across_order(self):
        original=json.loads((Path(__file__).resolve().parents[1]/'results/predictions.json').read_text())
        first=[(r['event'],r['repo'],r['pr']) for r in select_pairs(original)]
        second=[(r['event'],r['repo'],r['pr']) for r in select_pairs(list(reversed(original)))]
        self.assertEqual(first,second)
        self.assertEqual(len(first),36)
        self.assertEqual(len({event for event,_,_ in first}),9)

    def test_identification_tightens_when_candidate_world_narrows(self):
        A={'alice','bob'};B={'bob','carol'}
        wide=sharp_delta_bounds({'alice','bob','carol','dave'},A,B,1)
        narrow=sharp_delta_bounds({'bob','carol'},A,B,1)
        self.assertLessEqual(wide[0],narrow[0])
        self.assertGreaterEqual(wide[1],narrow[1])

    def test_identifiability_not_a_confidence_interval(self):
        # Algebraic support can be two-sided even if every public trace is fixed.
        A={'alice'};B={'carol'}
        self.assertEqual(sharp_delta_bounds({'alice','carol'},A,B,1),[-1.,1.])


if __name__=='__main__': unittest.main()
