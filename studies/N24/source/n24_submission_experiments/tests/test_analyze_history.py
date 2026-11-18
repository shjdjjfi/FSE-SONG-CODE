import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from analyze_history import summarize


class UniqueLockfileUnits(unittest.TestCase):
    def test_three_native_parents_count_as_one_version_churn_event(self):
        with tempfile.TemporaryDirectory() as folder:
            p = pathlib.Path(folder) / "runs.json"
            def row(strategy, successes, churn):
                return {"project": "cloudreve", "commit": "frozen",
                        "strategy": strategy,
                        "treatment": {"seconds": 1},
                        "npm_ci": {"returncode": 0},
                        "comparison": {"changed_non_target_versions": churn},
                        "per_parent": {f: {"native_execution_ok": ok,
                                            "coverage": {"host_missing": []}}
                                       for f, ok in zip(("rollup", "esbuild", "swc"), successes)}}
            p.write_text(json.dumps({"host": {"os": "linux"},
                "results": [row("unmodified", (False, False, False), 0),
                            row("npm12-in-place", (True, True, True), 87)]}), encoding="utf-8")
            output = summarize([p])
            self.assertEqual(output["n_project_host_parent_cells"], 3)
            self.assertEqual(output["n_unique_project_host_lockfiles"], 1)
            fixed = output["strategy_summary"]["npm12-in-place"]
            self.assertEqual(fixed["n_package_host_cells"], 3)
            self.assertEqual(fixed["n_unique_project_host_lockfiles"], 1)
            self.assertEqual(fixed["non_target_version_churn_unique_lockfiles_total"], 87)
            self.assertEqual(fixed["all_native_parents_pass_n"], 1)


if __name__ == "__main__":
    unittest.main()
