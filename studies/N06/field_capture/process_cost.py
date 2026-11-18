"""Record observed CPU/RSS of a REAL, already-running Linux alert process.

This observer only reads /proc. Running it against a synthetic local replay
does not turn those numbers into a production-overhead measurement.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import os
import time


def process_values(pid: int) -> tuple[float, float, int]:
    raw = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
    # comm is enclosed in parentheses and may itself contain spaces.
    fields = raw[raw.rfind(")") + 2:].split()
    utime, stime, starttime = int(fields[11]), int(fields[12]), int(fields[19])
    clock_ticks = os.sysconf("SC_CLK_TCK")
    status = Path(f"/proc/{pid}/status").read_text(encoding="utf-8")
    rss_kb = next((int(line.split()[1]) for line in status.splitlines()
                   if line.startswith("VmRSS:")), 0)
    return (utime + stime) / clock_ticks, rss_kb / 1024, starttime


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--cluster-id", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seconds", type=float, default=1800)
    parser.add_argument("--interval", type=float, default=5)
    args = parser.parse_args()
    if args.seconds <= 0 or args.interval <= 0 or args.pid <= 0:
        parser.error("positive seconds, interval and pid are required")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    last_cpu, _, starttime = process_values(args.pid)
    samples = 0
    with args.out.open("a", encoding="utf-8") as stream:
        while time.monotonic() - started < args.seconds:
            time.sleep(min(args.interval, max(0, args.seconds - (time.monotonic() - started))))
            try:
                cpu, rss, current_start = process_values(args.pid)
            except OSError:
                print("Monitored process exited; no further live-process measurements")
                break
            if current_start != starttime:
                print("PID reused; measurement stopped to avoid mixing processes")
                break
            row = {"collector_kind": "live_process", "measured_at": datetime.now(timezone.utc).isoformat(),
                   "cluster_id": args.cluster_id, "policy": args.policy,
                   "pid": args.pid, "cpu_seconds_per_interval": round(max(0, cpu - last_cpu), 6),
                   "resident_memory_mb": round(rss, 3), "interval_seconds": args.interval}
            stream.write(json.dumps(row, separators=(",", ":")) + "\n")
            stream.flush()
            samples += 1
            last_cpu = cpu
    print(json.dumps({"samples": samples, "out": str(args.out)}))
    return 0 if samples else 2


if __name__ == "__main__":
    raise SystemExit(main())
