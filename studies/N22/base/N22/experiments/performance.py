"""Local scaling of schema, untyped-row, and semantic-data SQL gates.

This generates synthetic rows only. It measures a local SQLite read query, NOT
production deployment latency, CI cost, or human engineering time.
"""

from __future__ import annotations

import argparse
import json
import platform
import sqlite3
import statistics
import time
from pathlib import Path


QUERIES = {
    "schema_plus_ledger": (
        "SELECT name,sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY name",
        "SELECT name FROM migration_ledger ORDER BY name",
    ),
    "row_count": (
        "SELECT COUNT(*) FROM user_profile",
        "SELECT COUNT(*) FROM child",
    ),
    "contract_type_and_links": (
        "SELECT COUNT(*) FROM user_profile WHERE settings IS NOT NULL "
        "AND json_valid(settings)=1 AND json_type(settings) <> 'object'",
        "SELECT COUNT(*) FROM child c LEFT JOIN parent p ON p.id=c.parent_id "
        "WHERE c.parent_id IS NULL OR p.id IS NULL",
    ),
}


def make_db(path: Path, n: int) -> None:
    if path.exists():
        path.unlink()
    con = sqlite3.connect(path)
    con.executescript(
        "CREATE TABLE user_profile(id INTEGER PRIMARY KEY,settings TEXT);"
        "CREATE TABLE parent(id INTEGER PRIMARY KEY);"
        "CREATE TABLE child(id INTEGER PRIMARY KEY,parent_id INTEGER,payload TEXT);"
        "CREATE TABLE migration_ledger(name TEXT PRIMARY KEY);"
        "INSERT INTO migration_ledger VALUES ('target');"
    )
    con.executemany("INSERT INTO parent(id) VALUES (?)", ((i,) for i in range(n)))
    con.executemany(
        "INSERT INTO child(id,parent_id,payload) VALUES (?,?,?)",
        ((i, i, "message") for i in range(n)),
    )
    con.executemany(
        "INSERT INTO user_profile(id,settings) VALUES (?,?)",
        ((i, '{"ui":{"theme":"dark"}}') for i in range(n)),
    )
    con.commit()
    con.close()


def sample(path: Path, queries: tuple[str, ...], rounds: int) -> dict:
    con = sqlite3.connect(path)
    durations = []
    for i in range(rounds + 10):
        start = time.perf_counter_ns()
        for query in queries:
            con.execute(query).fetchall()
        elapsed = (time.perf_counter_ns() - start) / 1e6
        if i >= 10:
            durations.append(elapsed)
    con.close()
    durations.sort()
    return {
        "rounds": rounds,
        "median_ms": round(statistics.median(durations), 4),
        "p95_ms": round(durations[int(rounds * 0.95)], 4),
        "max_ms": round(durations[-1], 4),
    }


def run(output: Path, rounds: int = 30) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    all_sizes = []
    for n in (0, 100, 1000, 10000):
        db_path = output / f"synthetic_n{n}.sqlite"
        make_db(db_path, n)
        all_sizes.append(
            {
                "rows_per_application_table": n,
                "db_bytes": db_path.stat().st_size,
                "gates": {name: sample(db_path, statements, rounds)
                          for name, statements in QUERIES.items()},
            }
        )
    result = {
        "scope": "synthetic local scale, not real projects or industrial ROI",
        "environment": {
            "python": platform.python_version(),
            "sqlite": sqlite3.sqlite_version,
            "platform": platform.platform(),
        },
        "sizes": all_sizes,
    }
    (output / "performance.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    cli = argparse.ArgumentParser()
    cli.add_argument("--output", type=Path, required=True)
    cli.add_argument("--rounds", type=int, default=30)
    args = cli.parse_args()
    r = run(args.output.resolve(), args.rounds)
    for entry in r["sizes"]:
        print(entry["rows_per_application_table"], entry["db_bytes"], entry["gates"])
