import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from historical_scan import classify


class HistoricalScannerContract(unittest.TestCase):
    def test_counts_structural_gap_without_claiming_failure(self):
        lock = {"packages": {"node_modules/rollup": {"version": "4.0.0",
            "optionalDependencies": {"@rollup/rollup-linux-x64-gnu": "4.0.0",
                                     "@rollup/rollup-darwin-arm64": "4.0.0"}},
            "node_modules/@rollup/rollup-linux-x64-gnu": {"version": "4.0.0", "resolved": "https://example.com/tgz", "integrity": "sha512-..."}}}
        obs = classify(lock)
        self.assertEqual(len(obs["instances"]), 1)
        self.assertEqual(obs["instances"][0]["missing_from_all_lock_nodes"], ["@rollup/rollup-darwin-arm64"])
        self.assertEqual(obs["instances"][0]["complete_hoisted"], 1)

    def test_does_not_turn_nonnative_or_unparseable_v1_into_gap(self):
        self.assertFalse(classify({"dependencies": {"x": {}}})["parseable_packages"])
        self.assertEqual(classify({"packages": {"node_modules/esbuild": {"optionalDependencies": {"fsevents": "^2"}}}})["instances"], [])


if __name__ == "__main__":
    unittest.main()
