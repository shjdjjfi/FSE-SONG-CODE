"""Executable, provenance-pinned replay of an upstream Open WebUI migration.

This is NOT a full-stack Open WebUI installation. It executes the unchanged
upstream Alembic migration body against a minimal, representative SQLite
pre-revision table, and separately runs an in-memory, explicitly labelled
reference patch adapted from open-webui discussion #26635.

No personal or production database is used.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sqlite3
import sys
import time
import traceback
import types
from pathlib import Path
from typing import Any

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from pydantic import BaseModel, ValidationError

UPSTREAM_SHA256 = "9ad51c7b6129683700fce53672b3d69b097de7ac5eb3cb2ce14f7c85eac03698"
ORIGINAL_REVISION = "2f1211949ecc"
TARGET_REVISION = "b10670c03dd5"


class UserProbe(BaseModel):
    id: str
    settings: dict[str, Any] | None
    info: dict[str, Any] | None


SCENARIOS = {
    "zero_users": [],
    "one_valid": [
        {"id": "u0", "info": {"name": "Alice"}, "settings": {"ui": {"version": "0.4.7"}}}
    ],
    "one_empty": [
        {"id": "u0", "info": {}, "settings": {}}
    ],
    "one_null": [
        {"id": "u0", "info": None, "settings": None}
    ],
    "one_custom": [
        {"id": "u0", "info": {"name": "Customer"}, "settings": {"theme": "custom"}}
    ],
    "two_valid": [
        {"id": "u0", "info": {"name": "A"}, "settings": {"ui": {"version": "v0"}}},
        {"id": "u1", "info": {"name": "B"}, "settings": {"ui": {"version": "v1"}}},
    ],
    "three_valid": [
        {"id": f"u{i}", "info": {"i": i}, "settings": {"i": i}}
        for i in range(3)
    ],
}


def reference_patch(source: str) -> str:
    # Exact upstream sites, not a search-and-replace over arbitrary repositories.
    before1 = "sa.update(sa.table(table, sa.column('id'), t_json))"
    after1 = "sa.update(sa.table(table, sa.column('id'), sa.column(f'{column}_json', sa.JSON)))"
    before2 = ".values({f'{column}_json': json.dumps(parsed) if parsed else None})"
    after2 = ".values({f'{column}_json': parsed})"
    if source.count(before1) != 1 or source.count(before2) != 1:
        raise RuntimeError("Upstream migration changed: reference patch is invalid")
    return source.replace(before1, after1).replace(before2, after2)


def load_original_module(source_code: str, label: str, source_path: Path):
    # The target migration contains an unused first-party import. A dummy module
    # allows executing the historical migration without importing the entire web app.
    for name in ("open_webui", "open_webui.internal", "open_webui.internal.db"):
        sys.modules.setdefault(name, types.ModuleType(name))
    mod = types.ModuleType("n22_openwebui_" + label)
    mod.__file__ = str(source_path)
    exec(compile(source_code, str(source_path), "exec"), mod.__dict__)
    assert mod.revision == TARGET_REVISION
    return mod


def schema_rows(db: Path) -> list[list[str]]:
    with sqlite3.connect(db) as con:
        rows = con.execute(
            "SELECT name, sql FROM sqlite_master "
            "WHERE sql IS NOT NULL AND type IN ('table','index','view','trigger') "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        return [[a, b] for a, b in rows]


def setup(db: Path, original_users: list[dict[str, Any]]) -> None:
    with sqlite3.connect(db) as con:
        con.executescript(
            "PRAGMA foreign_keys=ON;"
            "CREATE TABLE user (id TEXT PRIMARY KEY, info TEXT, settings TEXT);"
            "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL);"
            "INSERT INTO alembic_version VALUES ('2f1211949ecc');"
        )
        for user in original_users:
            con.execute(
                "INSERT INTO user (id, info, settings) VALUES (?, ?, ?)",
                (
                    user["id"],
                    json.dumps(user["info"]) if user["info"] is not None else None,
                    json.dumps(user["settings"]) if user["settings"] is not None else None,
                ),
            )
        con.commit()


def execute_migration(mod: types.ModuleType, db: Path) -> tuple[bool, str | None, float]:
    started = time.perf_counter_ns()
    engine = sa.create_engine("sqlite:///" + str(db))
    error = None
    ok = False
    try:
        with engine.connect() as conn:
            conn.execute(sa.text("PRAGMA foreign_keys=ON"))
            operations = Operations(MigrationContext.configure(conn))
            mod.op = operations
            try:
                mod.upgrade()
                # Mimic an Alembic revision ledger advanced after a successful body;
                # this harness does not claim to exercise the full Alembic CLI chain.
                conn.execute(
                    sa.text("UPDATE alembic_version SET version_num=:rev"),
                    {"rev": TARGET_REVISION},
                )
                conn.commit()
                ok = True
            except Exception as exc:
                error = type(exc).__name__ + ": " + str(exc)
                conn.rollback()
    finally:
        engine.dispose()
    elapsed_ms = (time.perf_counter_ns() - started) / 1e6
    return ok, error, elapsed_ms


def inspect(db: Path, original_users: list[dict[str, Any]]) -> dict[str, Any]:
    with sqlite3.connect(db) as con:
        con.row_factory = sqlite3.Row
        names = {r["name"] for r in con.execute("PRAGMA table_info('user')")}
        raw_users = [dict(r) for r in con.execute("SELECT * FROM user ORDER BY id")]
        rev = con.execute("SELECT version_num FROM alembic_version").fetchone()[0]
        generic_json_ok = True
        typed_read_ok = True
        independent_oracle_ok = True
        app_errors = []
        original_by_id = {user["id"]: user for user in original_users}
        for row in raw_users:
            parsed = {}
            for key in ("info", "settings"):
                if key not in names:
                    generic_json_ok = False
                    independent_oracle_ok = False
                    typed_read_ok = False
                    continue
                raw = row[key]
                try:
                    parsed[key] = json.loads(raw) if raw is not None else None
                except (ValueError, TypeError):
                    parsed[key] = raw
                    generic_json_ok = False
                if parsed[key] != original_by_id[row["id"]][key]:
                    independent_oracle_ok = False
            try:
                UserProbe.model_validate({"id": row["id"], **parsed})
            except ValidationError as exc:
                typed_read_ok = False
                app_errors.append(
                    {"user_id": row["id"], "error_types": [e["type"] for e in exc.errors()]}
                )
        return {
            "ledger": rev,
            "user_count": len(raw_users),
            "raw_users": raw_users,
            "generic_json_parse_success": generic_json_ok,
            "typed_pydantic_probe_success": typed_read_ok,
            "oracle_preserves_source_payload": independent_oracle_ok,
            "application_probe_errors": app_errors,
            "schema": schema_rows(db),
            "columns": sorted(names),
        }


def replay(source_path: Path, output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    source_bytes = source_path.read_bytes()
    actual_sha = hashlib.sha256(source_bytes).hexdigest()
    if actual_sha != UPSTREAM_SHA256:
        raise RuntimeError(f"Open WebUI input hash mismatch: {actual_sha}")
    source = source_bytes.decode("utf-8")
    upstream = load_original_module(source, "upstream", source_path)
    fixed_source = reference_patch(source)
    corrected = load_original_module(fixed_source, "reference", source_path)
    matrix = []
    for scenario, users in SCENARIOS.items():
        for arm, mod in (("upstream", upstream), ("reference_patch", corrected)):
            db = output / f"{scenario}__{arm}.sqlite"
            if db.exists():
                db.unlink()
            setup(db, users)
            success, exception, ms = execute_migration(mod, db)
            observed = inspect(db, users)
            matrix.append(
                {
                    "id": f"{scenario}__{arm}",
                    "project": "open-webui",
                    "source_class": "real_upstream_migration_with_controlled_input",
                    "arm": arm,
                    "scenario": scenario,
                    "input_users": users,
                    "success": success,
                    "exception": exception,
                    "migration_ms": round(ms, 3),
                    "sqlite_file": db.name,
                    **observed,
                }
            )
    by_id = {x["id"]: x for x in matrix}
    for scenario in SCENARIOS:
        a = by_id[f"{scenario}__upstream"]
        b = by_id[f"{scenario}__reference_patch"]
        a["same_schema_as_reference"] = a["schema"] == b["schema"]
        a["same_ledger_as_reference"] = a["ledger"] == b["ledger"]
        a["same_row_count_as_reference"] = a["user_count"] == b["user_count"]
        b["same_schema_as_reference"] = True
        b["same_ledger_as_reference"] = True
        b["same_row_count_as_reference"] = True
    summary = {
        "input": {
            "file": "backend/open_webui/migrations/versions/b10670c03dd5_update_user_table.py",
            "tag": "v0.9.6",
            "commit": "1a97751e376e00a1897bc3679215ae1c7bd8fd42",
            "sha256": actual_sha,
            "patch_sha256": hashlib.sha256(fixed_source.encode()).hexdigest(),
            "reference_patch_is_not_an_upstream_release": True,
            "sqlalchemy": sa.__version__,
            "sqlite": sqlite3.sqlite_version,
            "python": platform.python_version(),
        },
        "runs": matrix,
    }
    (output / "openwebui-observations.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = replay(args.source.resolve(), args.output.resolve())
    for row in result["runs"]:
        print(
            row["id"],
            "success=", row["success"],
            "schema_eq=", row["same_schema_as_reference"],
            "ledger_eq=", row["same_ledger_as_reference"],
            "contract=", row["oracle_preserves_source_payload"],
            "app=", row["typed_pydantic_probe_success"],
        )
