"""Controlled mechanism and leakage tests; not empirical outcome evidence."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from analyze import exact_sign_flip, is_handoff, recommend, reviewer_counts, reviewed_users  # noqa: E402
from harvest import owner_for, parse_patch_renames, review_timeline  # noqa: E402
from audit_requests import parse_author, parse_requests  # noqa: E402


class N08Tests(unittest.TestCase):
    def test_owner_precedence(self):
        s = '* @org/all\na/ @org/old\na/target @org/new\n'
        self.assertEqual(owner_for('a/src/x.py', s), ['@org/old'])
        self.assertEqual(owner_for('a/target/file.py', s), ['@org/new'])

    def test_git_rename_pair(self):
        x = 'rename from legacy/a.py\nrename to modern/a.py\nrename from old/b.py\nrename to new/b.py\n'
        self.assertEqual(parse_patch_renames(x)[1], {'old': 'old/b.py', 'new': 'new/b.py'})

    def test_no_same_team_handoff(self):
        self.assertFalse(is_handoff(['@org/a'], ['@org/a'], [{'old': 'a', 'new': 'b'}]))
        self.assertFalse(is_handoff(['@org/a'], ['@org/b'], [], substantive=True))
        self.assertFalse(is_handoff(['@org/a'], ['@org/b'], [{'old': 'a', 'new': 'b'}], substantive=False))
        self.assertTrue(is_handoff(['@org/a'], ['@org/b'], [{'old': 'a', 'new': 'b'}]))
        self.assertTrue(is_handoff(['@org/a', '@org/b'], ['@org/b'], [{'old': 'a', 'new': 'b'}]))

    def test_review_parser_extracts_submitted_time(self):
        html = '''<div class="TimelineItem"><a class="TimelineItem-avatar" href="/alice"></a>
          alice approved these changes <relative-time datetime="2025-01-01T03:00:00Z"></relative-time></div>
          <div class="TimelineItem">bob merged commit deadbee
          <relative-time datetime="2025-01-03T00:00:00Z"></relative-time></div>'''
        opened, merged, reviews = review_timeline(html)
        self.assertEqual(merged, '2025-01-03T00:00:00Z')
        self.assertEqual(reviews, [{'login': 'alice', 'state': 'APPROVED', 'submitted_at': '2025-01-01T03:00:00Z'}])

    def test_pr_author_excluded_and_request_parsed(self):
        body = '''<a class="author Link--primary" href="/alice">alice</a>
        <div class="TimelineItem"><a class="TimelineItem-avatar" href="/alice"></a>
        <a href="/alice">alice</a> requested review from <a href="/bob">bob</a>
        <relative-time datetime="2025-01-01T01:00:00Z"></relative-time></div>'''
        self.assertEqual(parse_author(body), 'alice')
        self.assertEqual(parse_requests(body)[0]['requested_people'], ['bob'])
        self.assertEqual(recommend('git_follow', {'alice': 10, 'bob': 2}, {}, {}, 2, k=1,
                                   excluded_user='alice'), ['bob'])

    def test_after_merge_review_does_not_count(self):
        pr = {'merged_at': '2025-01-02T00:00:00Z', 'reviews': [
            {'login': 'Alice', 'state': 'APPROVED', 'submitted_at': '2025-01-01T00:00:00Z'},
            {'login': 'Bob', 'state': 'APPROVED', 'submitted_at': '2025-01-03T00:00:00Z'}]}
        self.assertEqual(reviewed_users(pr), {'alice'})

    def test_target_review_future_is_not_training(self):
        past = {'merged_at': '2025-01-02T00:00:00Z', 'reviews': [
            {'login': 'alice', 'state': 'APPROVED', 'submitted_at': '2025-01-01T00:00:00Z'}]}
        future = {'merged_at': '2025-01-08T00:00:00Z', 'reviews': [
            {'login': 'bob', 'state': 'APPROVED', 'submitted_at': '2025-01-06T00:00:00Z'}]}
        from analyze import parse_time
        t = parse_time('2025-01-04T00:00:00Z')
        self.assertEqual(dict(reviewer_counts([past, future], t)), {'alice': 1})

    def test_handoff_expires(self):
        src = {'legacy': 8}
        new = {'new': 2}
        pop = {'legacy': 8, 'new': 4}
        self.assertEqual(recommend('windowed_handoff', src, new, pop, days_since=1, k=1), ['legacy'])
        self.assertEqual(recommend('windowed_handoff', src, new, pop, days_since=181, k=1), ['new'])
        self.assertEqual(recommend('git_follow', src, new, pop, days_since=181, k=1), ['legacy'])

    def test_exact_sign_flips_small_sample(self):
        self.assertEqual(exact_sign_flip([0., 0.]), 1.0)
        self.assertEqual(exact_sign_flip([1., 1.]), .5)


if __name__ == '__main__':
    unittest.main()
