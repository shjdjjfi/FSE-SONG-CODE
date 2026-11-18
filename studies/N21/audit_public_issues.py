#!/usr/bin/env python3
"""Capture transparent, non-random, public issue evidence about N21.

This is a *purposive* case catalog, NOT a denominator for incidence or
prevalence. No claim is made that a public issue reproduces an industrial CI run.
"""

from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import urllib.request

HERE = Path(__file__).resolve().parent
CATALOG = [
    {
        "repo": "microsoft/TypeScript", "number": 30602,
        "evidence": "TypeScript --build may skip deleted emitted JavaScript; public minimal repro and maintainer explanation",
        "category": "reproduction + maintainer clarification", "scope": "missing-output",
        "ci_evidence": "comment mentions parallel branch CI caching of build info; no full CI trace supplied",
        "mechanism": "incremental state does not treat absent emitted file as necessarily stale",
    },
    {
        "repo": "microsoft/TypeScript", "number": 50646,
        "evidence": "user reports that deleting dist while retaining tsbuildinfo leads to a successful no-output build",
        "category": "user report", "scope": "missing-output",
        "ci_evidence": "not documented",
        "mechanism": "output directory and incremental metadata lifetime diverge",
    },
    {
        "repo": "google/wireit", "number": 905, "issue_type": "pull",
        "evidence": "contributor reports output omissions after error/fix sequence; proposes correcting buildinfo output manifest",
        "category": "user demonstration + proposed configuration repair", "scope": "missing-output",
        "ci_evidence": "not documented",
        "mechanism": "buildinfo excluded from declared output cleanup; pull request currently not assumed merged",
    },
    {
        "repo": "nrwl/nx", "number": 35079,
        "evidence": "Nx maintainer documents stale compilation after dependency task cache restoration; workaround removes build info",
        "category": "maintainer issue + concrete reproduction steps", "scope": "stale-output",
        "ci_evidence": "problem in a build-base workflow; original production replay not supplied",
        "mechanism": "interplay of Nx task cache and TypeScript incremental state",
    },
    {
        "repo": "nestjs/nest-cli", "number": 3312,
        "evidence": "Nest CLI deleteOutDir and TypeScript 6 incremental state can silently emit zero files; merged repair",
        "category": "maintainer-confirmed issue + repair", "scope": "missing-output",
        "ci_evidence": "tooling scenario, not a shared production CI incident trace",
        "mechanism": "deletion of dist without deletion of outside tsbuildinfo",
    },
    {
        "repo": "microsoft/TypeScript", "number": 38648,
        "evidence": "dependency-typing change may be missed by incremental compilation",
        "category": "nearby but distinct failure", "scope": "input-drift-not-output-loss",
        "ci_evidence": "author mentions TS output caching in CI; no run logs supplied",
        "mechanism": "cache invalidation when node_modules change",
    },
    {
        "repo": "microsoft/TypeScript", "number": 42769,
        "evidence": "report of stale semantic diagnostic data in tsbuildinfo",
        "category": "nearby but distinct failure", "scope": "stale-diagnostics",
        "ci_evidence": "not documented",
        "mechanism": "incremental diagnostics invalidation rather than missing artifacts",
    },
]


def fetch(url: str):
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json",
         "User-Agent": "N21-FSE-Industry-Evidence-Audit", "X-GitHub-Api-Version": "2022-11-28"})
    with urllib.request.urlopen(request, timeout=35) as response:
        return json.load(response)


def main():
    output = []
    for x in CATALOG:
        route = "pulls" if x.get("issue_type") == "pull" else "issues"
        url = f"https://api.github.com/repos/{x['repo']}/{route}/{x['number']}"
        row = dict(x)
        try:
            data = fetch(url)
            body = (data.get("body") or "").encode("utf-8")
            row.update({
                "source_api": url, "source_url": data.get("html_url"),
                "author_login": data.get("user", {}).get("login"),
                "title": data.get("title"), "state": data.get("state"),
                "created_at": data.get("created_at"), "updated_at": data.get("updated_at"),
                "closed_at": data.get("closed_at"), "body_sha256": hashlib.sha256(body).hexdigest(),
                "body_bytes": len(body), "retrieved": True,
            })
        except Exception as e:
            row.update({"retrieved": False, "retrieval_error": str(e), "source_url":
                f"https://github.com/{x['repo']}/{('pull' if route == 'pulls' else 'issues')}/{x['number']}"})
        output.append(row)
    path = HERE / "results" / "public_issue_audit.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"audit_utc": datetime.now(timezone.utc).isoformat(),
        "sampling": "non-random candidate issues identified by targeted queries; not population prevalence",
        "no_independent_ci_replay": True, "cases": output}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved {len(output)} case records; API retrievals: {sum(x['retrieved'] for x in output)}/{len(output)}")

if __name__ == "__main__":
    main()
