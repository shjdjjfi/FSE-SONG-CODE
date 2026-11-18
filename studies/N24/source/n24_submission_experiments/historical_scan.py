#!/usr/bin/env python3
"""Read-only provenance-backed audit of publicly committed npm lockfiles.

No install, mutations of upstream repositories, or CI outcome claims. Commit
SHAs are resolved once and saved for permanent re-fetch; use --frozen to rerun
against the identical inputs without querying moving branch names.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


FAMILIES = {
    "rollup": ("rollup", "@rollup/rollup-"),
    "esbuild": ("esbuild", "@esbuild/"),
    "biome": ("@biomejs/biome", "@biomejs/cli-"),
    "swc": ("@swc/core", "@swc/core-"),
    "lightningcss": ("lightningcss", "lightningcss-"),
}


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "fse-n24-public-lock-audit/1.0",
                                                    "Accept": "application/vnd.github+json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=35) as response:
                return response.read()
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep(attempt + 1)
    raise AssertionError("unreachable")


def classify(lock: dict) -> dict:
    packages = lock.get("packages")
    if not isinstance(packages, dict):
        return {"parseable_packages": False, "instances": [], "n_packages": 0}
    instances = []
    for path, node in sorted(packages.items()):
        if not isinstance(node, dict):
            continue
        for label, (parent, prefix) in FAMILIES.items():
            if path != "node_modules/" + parent and not path.endswith("/node_modules/" + parent):
                continue
            optional = node.get("optionalDependencies", {})
            if not isinstance(optional, dict):
                continue
            names = sorted(x for x in optional if x.startswith(prefix))
            if not names:
                continue
            present, absent, partial, nested = [], [], [], []
            for name in names:
                direct = "node_modules/" + name
                # Other locations are not automatically resolvable from this parent.
                located = [key for key in packages if key.endswith(direct)]
                if direct in packages:
                    entry = packages[direct]
                    if entry.get("version") and entry.get("integrity") and entry.get("resolved"):
                        present.append(name)
                    else:
                        partial.append(name)
                elif located:
                    nested.append({"name": name, "locations": located[:3]})
                else:
                    absent.append(name)
            instances.append({"family": label, "parent_path": path,
                              "parent_version": node.get("version"),
                              "declared": len(names), "complete_hoisted": len(present),
                              "missing_from_all_lock_nodes": absent,
                              "incomplete_metadata": partial,
                              "present_only_nested": nested,
                              "scope": "structural lockfile audit only; not proof that a CI failure occurred"})
    return {"parseable_packages": True, "n_packages": len(packages), "instances": instances}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", default=str(Path(__file__).with_name("historical_sources.json")), type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--frozen", type=Path, help="Previously emitted freeze.json (requires pinned exact SHA)")
    args = ap.parse_args()
    source = json.loads(args.sources.read_text(encoding="utf-8"))
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    freeze = json.loads(args.frozen.read_text(encoding="utf-8")) if args.frozen else None
    frozen_by_key = {(r["repo"], r["path"]): r["sha"] for r in freeze["entries"]} if freeze else {}
    entries = []
    for entry in source["sources"]:
        repo, ref, path = entry["repo"], entry["ref"], entry["path"]
        obs = {"repo": repo, "source_ref": ref, "path": path}
        try:
            pinned = frozen_by_key.get((repo, path))
            if not pinned:
                if len(ref) == 40 and all(c in "0123456789abcdef" for c in ref.lower()):
                    pinned = ref
                else:
                    api = f"https://api.github.com/repos/{repo}/commits/{urllib.parse.quote(ref, safe='')}"
                    pinned = json.loads(fetch(api))["sha"]
            if not (len(pinned) == 40 and all(c in "0123456789abcdef" for c in pinned.lower())):
                raise ValueError("Resolved invalid SHA")
            obs["sha"] = pinned
            url = f"https://raw.githubusercontent.com/{repo}/{pinned}/{path}"
            blob = fetch(url)
            obs.update({"url": url, "bytes": len(blob), "sha256": hashlib.sha256(blob).hexdigest()})
            lock = json.loads(blob)
            obs.update({"lockfile_version": lock.get("lockfileVersion"), **classify(lock)})
            local_name = repo.replace("/", "_") + "_" + hashlib.sha256(path.encode()).hexdigest()[:6] + ".json"
            (output / "snapshots").mkdir(exist_ok=True)
            (output / "snapshots" / local_name).write_bytes(blob)
        except Exception as e:
            obs["error"] = str(e)
        entries.append(obs)
        print(json.dumps({"repo": repo, "sha": obs.get("sha"),
                          "parent_instances": len(obs.get("instances", [])),
                          "missing": sum(len(i["missing_from_all_lock_nodes"]) for i in obs.get("instances", [])),
                          "error": obs.get("error")}), flush=True)
        (output / "freeze.json").write_text(json.dumps({"entries": entries}, indent=2) + "\n", encoding="utf-8")
    usable = [o for o in entries if not o.get("error") and o.get("parseable_packages")]
    summary = {"date_utc": "2026-11-18", "sample_class": "search-discovered public GitHub projects, convenience sample",
               "n_selected": len(entries), "n_usable": len(usable), "n_failed_to_fetch_or_parse": len(entries) - len(usable),
               "n_parents": sum(len(x["instances"]) for x in usable),
               "n_parents_with_missing_variants": sum(bool(i["missing_from_all_lock_nodes"]) for x in usable for i in x["instances"]),
               "n_missing_variant_refs": sum(len(i["missing_from_all_lock_nodes"]) for x in usable for i in x["instances"]),
               "entries": entries,
               "limits": ["No sampled GitHub lock is labeled a real CI failure without matching original CI logs",
                          "Missing optional variant entries are at-risk structural gaps, not demonstrated failed applications",
                          "Convenience sample is not an estimate of ecosystem prevalence",
                          "Public repo path/ref failures are recorded, not silently dropped"]}
    (output / "scan.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k.startswith("n_")}, indent=2))


if __name__ == "__main__":
    main()
