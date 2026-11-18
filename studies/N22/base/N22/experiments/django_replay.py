"""Django 5.1.8 real migration runner: positive execution-order boundary + controls.

The PetterS/django-demo-app input is a real issue reproducer for Django #29843.
It demonstrates an immediate migration exception, NOT a silent same-ledger defect.
The built-in sites example exercises legitimate user customization and the
original N22 ZIP's negative-control scope on a fresh host.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import django

PETTER_COMMIT = "8c62fd7c54a894d251679ab2b2f27138166380f9"

SITE_RUNNER = r"""
import json
import sys
from django.conf import settings
settings.configure(
    DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": sys.argv[1]}},
    INSTALLED_APPS=["django.contrib.sites", "django.contrib.redirects", "django.contrib.flatpages"],
    SITE_ID=1, SECRET_KEY="n22-internal-sample-only", USE_TZ=True,
)
import django
django.setup()
from django.core.management import call_command
from django.contrib.sites.models import Site

mode=sys.argv[2]
if mode == "fresh":
    call_command("migrate", interactive=False, verbosity=0)
else:
    call_command("migrate", "sites", "0001", interactive=False, verbosity=0)
    if mode == "staged-user-row":
        Site.objects.filter(pk=1).update(domain="customer.example", name="Customer")
    call_command("migrate", interactive=False, verbosity=0)

got = Site.objects.get_current()
print(json.dumps({"application_site_lookup": {
    "pk": got.pk, "domain": got.domain, "name": got.name,
    "valid": bool(got.domain and got.name)
}}))
"""


def collect(db_path: Path) -> dict:
    with sqlite3.connect(db_path) as con:
        schema = [
            [name, sql] for name, sql in con.execute(
                "SELECT name,sql FROM sqlite_master "
                "WHERE sql IS NOT NULL AND type IN ('table','view','index','trigger') "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        ledger = []
        if any(x[0] == "django_migrations" for x in schema):
            ledger = [list(row) for row in con.execute(
                "SELECT app,name FROM django_migrations ORDER BY app,name"
            )]
        content = {}
        tables = {item[0] for item in schema}
        if "django_site" in tables:
            content["django_site"] = [
                list(row) for row in con.execute(
                    "SELECT id,domain,name FROM django_site ORDER BY id"
                )
            ]
        if "auth_permission" in tables:
            content["custom_permissions"] = [
                list(row) for row in con.execute(
                    "SELECT codename FROM auth_permission "
                    "WHERE codename IN ('can_hear','can_smell') ORDER BY codename"
                )
            ]
        if "auth_group" in tables:
            content["employee_group"] = [
                list(row) for row in con.execute(
                    "SELECT g.name, p.codename FROM auth_group g "
                    "LEFT JOIN auth_group_permissions gp ON gp.group_id=g.id "
                    "LEFT JOIN auth_permission p ON p.id=gp.permission_id "
                    "WHERE g.name='employees' ORDER BY p.codename"
                )
            ]
        return {"schema": schema, "ledger": ledger, "content": content}


def launch(argv: list[str], cwd: Path | None = None) -> dict:
    started = time.perf_counter_ns()
    process = subprocess.run(
        argv, cwd=cwd, capture_output=True, text=True,
        errors="replace", timeout=90, env=os.environ.copy(),
    )
    return {
        "argv": [Path(argv[0]).name, *argv[1:]],
        "return_code": process.returncode,
        "stdout": process.stdout,
        "stderr": process.stderr[-12000:],
        "ms": round((time.perf_counter_ns() - started) / 1e6, 3),
    }


def replay_petter(source: Path, output: Path) -> dict:
    expected = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "HEAD"],
        capture_output=True, check=True, text=True,
    ).stdout.strip()
    if expected != PETTER_COMMIT:
        raise ValueError(f"PetterS repository changed: {expected}")
    records = []
    paths = {
        "direct": [["auth"], ["myapp"]],
        "staged": [
            ["auth"], ["myapp", "0001_initial"],
            ["myapp", "0002_auto_20181012_1052"],
            ["myapp", "0003_auto_20181012_1054"],
        ],
        "checkpoint_direct": [["auth"], ["myapp", "0002_auto_20181012_1052"]],
        "checkpoint_staged": [
            ["auth"], ["myapp", "0001_initial"],
            ["myapp", "0002_auto_20181012_1052"],
        ],
    }
    for label, path in paths.items():
        with tempfile.TemporaryDirectory(prefix="n22-petter-") as temp:
            root = Path(temp) / "source"
            shutil.copytree(source, root, ignore=shutil.ignore_patterns(".git", "*.sqlite", "__pycache__"))
            log = []
            for migration_args in path:
                call = launch(
                    [sys.executable, "manage.py", "migrate", *migration_args,
                     "--noinput", "--verbosity", "0"],
                    cwd=root,
                )
                log.append(call)
                if call["return_code"] != 0:
                    break
            db = root / "db.sqlite3"
            stored = output / f"petter-{label}.sqlite"
            shutil.copy2(db, stored)
            snapshot = collect(stored)
            records.append({
                "scenario": label,
                "success": all(x["return_code"] == 0 for x in log),
                "steps": log,
                "database": stored.name,
                **snapshot,
            })
    by_case = {x["scenario"]: x for x in records}
    by_case["checkpoint_direct"]["same_schema_as_staged"] = (
        by_case["checkpoint_direct"]["schema"] == by_case["checkpoint_staged"]["schema"]
    )
    by_case["checkpoint_direct"]["same_ledger_as_staged"] = (
        by_case["checkpoint_direct"]["ledger"] == by_case["checkpoint_staged"]["ledger"]
    )
    return {
        "source": "https://github.com/PetterS/django-demo-app",
        "issue": "https://code.djangoproject.com/ticket/29843",
        "commit": PETTER_COMMIT,
        "observations": records,
        "positive_scope": "real_migration_failure_not_silent_success",
    }


def replay_sites(output: Path) -> dict:
    records = []
    for mode in ("fresh", "staged", "staged-user-row"):
        db = output / f"django-sites-{mode}.sqlite"
        if db.exists():
            db.unlink()
        log = launch([sys.executable, "-c", SITE_RUNNER, str(db), mode])
        observed = collect(db) if db.exists() else {}
        app_probe = None
        if log["return_code"] == 0:
            app_probe = json.loads(log["stdout"].splitlines()[-1])
        records.append({
            "scenario": mode,
            "success": log["return_code"] == 0,
            "step": log,
            "database": db.name,
            "application_probe": app_probe,
            **observed,
        })
    ref = records[0]
    for row in records:
        row["same_schema_as_fresh"] = row["schema"] == ref["schema"]
        row["same_ledger_as_fresh"] = row["ledger"] == ref["ledger"]
        row["same_rows_as_fresh"] = row["content"] == ref["content"]
        row["contract_valid"] = (
            bool(row.get("application_probe", {}).get("application_site_lookup", {}).get("valid"))
            if row.get("application_probe") else False
        )
    return {"observations": records, "negative_scope": "legitimate_site_customization"}


def run(source: Path, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    result = {
        "environment": {
            "django": django.get_version(),
            "python": platform.python_version(),
            "sqlite": sqlite3.sqlite_version,
        },
        "petter": replay_petter(source, output),
        "builtin_sites": replay_sites(output),
    }
    (output / "django-observations.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--petter-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    outcome = run(args.petter_source.resolve(), args.output.resolve())
    for row in outcome["petter"]["observations"]:
        print("Petter", row["scenario"], "success=", row["success"], "ledger=", len(row["ledger"]))
    for row in outcome["builtin_sites"]["observations"]:
        print("Sites", row["scenario"], "schema=", row["same_schema_as_fresh"],
              "ledger=", row["same_ledger_as_fresh"], "contract=", row["contract_valid"])
