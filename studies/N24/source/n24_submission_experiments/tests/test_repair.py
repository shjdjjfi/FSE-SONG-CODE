import copy
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from repair import repair_lock, RepairRejected


def fixture():
    parent = {"version": "1.2.3", "optionalDependencies": {"@demo/linux-x64": "1.2.3"}}
    child = {"version": "1.2.3", "resolved": "https://registry.npmjs.org/@demo/linux-x64/-/linux-x64-1.2.3.tgz",
             "integrity": "sha512-realistic-but-test-only", "os": ["linux"], "cpu": ["x64"], "optional": True}
    original = {"name": "x", "lockfileVersion": 3,
                "packages": {"": {"dependencies": {"demo": "1.2.3"}}, "node_modules/demo": parent}}
    donor = copy.deepcopy(original)
    donor["packages"]["node_modules/@demo/linux-x64"] = child
    return original, donor


class RepairContract(unittest.TestCase):
    def test_adds_one_full_integrity_checked_leaf_and_preserves_original(self):
        original, donor = fixture()
        untouched = copy.deepcopy(original)
        repaired, audit = repair_lock(original, donor, "demo")
        self.assertEqual(original, untouched)
        self.assertEqual(audit["added"], ["@demo/linux-x64"])
        self.assertEqual(repaired["packages"]["node_modules/@demo/linux-x64"],
                         donor["packages"]["node_modules/@demo/linux-x64"])

    def test_idempotent_and_negative_control(self):
        original, donor = fixture()
        once, _ = repair_lock(original, donor, "demo")
        twice, info = repair_lock(once, donor, "demo")
        self.assertEqual(once, twice)
        self.assertEqual(info["added"], [])

    def test_rejects_changed_parent_version(self):
        original, donor = fixture()
        donor["packages"]["node_modules/demo"]["version"] = "2.0.0"
        with self.assertRaises(RepairRejected):
            repair_lock(original, donor, "demo")

    def test_rejects_changed_parent_declaration(self):
        original, donor = fixture()
        donor["packages"]["node_modules/demo"]["optionalDependencies"].clear()
        with self.assertRaises(RepairRejected):
            repair_lock(original, donor, "demo")

    def test_skips_non_leaf(self):
        original, donor = fixture()
        donor["packages"]["node_modules/@demo/linux-x64"]["dependencies"] = {"lib": "^2.0.0"}
        output, audit = repair_lock(original, donor, "demo")
        self.assertEqual(original, output)
        self.assertIn("non-leaf", audit["skipped"]["@demo/linux-x64"])

    def test_skips_non_exact_or_untrusted_or_missing_integrity(self):
        for kind in ("range", "url", "integrity"):
            with self.subTest(kind=kind):
                original, donor = fixture()
                child = donor["packages"]["node_modules/@demo/linux-x64"]
                if kind == "range":
                    original["packages"]["node_modules/demo"]["optionalDependencies"]["@demo/linux-x64"] = "^1.2.3"
                    donor["packages"]["node_modules/demo"]["optionalDependencies"]["@demo/linux-x64"] = "^1.2.3"
                if kind == "url": child["resolved"] = "https://private.example/registry"
                if kind == "integrity": child.pop("integrity")
                output, audit = repair_lock(original, donor, "demo")
                self.assertEqual(original, output)
                self.assertIn("@demo/linux-x64", audit["skipped"])

    def test_incomplete_existing_entry_not_silently_overwritten(self):
        original, donor = fixture()
        original["packages"]["node_modules/@demo/linux-x64"] = {"optional": True}
        output, audit = repair_lock(original, donor, "demo")
        self.assertEqual(output, original)
        self.assertIn("incomplete", audit["skipped"]["@demo/linux-x64"])

    def test_v2_refused(self):
        original, donor = fixture()
        original["lockfileVersion"] = 2
        with self.assertRaises(RepairRejected):
            repair_lock(original, donor, "demo")


if __name__ == "__main__":
    unittest.main()
