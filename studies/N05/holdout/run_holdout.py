#!/usr/bin/env python3
"""Prospective eight-crate package-level validation with frozen N05 method.

These eight packages are outside the 24-package development sample. The code
and ranking rules in scripts/replay.py are not tuned from holdout results.
Run stages in order: collect, select, screen, search, minimize, ablate, audit,
analyze. Results are stored under holdout/ and are never pooled into training.
"""
import argparse
import importlib.util
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parents[1]
HOLDOUT = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / "scripts"))

import collect
import replay
import minimize
import ablations
import audit
import analyze

spec = importlib.util.spec_from_file_location("n05_sample_selector", BASE / "scripts" / "select.py")
select = importlib.util.module_from_spec(spec)
spec.loader.exec_module(select)

FROZEN = [
    ("tower-http", "0.6.6"),
    ("tower", "0.5.2"),
    ("tokio-stream", "0.1.17"),
    ("bytes", "1.10.1"),
    ("dashmap", "6.1.0"),
    ("miette", "7.6.0"),
    ("serde_json", "1.0.140"),
    ("hashbrown", "0.15.4"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["collect", "select", "screen", "search", "minimize", "ablate", "audit", "analyze"])
    args = ap.parse_args()
    collect.DATA = HOLDOUT / "data"
    collect.RAW = collect.DATA / "crates"
    collect.PINNED = FROZEN
    select.DATA = collect.DATA
    replay.DATA = collect.DATA
    replay.RESULTS = HOLDOUT / "results"
    # Reuse only the *compiler build cache*; holdout source & results isolated.
    replay.WORK = BASE / "work"
    minimize.DATA = collect.DATA
    minimize.RESULTS = replay.RESULTS
    ablations.DATA = collect.DATA
    ablations.RESULTS = replay.RESULTS
    audit.DATA = collect.DATA
    audit.RESULTS = replay.RESULTS
    analyze.DATA = collect.DATA
    analyze.RESULTS = replay.RESULTS
    analyze.PAPER = HOLDOUT / "paper"
    if args.stage == "collect":
        collect.main()
    elif args.stage == "select":
        select.main()
    elif args.stage in ("screen", "search"):
        sys.argv = ["replay.py", "--stage", args.stage]
        replay.main()
    elif args.stage == "minimize":
        sys.argv = ["minimize.py"]
        minimize.main()
    elif args.stage == "ablate":
        ablations.main()
    elif args.stage == "audit":
        audit.main()
    elif args.stage == "analyze":
        analyze.main()


if __name__ == "__main__":
    main()
