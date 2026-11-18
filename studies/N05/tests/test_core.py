import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import replay
import minimize
import pathaware
import diagnostic_baseline


class CoreTests(unittest.TestCase):
    def test_hidden_main_is_included(self):
        example = {"compiled_code": "use std::fmt::Debug;\nfn main() {}", "visible_code": "fn main() {}"}
        self.assertIn("use std::fmt", replay.code_for_consumer(example))
        self.assertNotIn("use std::fmt", replay.code_for_consumer(example, visible=True))

    def test_harness_adds_fallible_main(self):
        code = replay.code_for_consumer({"compiled_code": "foo()?;", "visible_code": "foo()?;"})
        self.assertIn("Result<(), Box<dyn std::error::Error>>", code)
        self.assertIn("Ok(())", code)

    def test_default_vs_docs_profiles(self):
        meta = {"crate": "demo", "version": "1.0.0", "feature_names": ["default", "foo", "bar"],
                "docs_metadata": {"features": ["foo"]}}
        self.assertNotIn('"foo"', replay.cargo_manifest(meta, "default"))
        self.assertIn('"foo"', replay.cargo_manifest(meta, "docs"))

    def test_full_feature_closure(self):
        m = {"default_features": [], "feature_map": {"full": ["rt", "io"], "rt": [], "io": []}}
        self.assertEqual(["full", "io", "rt"], minimize.feature_closure(m, ["full"]))

    def test_source_archive_hashes(self):
        if not (ROOT / "data" / "crates_manifest.json").exists():
            self.skipTest("source archives not collected")
        for meta in json.loads((ROOT / "data" / "crates_manifest.json").read_text()):
            path = ROOT / "data" / "crates" / f'{meta["crate"]}-{meta["version"]}.crate'
            self.assertEqual(meta["archive_sha256"], hashlib.sha256(path.read_bytes()).hexdigest())

    def test_pathaware_source_directory_is_generic(self):
        meta = {"crate": "library", "feature_names": ["default", "alpha", "fs", "zzzz"],
                "docs_metadata": {}, "feature_map": {}, "default_features": []}
        row = {"source": "src/services/fs/serve_dir/mod.rs", "raw_code": "library::Foo::new();",
               "compiled_code": "library::Foo::new();", "context_before": ""}
        self.assertEqual(pathaware.candidate_features_v2(meta, row)[0], "fs")
        self.assertEqual(set(pathaware.candidate_features_v2(meta, row)),
                         set(replay.candidate_features(meta, row)))

    def test_prospective_cohort_disjoint_crate_names(self):
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location("prospective_fixed", ROOT / "prospective/run_prospective.py")
        mod = module_from_spec(spec)
        spec.loader.exec_module(mod)
        original = json.loads((ROOT / "data/crates_manifest.json").read_text())
        held = json.loads((ROOT / "holdout/data/crates_manifest.json").read_text())
        old = {r["crate"] for r in original + held}
        self.assertFalse(old.intersection({r[0] for r in mod.FROZEN}))
        self.assertEqual(len(mod.FROZEN), len({r[0] for r in mod.FROZEN}))

    def test_rustc_diagnostic_strong_baseline_extracts_gated_feature(self):
        check = {"errors": [{"rendered": 'error[E0432]: unresolved import\n#[cfg(feature = "fs")]\n  the item is gated behind the `fs` feature'}]}
        meta = {"feature_names": ["default", "fs", "cors", "full"]}
        self.assertEqual(diagnostic_baseline.compiler_feature_hints(check, meta), ["fs"])

    def test_exact_cluster_bootstrap_does_not_overclaim_boundary(self):
        sys.path.insert(0, str(ROOT / "prospective"))
        import validate
        nine_projects = [{"repo": f"independent_{i}", "gain": 1 if i < 3 else 0}
                         for i in range(9)]
        interval = validate.bootstrap(nine_projects, "gain")
        self.assertEqual(interval[0], 0.0)
        self.assertGreater(interval[1], 0.0)

    def test_second_cohort_success_claim_gated_by_exact_interval(self):
        path = ROOT / "prospective/results/independent_validation.json"
        if not path.exists():
            self.skipTest("second cohort not evaluated")
        record = json.loads(path.read_text())
        self.assertEqual(record["searched_feature_profile_mismatches"], 24)
        self.assertEqual(record["strictly_independent_repositories"]["source_repositories"], 9)
        self.assertFalse(record["pre_registered_superiority_criterion_satisfied"])
        self.assertEqual(record["strictly_independent_repositories"]["gain_repository_cluster_bootstrap_95ci"][0], 0.0)


if __name__ == "__main__":
    unittest.main()
