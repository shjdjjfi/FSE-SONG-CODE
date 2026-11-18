"""Align measured test IDs to the source-control *commit* chronology.

The original dataset's timestamps are dates of the 2023 replay execution, not
dates of the 2017--2019 source revisions.  Sorting by execution timestamps
would create spurious transitions, so this script uses Git ancestry.
"""

import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess


def git(repo: Path, *args: str, check=True) -> str:
    p = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if check and p.returncode:
        raise RuntimeError(f"git {args}: {p.stderr[:400]}")
    return p.stdout.strip()


def sorted_source_commits(repo: Path, observed: list[str]) -> tuple[list[str], dict]:
    full = {x: git(repo, "rev-parse", x + "^{commit}") for x in observed}
    timestamps = {x: int(git(repo, "show", "-s", "--format=%ct", full[x])) for x in observed}
    # Candidate max by date, then require that the retained history is on the
    # same ancestry path.  If it isn't, record incomparability explicitly.
    newest = max(observed, key=lambda x: (timestamps[x], x))
    topo = git(repo, "rev-list", "--topo-order", "--reverse", full[newest]).splitlines()
    positions = {sha: i for i, sha in enumerate(topo)}
    missing_from_path = [x for x in observed if full[x] not in positions]
    if missing_from_path:
        # Some histories include a seed commit before a non-adjacent replay or
        # multiple branches; leave such revisions in a separate summary only.
        ordered = sorted(
            (x for x in observed if x not in missing_from_path),
            key=lambda x: positions[full[x]],
        )
    else:
        ordered = sorted(observed, key=lambda x: positions[full[x]])
    return ordered, {"newest": newest, "excluded_unreachable": missing_from_path,
                     "source_times": timestamps, "full_sha": full}


def align(source: dict, mappings: dict[str, Path]) -> dict:
    evaluations = {}
    for name, project in sorted(source["projects"].items()):
        slug = project["repository"]
        if slug not in mappings:
            evaluations[name] = {"repository": slug, "status": "source_not_available"}
            continue
        repo = mappings[slug]
        by_commit = {item["hash"]: item for item in project["commits"]}
        order, metadata = sorted_source_commits(repo, list(by_commit))
        transitions = []
        for prev, after in zip(order, order[1:]):
            a = set(by_commit[prev]["tests"])
            b = set(by_commit[after]["tests"])
            dropped, introduced = sorted(a-b), sorted(b-a)
            if not dropped and not introduced:
                continue
            # A source span of more than one commit would obscure the cause.
            gap = int(git(repo, "rev-list", "--count", f"{prev}..{after}"))
            test_diff = git(repo, "diff", "--find-renames", "--name-status", prev, after,
                            "--", "*test*", "*Test*", check=False)
            transitions.append({
                "before": prev, "after": after,
                "source_gap_commits": gap,
                "removed": dropped, "added": introduced,
                "git_changed_test_files": test_diff.splitlines()[:40],
                "n_removed": len(dropped), "n_added": len(introduced),
            })
        evaluations[name] = {
            "repository": slug,
            "status": "aligned",
            "commits": order,
            "metadata": metadata,
            "n_churn_boundaries": len(transitions),
            "n_joint_boundaries": sum(bool(x["n_removed"] and x["n_added"]) for x in transitions),
            "transitions": transitions,
        }
    return {"semantics": "source-control ancestor chronology; excludes unreachable commits",
            "evaluations": evaluations}


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--histories", type=Path, required=True)
    a.add_argument("--repo", nargs=2, action="append", default=[], metavar=("SLUG", "PATH"))
    a.add_argument("--output", type=Path, required=True)
    args = a.parse_args()
    result = align(json.loads(args.histories.read_text()), {k: Path(v) for k,v in args.repo})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    for key, p in result["evaluations"].items():
        if p["status"] == "aligned":
            print(key, "commits", len(p["commits"]),
                  "churn", p["n_churn_boundaries"], "joint", p["n_joint_boundaries"],
                  "unreachable", len(p["metadata"]["excluded_unreachable"]))


if __name__ == "__main__":
    main()
