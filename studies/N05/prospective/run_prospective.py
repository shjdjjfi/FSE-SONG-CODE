#!/usr/bin/env python3
"""Second independent package evaluation, with frozen versions and methods."""
import argparse
import importlib.util
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parents[1]
COHORT = Path(__file__).resolve().parent
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

# Unseen crate names and fixed releases. Never select on a compiler outcome.
FROZEN = [
    ("serde_with", "3.12.0"),
    ("redis", "0.32.1"),
    ("mio", "1.0.4"),
    ("async-compression", "0.4.23"),
    ("hyper-util", "0.1.15"),
    ("tonic", "0.13.1"),
    ("rand_distr", "0.5.1"),
    ("ulid", "1.2.1"),
    ("semver", "1.0.26"),
    ("time", "0.3.41"),
    ("rust_decimal", "1.37.2"),
    ("chrono-tz", "0.10.3"),
    ("deadpool", "0.12.2"),
    ("slog", "2.7.0"),
    ("ratatui", "0.29.0"),
    ("crossterm", "0.28.1"),
    ("config", "0.15.11"),
    ("validator", "0.20.0"),
    ("utoipa", "5.3.1"),
    ("schemars", "0.8.22"),
    ("quick-xml", "0.37.5"),
    ("notify", "8.0.0"),
    ("http-body-util", "0.1.3"),
    ("clap_complete", "4.5.55"),
    ("bincode", "2.0.1"),
    ("sqlparser", "0.56.0"),
    ("sea-query", "0.32.5"),
    ("figment", "0.10.19"),
    ("opentelemetry", "0.29.1"),
    ("poem", "3.1.12"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["collect", "select", "screen", "search", "minimize", "ablate", "audit", "analyze"])
    ap.add_argument("--limit", type=int, default=0, help="explicitly incomplete preflight only")
    args = ap.parse_args()
    collect.DATA = COHORT / "data"
    collect.RAW = collect.DATA / "crates"
    collect.PINNED = FROZEN
    select.DATA = collect.DATA
    replay.DATA = collect.DATA
    replay.RESULTS = COHORT / "results"
    replay.WORK = BASE / "work"
    minimize.DATA = collect.DATA
    minimize.RESULTS = replay.RESULTS
    ablations.DATA = collect.DATA
    ablations.RESULTS = replay.RESULTS
    audit.DATA = collect.DATA
    audit.RESULTS = replay.RESULTS
    analyze.DATA = collect.DATA
    analyze.RESULTS = replay.RESULTS
    analyze.PAPER = COHORT / "paper"
    if args.stage == "collect":
        collect.main()
    elif args.stage == "select":
        select.main()
    elif args.stage in ("screen", "search"):
        sys.argv = ["replay.py", "--stage", args.stage]
        if args.limit:
            sys.argv.extend(["--limit", str(args.limit)])
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
