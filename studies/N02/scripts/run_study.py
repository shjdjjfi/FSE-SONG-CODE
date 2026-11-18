#!/usr/bin/env python3
"""CPU-only chart-upgrade counterfactuals using the genuine Helm v3.17 renderer.

IMPORTANT: This is a constructed historical-release *emulation*; no Kubernetes
cluster is contacted and no old release database is read.  The three value
policies are reproduced via explicit values overlays and marked accordingly.
The benchmark cases are author-curated from public migration documentation.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

import yaml


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def deep_copy(item: Any) -> Any:
    return copy.deepcopy(item)


def deep_merge(base: Any, additions: Any) -> Any:
    """Helm-like right-biased recursive map merge for YAML values.

    Exact Helm reuse additionally coalesces nils, aliases, subcharts and schema;
    the renderer validates the resulting values independently below.  Thus the
    --reuse-values arm is an *approximation*, not a real stored-release upgrade.
    """
    if not isinstance(base, dict) or not isinstance(additions, dict):
        return deep_copy(additions)
    result = deep_copy(base)
    for key, value in additions.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = deep_copy(value)
    return result


def render(helm: Path, chart: Path, override: dict[str, Any],
           *, timeout: int = 60) -> dict[str, Any]:
    cmd = [
        str(helm), "template", "n02", str(chart), "--is-upgrade",
        "--namespace", "n02-test", "--kube-version", "1.30.0", "-f", "-",
    ]
    start = time.monotonic()
    try:
        process = subprocess.run(
            cmd, input=yaml.safe_dump(override, sort_keys=True), text=True,
            capture_output=True, timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {"ok": False, "error": f"Timeout: {exc}", "seconds": time.monotonic()-start}
    data: dict[str, Any] = {
        "ok": process.returncode == 0,
        "exit_code": process.returncode,
        "seconds": round(time.monotonic()-start, 4),
        "stdout_sha256": hashlib.sha256(process.stdout.encode()).hexdigest(),
        "stdout_bytes": len(process.stdout.encode()),
        "error": process.stderr[-2000:],
    }
    if not data["ok"]:
        return data
    try:
        docs = list(yaml.safe_load_all(process.stdout))
    except yaml.YAMLError as exc:
        return data | {"ok": False, "error": f"Parsing Helm output: {exc}"}
    data["documents"] = [d for d in docs if isinstance(d, dict) and d.get("kind")]
    data["resource_count"] = len(data["documents"])
    return data


def path_repr(path: tuple[Any, ...]) -> str:
    return "/".join(str(x) for x in path)


def flatten(value: Any, path: tuple[Any, ...] = ()) -> dict[str, Any]:
    """Identify resource-local leaf positions; use for *within-version* effects."""
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, child in sorted(value.items(), key=lambda p: str(p[0])):
            result.update(flatten(child, path+(key,)))
        return result or {path_repr(path): "{}"}
    if isinstance(value, list):
        result = {}
        # Stable YAML collection identities prevent a reordered scrape/job
        # list from looking like many changes to unrelated list positions.
        identity_key = next((
            key for key in ("job_name", "name")
            if value and all(isinstance(x, dict) and
                             isinstance(x.get(key), (str, int)) for x in value)
            and len({str(x[key]) for x in value}) == len(value)
        ), None)
        for index, child in enumerate(value):
            index_or_name = (f"{identity_key}={child[identity_key]}"
                             if identity_key else index)
            result.update(flatten(child, path+(index_or_name,)))
        return result or {path_repr(path): "[]"}
    return {path_repr(path): value}


def flatten_docs(docs: list[dict[str, Any]]) -> dict[str, Any]:
    result = {}
    for doc in docs:
        meta = doc.get("metadata") or {}
        # Namespace is stable across counterfactuals and not needed as a key.
        ident = f"{doc.get('apiVersion')}/{doc['kind']}/{meta.get('name','')}"
        semantic_doc = deep_copy(doc)
        if doc.get("kind") == "ConfigMap":
            for key, value in (semantic_doc.get("data") or {}).items():
                if isinstance(value, str) and key.endswith((".yaml", ".yml")):
                    try:
                        parsed = yaml.safe_load(value)
                        if isinstance(parsed, (dict, list)):
                            semantic_doc["data"][key] = parsed
                    except yaml.YAMLError:
                        pass
        result.update(flatten(semantic_doc, (ident+"::",)))
    return result


def effect(left: dict[str, Any], right: dict[str, Any]) -> set[str]:
    # A whole resource entering/leaving the manifest counts once, not as
    # thousands of CRD schema fields.  Within shared resources inspect the
    # named YAML leaf paths.  This avoids versioned CRD drift inflating losses.
    groups_left = {k.partition("::")[0] for k in left}
    groups_right = {k.partition("::")[0] for k in right}
    result = {f"{g}::@resource_exists" for g in groups_left ^ groups_right}
    common = groups_left & groups_right
    return result | {
        key for key in left.keys() | right.keys()
        if key.partition("::")[0] in common
        and left.get(key, ("missing",)) != right.get(key, ("missing",))
    }


def user_strings(values: Any) -> set[str]:
    if isinstance(values, dict):
        return set().union(*(user_strings(x) for x in values.values()))
    if isinstance(values, list):
        return set().union(*(user_strings(x) for x in values))
    if isinstance(values, str) and len(values) >= 6:
        return {values}
    return set()


def lost_literals(user: dict[str, Any], original: dict[str, Any],
                  newer: dict[str, Any]) -> list[str]:
    if not original["ok"] or not newer["ok"]:
        return []
    old_dump = yaml.safe_dump_all(original["documents"], sort_keys=True)
    new_dump = yaml.safe_dump_all(newer["documents"], sort_keys=True)
    # A distinctive operator-supplied value that the prior chart visibly
    # emitted but the new chart drops is weak evidence of a lost intent.
    # Ignore non-string scalars because e.g. booleans are ubiquitous.
    return sorted(x for x in user_strings(user) if x in old_dump and x not in new_dump)


def find_resource(docs: list[dict[str, Any]], *, kind: str | None = None,
                  name: str | None = None, data_key: str | None = None) -> dict[str, Any] | None:
    for doc in docs:
        if kind and doc.get("kind") != kind:
            continue
        if name and (doc.get("metadata") or {}).get("name") != name:
            continue
        if data_key and data_key not in (doc.get("data") or {}):
            continue
        return doc
    return None


def nested(doc: Any, path: list[Any]) -> Any:
    try:
        for p in path:
            doc = doc[p]
        return doc
    except (KeyError, TypeError, IndexError):
        return None


def extract_contract(contract: dict[str, Any], docs: list[dict[str, Any]]) -> Any:
    typ = contract["type"]
    if typ == "argo_cm_exists":
        return find_resource(docs, kind="ConfigMap", name="argocd-cm") is not None
    if typ in ("argo_url", "argo_rbac_default"):
        name = "argocd-cm" if typ == "argo_url" else "argocd-rbac-cm"
        field = "url" if typ == "argo_url" else "policy.default"
        resource = find_resource(docs, kind="ConfigMap", name=name)
        return (resource.get("data") or {}).get(field) if resource else None
    if typ == "argo_ingress_host":
        resource = find_resource(docs, kind="Ingress")
        return nested(resource, ["spec", "rules", 0, "host"])
    if typ in ("tempo_global_processors", "tempo_tenant_processors"):
        name = "tempo.yaml" if typ == "tempo_global_processors" else "overrides.yaml"
        resource = find_resource(docs, kind="ConfigMap", data_key=name)
        content = (resource or {}).get("data", {}).get(name, "")
        if not content:
            return None
        parsed = yaml.safe_load(content) or {}
        if typ == "tempo_global_processors":
            return nested(parsed, ["overrides", "defaults", "metrics_generator", "processors"])
        return nested(parsed, ["overrides", "tenant_n02", "metrics_generator", "processors"])
    if typ == "prometheus_job_names":
        resource = find_resource(docs, kind="ConfigMap", data_key="prometheus.yml")
        content = (resource or {}).get("data", {}).get("prometheus.yml", "")
        parsed = yaml.safe_load(content) if content else {}
        return sorted([s.get("job_name") for s in (parsed or {}).get("scrape_configs", [])])
    if typ == "ksm_namespace_flag":
        resource = find_resource(docs, kind="Deployment")
        containers = nested(resource, ["spec", "template", "spec", "containers"]) or []
        all_args = [a for container in containers for a in container.get("args", [])]
        for arg in all_args:
            if arg.startswith("--namespace=") or arg.startswith("--namespaces="):
                # This is a value-level behavior alias across application CLI
                # versions; we compare the affected namespace, not flag spelling.
                return "--namespaces="+arg.split("=", 1)[1]
        return None
    raise KeyError(f"Unsupported contract extractor: {typ}")


def stat_record(result: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in result.items() if k != "documents"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--helm", type=Path, default=None)
    args = ap.parse_args()
    root = args.root.resolve()
    out = args.out.resolve() if args.out else root / "results"
    out.mkdir(parents=True, exist_ok=True)
    helm = (args.helm or root/"toolchain/linux-amd64/helm").resolve()
    if not helm.is_file():
        raise SystemExit("Missing Helm binary; see README.md for the pinned download.")
    specs = yaml.safe_load((root/"cases.yaml").read_text())
    families = specs["families"]
    cases = specs["cases"]
    tool_version = subprocess.run(
        [str(helm), "version", "--short"], text=True, capture_output=True, check=True
    ).stdout.strip()
    metadata = {
        "helm_version": tool_version,
        "helm_sha256": sha256(helm),
        "helm_template_flags": ["--is-upgrade","--namespace=n02-test","--kube-version=1.30.0"],
        "semantics": "SOURCE-CODE-INSPIRED VALUES EMULATION; NOT A PERSISTED RELEASE",
        "case_selection": "curated from cited official migration notes; not independent random holdout",
        "chart_artifacts": {},
    }
    baseline: dict[str, dict[str, Any]] = {}
    defaults: dict[str, dict[str, Any]] = {}
    for family, spec in families.items():
        old = (root/"charts"/spec["from"]).resolve()
        new = (root/"charts"/spec["to"]).resolve()
        for version, chart in (("old", old), ("new", new)):
            if not chart.is_file():
                raise FileNotFoundError(f"Chart missing: {chart}")
            metadata["chart_artifacts"][f"{family}-{version}"] = {
                "filename": chart.name, "sha256": sha256(chart),
                "bytes": chart.stat().st_size, "project": spec["project"],
            }
        oldvals = subprocess.run(
            [str(helm), "show", "values", str(old)],
            text=True, capture_output=True, check=True,
        )
        defaults[family] = yaml.safe_load(oldvals.stdout) or {}
        baseline[family] = {
            "old": render(helm, old, {}),
            "new": render(helm, new, {}),
        }
        for key in ("old", "new"):
            if not baseline[family][key]["ok"]:
                raise RuntimeError(f"Default render failed for {family}/{key}: {baseline[family][key]['error']}")
        print(f"DEFAULT {family}: {baseline[family]['old']['resource_count']} to "
              f"{baseline[family]['new']['resource_count']} resources", flush=True)
    (out/"toolchain_and_sources.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False))
    rows: list[dict[str, Any]] = []
    for case in cases:
        family = case["family"]
        pair = families[family]
        oldpath = root/"charts"/pair["from"]
        newpath = root/"charts"/pair["to"]
        user = case["old_user"]
        with_old = render(helm, oldpath, user)
        with_reset = render(helm, newpath, user)  # new defaults + old explicit config
        with_reuse = render(helm, newpath, deep_merge(defaults[family], user))
        migrated = render(helm, newpath, case.get("migrated_user", user))
        inputs = {"old": with_old, "reset_then_reuse": with_reset,
                  "reuse_old_defaults": with_reuse, "migrated": migrated}
        for name, output in inputs.items():
            if not output["ok"]:
                print(f"ERROR {case['id']} {name}: {output['error'][-260:]}", flush=True)
        before = flatten_docs(baseline[family]["old"]["documents"])
        after = flatten_docs(baseline[family]["new"]["documents"])
        oldpaths = (effect(before, flatten_docs(with_old["documents"]))
                    if with_old["ok"] else set())
        newpaths = (effect(after, flatten_docs(with_reset["documents"]))
                    if with_reset["ok"] else set())
        merged_version_drift = (
            len(effect(flatten_docs(with_old["documents"]), flatten_docs(with_reset["documents"])))
            if with_old["ok"] and with_reset["ok"] else None
        )
        lost = oldpaths - newpaths
        gained = newpaths - oldpaths
        vanished_literals = lost_literals(user, with_old, with_reset)
        score = (
            100.0 * bool(oldpaths and not newpaths)
            + 10.0 * len(lost) / max(len(oldpaths), 1)
            + 1.0 * min(len(gained), 100) / max(len(newpaths), 1)
            + 60.0 * bool(vanished_literals)
        )
        contracts = None
        if case.get("contract"):
            contracts = {}
            for k, output in inputs.items():
                contracts[k] = (
                    extract_contract(case["contract"], output["documents"])
                    if output["ok"] else "RENDER_FAILED"
                )
            expected = case["contract"]["expected"]
            if case["contract"]["type"] == "prometheus_job_names":
                expected = sorted(expected)
            contracts["expected"] = expected
            contracts["old_ok"] = contracts["old"] == expected
            contracts["reset_then_reuse_ok"] = contracts["reset_then_reuse"] == expected
            contracts["migrated_ok"] = contracts["migrated"] == expected
        # A fixed label-blind ranking algorithm: old override's measurable
        # per-key template effect lost or moved under new chart.  This has no
        # access to migration labels or operator-specified expected behavior.
        row = {
            "id": case["id"], "family": family, "label": case["label"],
            "intent": case.get("intent"),
            "documentation_covered": bool(case.get("documentation_covered")),
            "documented_actionable_migration": bool(case.get("documented_actionable_migration")),
            "inputs": {"old_user": user, "migrated_user": case.get("migrated_user", user)},
            "render": {k: stat_record(v) for k, v in inputs.items()},
            "contract": contracts,
            "old_effect_positions": len(oldpaths),
            "new_effect_positions": len(newpaths),
            "lost_effect_positions": len(lost),
            "gained_effect_positions": len(gained),
            "vanished_operator_literals": vanished_literals,
            "old_effect_sample": sorted(oldpaths)[:30],
            "new_effect_sample": sorted(newpaths)[:30],
            "changed_version_positions": merged_version_drift,
            "score_counterfactual": round(score, 7),
            "score_manifest_diff": merged_version_drift or 0,
            "score_missing_in_new_defaults": -1,
            "schema": "per-key leaf paths matched against chart values, not a JSON schema",
        }
        # Value keys not declared by the newer defaults are suspicious but
        # templated maps may legitimately contain dynamic (undeclared) keys.
        new_vals = yaml.safe_load(subprocess.run(
            [str(helm), "show", "values", str(newpath)],
            text=True, capture_output=True, check=True
        ).stdout) or {}
        def leaves(m: Any, prefix: tuple[str, ...] = ()) -> list[tuple[str, ...]]:
            if isinstance(m, dict):
                return [p for k, v in m.items() for p in leaves(v, prefix+(str(k),))]
            if isinstance(m, list):
                return [prefix]
            return [prefix]
        def contains_path(m: Any, p: tuple[str, ...]) -> bool:
            for key in p:
                if not isinstance(m, dict) or key not in m:
                    return False
                m = m[key]
            return True
        leafpaths=leaves(user)
        row["score_missing_in_new_defaults"] = sum(
            int(not contains_path(new_vals, path)) for path in leafpaths
        )
        rows.append(row)
        print(f"{case['id']:<26} {case['label']:<9} "
              f"old={len(oldpaths):>3} new={len(newpaths):>3} "
              f"lost={len(lost):>3} rank={score:>6.2f} "
              f"contract={contracts['old_ok'] if contracts else 'n/a'}"
              f"/{contracts['reset_then_reuse_ok'] if contracts else 'n/a'}"
              f"/{contracts['migrated_ok'] if contracts else 'n/a'}",flush=True)
        (out/"case_results.jsonl").write_text("\n".join(
            json.dumps(r, ensure_ascii=False) for r in rows
        )+"\n")
    # Record the version-only chart default changes *without* suggesting that
    # all of them are application regressions.
    fam_rows = []
    for family, state in baseline.items():
        old, new = state["old"], state["new"]
        oldflat = flatten_docs(old["documents"])
        newflat = flatten_docs(new["documents"])
        fam_rows.append({
            "family": family,
            "old_render": stat_record(old),
            "new_render": stat_record(new),
            "default_changed_field_positions": len(effect(oldflat, newflat)),
            "default_old_resources": old["resource_count"],
            "default_new_resources": new["resource_count"],
        })
    (out/"default_drift.json").write_text(json.dumps(fam_rows, indent=2, ensure_ascii=False))
    print(f"STUDY COMPLETE: {len(rows)} cases, "
          f"{sum(r['label']=='positive' for r in rows)} migration cases.",flush=True)


if __name__ == "__main__":
    main()
