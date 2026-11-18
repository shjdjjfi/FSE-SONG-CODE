#!/usr/bin/env python3
"""Independent negative controls using Django's actual migration executor.

The script never calls the N22 detector to generate ground truth. Business
observations come from Django's own Site manager and Redirect model.
"""

import argparse
import hashlib
import json
import platform
import sqlite3
from pathlib import Path


def hash_json(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--db", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--mode", required=True,
                   choices=["fresh", "staged", "staged_user", "staged_redirect", "staged_noop"])
    p.add_argument("--domain", default="client.example")
    p.add_argument("--name", default="Customer's original choice")
    a = p.parse_args()
    if a.db.exists():
        p.error("Refusing to overwrite SQLite input")
    a.db.parent.mkdir(parents=True, exist_ok=True)
    from django.conf import settings
    settings.configure(
        INSTALLED_APPS=["django.contrib.sites", "django.contrib.redirects", "django.contrib.flatpages"],
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": str(a.db)}},
        SITE_ID=1, SECRET_KEY="n22-isolated-controls-only", USE_TZ=True,
    )
    import django
    django.setup()
    from django.core.management import call_command
    from django.contrib.sites.models import Site
    from django.contrib.redirects.models import Redirect

    if a.mode == "fresh":
        call_command("migrate", interactive=False, verbosity=0)
    else:
        call_command("migrate", "sites", "0001", interactive=False, verbosity=0)
        if a.mode == "staged_user":
            Site.objects.filter(pk=1).update(domain=a.domain, name=a.name)
        call_command("migrate", interactive=False, verbosity=0)
        if a.mode == "staged_redirect":
            Redirect.objects.create(site=Site.objects.get(pk=1), old_path="/old", new_path="/new")
        if a.mode == "staged_noop":
            call_command("migrate", interactive=False, verbosity=0)

    Site.objects.clear_cache()
    observed = Site.objects.get_current()
    expected_domain = a.domain if a.mode == "staged_user" else "example.com"
    expected_name = a.name if a.mode == "staged_user" else "example.com"
    expected_redirects = 1 if a.mode == "staged_redirect" else 0
    oracle = {
        "site_id": observed.id,
        "site_domain": observed.domain,
        "site_name": observed.name,
        "redirect_count": Redirect.objects.count(),
        "expected_domain": expected_domain,
        "expected_name": expected_name,
        "expected_redirect_count": expected_redirects,
        "contract_violation": bool(
            observed.id != 1 or observed.domain != expected_domain or observed.name != expected_name
            or Redirect.objects.count() != expected_redirects
        ),
    }
    with sqlite3.connect(a.db) as conn:
        schema = conn.execute("SELECT type,name,tbl_name,sql FROM sqlite_master "
                              "WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' ORDER BY type,name").fetchall()
        ledger = conn.execute("SELECT app,name FROM django_migrations ORDER BY app,name").fetchall()
        rows = conn.execute("SELECT id,domain,name FROM django_site ORDER BY id").fetchall()
        redirects = conn.execute("SELECT site_id,old_path,new_path FROM django_redirect ORDER BY id").fetchall()
    result = {
        "case_id": a.mode + ("-" + a.domain if a.mode == "staged_user" else ""),
        "project": "django.contrib.sites/redirects/flatpages",
        "source": {"django_version": django.get_version(), "python": platform.python_version(),
                   "sqlite_version": sqlite3.sqlite_version},
        "schema_sha256": hash_json(schema),
        "migration_ledger_sha256": hash_json(ledger),
        "schema": schema, "migration_ledger": ledger,
        "site_rows": rows, "redirect_rows": redirects,
        "contract_input": {"site_id": 1, "user_owned_domain": expected_domain,
                           "user_owned_name": expected_name, "expected_redirect_count": expected_redirects},
        "business_oracle": oracle,
        "classification": "legitimate_user_configuration" if a.mode in ("staged_user", "staged_redirect")
                          else "migration_path_equivalent",
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"case_id": result["case_id"], "oracle": oracle,
                      "schema_sha256": result["schema_sha256"],
                      "migration_ledger_sha256": result["migration_ledger_sha256"]}))


if __name__ == "__main__":
    main()
