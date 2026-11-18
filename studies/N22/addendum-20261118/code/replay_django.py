#!/usr/bin/env python3
"""Run real Django migrations, capturing an independent auth-API oracle.

This does NOT patch Django. The caller selects an upstream Django source tree
through PYTHONPATH or uses an installed, pinned distribution.
"""

import argparse
import hashlib
import json
import platform
import sqlite3
import sys
from pathlib import Path


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def snapshot(db_file):
    with sqlite3.connect(db_file) as connection:
        schema = connection.execute(
            "SELECT type,name,tbl_name,sql FROM sqlite_master "
            "WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' "
            "ORDER BY type,name"
        ).fetchall()
        ledger = connection.execute(
            "SELECT app,name FROM django_migrations ORDER BY app,name"
        ).fetchall()
        count_sql = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        counts = {name: connection.execute(f'SELECT count(*) FROM "{name}"').fetchone()[0]
                  for (name,) in count_sql}
        permissions = connection.execute(
            "SELECT t.app_label,t.model,p.codename,p.name FROM auth_permission AS p "
            "JOIN django_content_type AS t ON p.content_type_id=t.id "
            "WHERE t.app_label='n22_perm_app' "
            "ORDER BY t.app_label,t.model,p.codename,p.name"
        ).fetchall()
        grants = connection.execute(
            "SELECT t.app_label,t.model,p.codename FROM auth_user_user_permissions AS g "
            "JOIN auth_permission AS p ON g.permission_id=p.id "
            "JOIN django_content_type AS t ON p.content_type_id=t.id "
            "ORDER BY t.app_label,t.model,p.codename"
        ).fetchall()
    return {
        "schema_sha256": digest(schema),
        "migration_ledger_sha256": digest(ledger),
        "schema": schema,
        "migration_ledger": ledger,
        "row_counts": counts,
        "app_permissions": permissions,
        "user_grants": grants,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--mode", choices=["fresh", "staged", "staged_ungrouped"], required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.db.parent.mkdir(parents=True, exist_ok=True)
    if args.db.exists():
        parser.error("Refusing to reuse/overwrite an existing SQLite database")

    from django.conf import settings

    settings.configure(
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.auth",
            "n22_perm_app",
        ],
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": str(args.db)}},
        SECRET_KEY="n22-isolated-reproduction-only",
        DEFAULT_AUTO_FIELD="django.db.models.AutoField",
        USE_TZ=True,
        PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    )
    import django

    django.setup()
    from django.contrib.auth.models import Permission, User
    from django.core.management import call_command

    def grant():
        user = User.objects.create_user(username="test_user")
        permission = Permission.objects.get(content_type__app_label="n22_perm_app", codename="view_songprofile")
        user.user_permissions.add(permission)

    if args.mode == "fresh":
        call_command("migrate", interactive=False, verbosity=0)
        grant()
    else:
        call_command("migrate", "n22_perm_app", "0001", interactive=False, verbosity=0)
        if args.mode == "staged":
            grant()
        call_command("migrate", interactive=False, verbosity=0)
        if args.mode == "staged_ungrouped":
            grant()

    user = User.objects.get(username="test_user")
    oracle = {
        "expected_songprofile_permission": True,
        "observed_songprofile_permission": user.has_perm("n22_perm_app.view_songprofile"),
        "observed_son_permission": user.has_perm("n22_perm_app.view_son"),
        "contract_violation": not user.has_perm("n22_perm_app.view_songprofile"),
    }
    result = {
        "source": {"django_version": django.get_version(), "django_file": django.__file__,
                   "python": platform.python_version(), "sqlite": sqlite3.sqlite_version},
        "mode": args.mode,
        "db_path": str(args.db),
        "status": "completed",
        "contract_input": {"granted_permission_before_or_after_migration":
                           ["n22_perm_app", "songprofile", "view_songprofile"]},
        "business_oracle": oracle,
        **snapshot(args.db),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"mode": args.mode, "oracle": oracle,
                      "schema": result["schema_sha256"], "ledger": result["migration_ledger_sha256"]}))


if __name__ == "__main__":
    main()
