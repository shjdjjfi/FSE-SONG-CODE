#!/usr/bin/env python3
"""Freeze experiment environment and transitive Cargo lockfiles."""
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
DATA = ROOT / "data"


def command_version(command):
    if not shutil.which(command[0]) and not Path(command[0]).exists():
        return None
    try:
        env = os.environ.copy()
        env["RUSTUP_HOME"] = str(ROOT.parent / "tools" / "rustup-home")
        env["CARGO_HOME"] = str(ROOT.parent / "tools" / "cargo-home")
        env["PATH"] = str(ROOT.parent / "tools" / "cargo-home" / "bin") + os.pathsep + env.get("PATH", "")
        result = subprocess.run(command, capture_output=True, text=True, timeout=12, env=env)
        return (result.stdout or result.stderr).strip().splitlines()[0]
    except (subprocess.SubprocessError, IndexError):
        return None


def main():
    cargo = ROOT.parent / "tools" / "cargo-home" / "bin" / "cargo"
    rustc = ROOT.parent / "tools" / "cargo-home" / "bin" / "rustc"
    data_locks = DATA / "locks"
    data_locks.mkdir(parents=True, exist_ok=True)
    locks = []
    for entry in sorted((ROOT / "work" / "consumers").glob("*/Cargo.lock")):
        target = data_locks / (entry.parent.name + ".lock")
        shutil.copyfile(entry, target)
        locks.append({"crate": entry.parent.name, "file": str(target.relative_to(ROOT)),
                      "sha256": hashlib.sha256(target.read_bytes()).hexdigest()})
    environment = {
        "study": "N05-v1",
        "host_os": platform.system(), "platform": platform.platform(),
        "architecture": platform.machine(), "python": sys.version.split()[0],
        "logical_cpus": os.cpu_count(),
        "cargo": command_version([str(cargo), "+1.91.0", "--version"]),
        "rustc": command_version([str(rustc), "+1.91.0", "--version"]),
        "gcc": command_version(["gcc", "--version"]),
        "target": "x86_64-unknown-linux-gnu", "cargo_build_jobs": 4,
        "toolchain_pinned": "1.91.0", "per_invocation_timeout_seconds": 180,
        "source_archive_count": len(list((DATA / "crates").glob("*.crate"))),
        "lockfiles": locks,
    }
    (RESULTS / "environment.json").write_text(json.dumps(environment, indent=2) + "\n")
    print(f"Archived {len(locks)} Cargo lockfiles and compiler environment")


if __name__ == "__main__":
    main()
