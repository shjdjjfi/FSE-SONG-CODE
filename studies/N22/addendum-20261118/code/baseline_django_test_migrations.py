#!/usr/bin/env python3
"""Strong existing-tool comparator on an isolated, disposable SQLite file.

django-test-migrations v1.7.0 deliberately mutes pre_migrate/post_migrate.
We populate intermediate permissions explicitly so the same pre-upgrade
user-grant contract can be checked. This tests tool execution semantics,
not an inability to write assertions in that framework.
"""

import argparse
import json
import sqlite3
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    if a.db.exists():
        ap.error("Refusing existing database: Migrator drops model tables")
    a.db.parent.mkdir(parents=True, exist_ok=True)
    from django.conf import settings
    settings.configure(
        INSTALLED_APPS=["django.contrib.contenttypes", "django.contrib.auth", "n22_perm_app"],
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": str(a.db)}},
        DEFAULT_AUTO_FIELD="django.db.models.AutoField", SECRET_KEY="isolated-N22-baseline",
        PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    )
    import django
    django.setup()
    from django.apps import apps
    from django.contrib.auth.management import create_permissions
    from django.contrib.auth.models import User, Permission
    from django.core.management import call_command
    from django_test_migrations.migrator import Migrator
    import django_test_migrations

    # The helper is documented for an already-migrated Django test database.
    # Create that initial empty test-schema state, then let it reset the tables.
    call_command("migrate", interactive=False, verbosity=0)
    migrator = Migrator()
    old_state = migrator.apply_initial_migration(("n22_perm_app", "0001_initial"))
    create_permissions(apps.get_app_config("n22_perm_app"), apps=old_state.apps, verbosity=0)
    user = User.objects.create_user(username="test_user")
    initial_perm = Permission.objects.get(content_type__app_label="n22_perm_app", codename="view_songprofile")
    user.user_permissions.add(initial_perm)
    migrator.apply_tested_migration(("n22_perm_app", "0002_rename_song"))
    user = User.objects.get(username="test_user")
    oracle = {
        "expected_songprofile_permission": True,
        "observed_songprofile_permission": user.has_perm("n22_perm_app.view_songprofile"),
        "observed_son_permission": user.has_perm("n22_perm_app.view_son"),
    }
    with sqlite3.connect(a.db) as conn:
        ledger = conn.execute("SELECT app,name FROM django_migrations ORDER BY app,name").fetchall()
        permissions = conn.execute(
            "SELECT c.model,p.codename FROM auth_permission AS p JOIN django_content_type AS c "
            "ON p.content_type_id=c.id WHERE c.app_label='n22_perm_app' ORDER BY c.model,p.codename"
        ).fetchall()
    report = {
        "comparison": "django-test-migrations 1.7.0 with explicit pre-upgrade grant",
        "django_version": django.get_version(),
        "django_test_migrations_version": getattr(django_test_migrations, "__version__", "1.7.0"),
        "migration_ledger": ledger,
        "permissions": permissions,
        "oracle": oracle,
        "detected_violation": not oracle["observed_songprofile_permission"],
        "note": "The library mutes Django migration signals. A direct manage.py migrate with the same grant detects the bug.",
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"oracle": oracle, "detected_violation": report["detected_violation"]}))


if __name__ == "__main__":
    main()
