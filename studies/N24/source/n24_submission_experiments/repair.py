"""Auditable, intentionally narrow v3 npm optional-platform leaf repair.

No network I/O happens here. Caller obtains an independently generated donor
lock for the *same exact published parent version*. Failing closed is part of
the specification: this is not a general npm dependency resolver.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any


class RepairRejected(ValueError):
    pass


def repair_lock(original: dict[str, Any], donor: dict[str, Any], parent: str) -> tuple[dict, dict]:
    root = "node_modules/" + parent
    original_packages = original.get("packages")
    donor_packages = donor.get("packages")
    if original.get("lockfileVersion") != 3 or donor.get("lockfileVersion") != 3:
        raise RepairRejected("Only npm lockfile v3 supported")
    if not isinstance(original_packages, dict) or not isinstance(donor_packages, dict):
        raise RepairRejected("Missing packages mapping")
    before_parent, donor_parent = original_packages.get(root), donor_packages.get(root)
    if not isinstance(before_parent, dict) or not isinstance(donor_parent, dict):
        raise RepairRejected("Named parent not present in both locks at root node_modules path")
    if not before_parent.get("version") or before_parent["version"] != donor_parent.get("version"):
        raise RepairRejected("Donor parent version differs from locked exact parent")
    expected = before_parent.get("optionalDependencies", {})
    if not isinstance(expected, dict) or expected != donor_parent.get("optionalDependencies", {}):
        raise RepairRejected("Donor and original parent optional-dependency declarations disagree")
    updated = deepcopy(original)
    patch = updated["packages"]
    added, already, skipped = [], [], {}
    for name, spec in sorted(expected.items()):
        # Avoid rewriting unrelated optional dependencies or package-manager metadata.
        key = "node_modules/" + name
        found = patch.get(key)
        if found is not None:
            if not isinstance(found, dict) or not found.get("version") or not found.get("integrity"):
                skipped[name] = "incomplete existing entry; requires resolver/human review"
            else:
                already.append(name)
            continue
        data = donor_packages.get(key)
        if not isinstance(data, dict):
            skipped[name] = "not a hoisted direct optional leaf in donor"
            continue
        if not (data.get("os") and data.get("cpu") and data.get("integrity") and
                data.get("resolved") and data.get("version")):
            skipped[name] = "missing platform, exact version, resolved URL or integrity"
            continue
        if not str(data["resolved"]).startswith("https://registry.npmjs.org/"):
            skipped[name] = "non-public or untrusted resolved registry URL"
            continue
        if spec != data["version"]:  # exact version constraints only
            skipped[name] = "parent does not pin donor variant to its exact version"
            continue
        if data.get("dependencies") or data.get("peerDependencies") or data.get("optionalDependencies"):
            skipped[name] = "non-leaf optional variant; requires full resolver"
            continue
        if data.get("link") or data.get("hasInstallScript"):
            skipped[name] = "link/install-script variant outside leaf-only policy"
            continue
        patch[key] = deepcopy(data)
        added.append(name)
    info = {"parent": parent, "parent_version": before_parent["version"],
            "expected_optional_count": len(expected), "added": added,
            "already_present": already, "skipped": skipped,
            "changed_existing_paths": [], "changed_non_target_versions": 0}
    for key, entry in original_packages.items():
        if key not in patch or patch[key] != entry:
            raise AssertionError("The repair modified or removed an existing lockfile node")
    return updated, info
