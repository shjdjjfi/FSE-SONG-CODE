"""Measured LOCAL Python mechanism cost on SYNTHETIC Pod objects, not production overhead."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import sys
import time
import tracemalloc

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.simulator import Observation, Pod, Policy  # noqa: E402


def run_one(policy_name: str, pods: int, ticks: int) -> dict:
    # All methods receive identical observations with distinct stable owners.
    values = tuple(Pod(f"pod-{i}", f"deployment-{i // 50}", bool(i % 7 == 0))
                   for i in range(pods))
    p = Policy(policy_name, hold_ticks=40)
    tracemalloc.start()
    begin = time.perf_counter()
    for t in range(ticks):
        p.step(Observation(time=t, pods=values, rollouts=(), probe_bad=None))
    elapsed = time.perf_counter() - begin
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {"policy": policy_name, "synthetic_pod_count": pods, "ticks": ticks,
            "wall_seconds": round(elapsed, 6),
            "microseconds_per_pod_tick": round(elapsed / (pods * ticks) * 1e6, 5),
            "peak_python_allocation_mb": round(peak / 1024 ** 2, 4)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "results_field/local_python_benchmark.json")
    parser.add_argument("--sizes", default="100,1000,10000")
    parser.add_argument("--ticks", type=int, default=12)
    args = parser.parse_args()
    sizes = [int(x) for x in args.sizes.split(",")]
    if args.ticks < 2 or not sizes or min(sizes) < 1 or max(sizes) > 100000:
        parser.error("ticks >= 2, 1 <= pod sizes <= 100000")
    records = [run_one(policy, n, args.ticks) for n in sizes
               for policy in ("owner_lookback", "owner_relink_v2")]
    payload = {"kind": "LOCAL_SYNTHETIC_MECHANISM_BENCHMARK_NOT_PRODUCTION",
               "captured_at": datetime.now(timezone.utc).isoformat(),
               "python": platform.python_version(), "host": platform.platform(),
               "results": records}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"result_count": len(records), "out": str(args.out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
