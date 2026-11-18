#!/usr/bin/env python3
"""Preregistered, no-retuning, out-of-family Helm value-preservation audit.

This is NOT evidence of Kubernetes Pods or user-generated Release histories.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
PHASE = ROOT / "phase2"
sys.path.insert(0, str(ROOT / "scripts"))
import run_study as frozen  # noqa: E402; deliberately import unchanged original

PAIRS = [
    ("grafana", "grafana", "7.3.12", "8.0.0", "https://grafana.github.io/helm-charts"),
    ("ingress-nginx", "ingress-nginx", "4.10.0", "4.11.0", "https://kubernetes.github.io/ingress-nginx"),
    ("metrics-server", "metrics-server", "3.11.0", "3.12.0", "https://kubernetes-sigs.github.io/metrics-server"),
    ("vault", "vault", "0.27.0", "0.28.0", "https://helm.releases.hashicorp.com"),
    ("traefik", "traefik", "24.0.0", "25.0.0", "https://traefik.github.io/charts"),
    ("loki", "loki", "5.47.2", "6.0.0", "https://grafana.github.io/helm-charts"),
    ("external-dns", "external-dns", "1.14.4", "1.15.0", "https://kubernetes-sigs.github.io/external-dns"),
    ("sealed-secrets", "sealed-secrets", "2.14.2", "2.15.0", "https://bitnami-labs.github.io/sealed-secrets"),
]
ORIGINAL_SCORER_SHA = "64381bae392d703b7fbc20159dbaa02cf9cb6591412eb8249e6bf1f55fbf2b2e"
SEED = 20261115
TARGET = 12
ATTEMPT_CAP = 150
BLOCK = ("secret", "password", "token", "credential", "private", "certificate",
         "cert", "passphrase", "auth", "license", "key", "pem")


def leaves(obj: Any, path: tuple[str, ...] = ()) -> list[tuple[str, ...]]:
    if isinstance(obj, dict):
        return [p for k, v in obj.items() for p in leaves(v, path+(str(k),))]
    if isinstance(obj, str) and obj.strip() and not any(b in ".".join(path).lower() for b in BLOCK):
        if "\n" not in obj and "{{" not in obj and len(obj) < 120:
            return [path]
    return []


def new_value(path: tuple[str, ...], token: str) -> str:
    p = ".".join(path).lower()
    if "url" in p or "uri" in p or "endpoint" in p:
        return f"https://{token}.example.invalid"
    if "host" in p or "domain" in p or "fqdn" in p:
        return f"{token}.example.invalid"
    if p.endswith("repository") or p.endswith("registry"):
        return f"example.invalid/{token}"
    return token


def nested_value(obj: dict, path: tuple[str, ...]) -> Any:
    for k in path:
        obj = obj[k]
    return obj


def has_value(docs: list[dict], needle: str) -> bool:
    return needle in yaml.safe_dump_all(docs, sort_keys=True)


def missing_new_key(values: Any, path: tuple[str, ...]) -> bool:
    for key in path:
        if not isinstance(values, dict) or key not in values:
            return True
        values = values[key]
    return False


def load_values(helm: Path, chart: Path) -> dict:
    run = subprocess.run([str(helm), "show", "values", str(chart)],
                         text=True, capture_output=True, check=True, timeout=40)
    return yaml.safe_load(run.stdout) or {}


def summarize(rs: dict[str, Any]) -> dict:
    return {k: v for k, v in rs.items() if k != "documents"}


def compute_metrics(rows: list[dict], releases: list[dict]) -> dict:
    evaluated = [r for r in rows if r["contract_status"] != "hard_render_failure"]
    families = sorted({r["family"] for r in evaluated})
    byfamily = {}
    for fam in families:
        sub = [r for r in evaluated if r["family"] == fam]
        positives = [r for r in sub if r["contract_status"] == "silent_value_loss"]
        negatives = [r for r in sub if r["contract_status"] == "preserved"]
        byfamily[fam] = {
            "states":len(sub), "losses":len(positives), "controls":len(negatives),
            "cid_tp":sum(r["cid_flag"] for r in positives),
            "cid_fp":sum(r["cid_flag"] for r in negatives),
            "missing_key_tp":sum(r["missing_new_default_flag"] for r in positives),
            "missing_key_fp":sum(r["missing_new_default_flag"] for r in negatives),
        }
    fields = ("states","losses","controls","cid_tp","cid_fp","missing_key_tp","missing_key_fp")
    total = {k:sum(x[k] for x in byfamily.values()) for k in fields}
    total["render_failures"] = len(rows)-len(evaluated)
    total["cid_recall"] = total["cid_tp"]/total["losses"] if total["losses"] else None
    total["cid_fpr"] = total["cid_fp"]/total["controls"] if total["controls"] else None
    total["missing_key_recall"] = (
        total["missing_key_tp"]/total["losses"] if total["losses"] else None)
    total["missing_key_fpr"] = (
        total["missing_key_fp"]/total["controls"] if total["controls"] else None)
    total["family_clusters"] = len(families)
    total["preregistered_families"] = len(PAIRS)
    rng = random.Random(81820261115)
    samples = []
    for _ in range(5000):
        draw = [byfamily[families[rng.randrange(len(families))]] for __ in families]
        p = sum(f["losses"] for f in draw)
        if p:
            samples.append(sum(f["cid_tp"]-f["missing_key_tp"] for f in draw)/p*100)
    total["cid_minus_missing_key_delta_pp"] = (
        100*(total["cid_tp"]-total["missing_key_tp"])/total["losses"]
        if total["losses"] else None)
    total["cluster_bootstrap_delta_95_pp"] = (
        [round(sorted(samples)[int(.025*len(samples))],3),
         round(sorted(samples)[int(.975*len(samples))-1],3)] if samples else None)
    return {
        "design":"preregistered out-of-family manifest literal-preservation, not native runtime",
        "freeze":ORIGINAL_SCORER_SHA, "seed":SEED,
        "inclusions_per_family":TARGET, "max_attempts":ATTEMPT_CAP,
        "by_family":byfamily, "aggregate":total,
        "all_original_pairs":releases,
        "limitations":[
            "oracle is exact sentinel retention in rendered manifests, not native health",
            "new-template render failures separate from silent losses",
            "not an empirical helm-diff plus human-reading study",
            "selection uses only old-chart successful exposures",
            "states within same chart family are not independent installations",
        ],
    }


def run() -> None:
    output = PHASE/"results"
    output.mkdir(parents=True, exist_ok=True)
    helm = ROOT/"toolchain/linux-amd64/helm"
    assert helm.is_file(), "Need the original Helm v3.17 toolchain"
    assert frozen.sha256(ROOT/"scripts/run_study.py") == ORIGINAL_SCORER_SHA, (
        "FROZEN SCORER MODIFIED: REFUSE TO RUN")
    allrows, audit, releases = [], [], []
    for family, chartname, oldver, newver, repo in PAIRS:
        oldpath = PHASE/"charts"/f"{chartname}-{oldver}.tgz"
        newpath = PHASE/"charts"/f"{chartname}-{newver}.tgz"
        frec = {
            "family":family,"from":oldver,"to":newver,"repository":repo,
            "old_archive":oldpath.name,"new_archive":newpath.name,
            "old_sha256":frozen.sha256(oldpath) if oldpath.exists() else None,
            "new_sha256":frozen.sha256(newpath) if newpath.exists() else None,
        }
        releases.append(frec)
        if not oldpath.exists() or not newpath.exists():
            frec["status"]="archive_unavailable_prespecified_no_replacement"
            audit.append({"family":family,"status":frec["status"]})
            print(f"SKIP {family}: registered archive not available", flush=True)
            continue
        oldvals, newvals = load_values(helm,oldpath), load_values(helm,newpath)
        olddef = frozen.render(helm,oldpath,{})
        newdef = frozen.render(helm,newpath,{})
        if not olddef["ok"] or not newdef["ok"]:
            frec["status"]="default_render_failure"
            frec["errors"]={"old":olddef["error"],"new":newdef["error"]}
            print(f"SKIP {family}: default render failure", flush=True)
            continue
        frec["status"]="evaluated"
        frec["old_default_resources"]=olddef["resource_count"]
        frec["new_default_resources"]=newdef["resource_count"]
        oldbase = frozen.flatten_docs(olddef["documents"])
        newbase = frozen.flatten_docs(newdef["documents"])
        candidates = sorted(leaves(oldvals),key=lambda p:hashlib.sha256(
            f"{SEED}/{family}/{'.'.join(p)}".encode()).digest())
        frec["eligible_paths"]=len(candidates)
        included = 0
        for attempt,path in enumerate(candidates[:ATTEMPT_CAP]):
            if included >= TARGET:
                break
            hexcode = hashlib.sha256(f"{family}/{'.'.join(path)}".encode()).hexdigest()[:9]
            injected = new_value(path,f"n02-{hexcode}-probe")
            user = {}
            node = user
            for key in path[:-1]:
                node=node.setdefault(key,{})
            node[path[-1]]=injected
            old = frozen.render(helm,oldpath,user)
            audited = {
                "family":family,"attempt":attempt+1,"path":".".join(path),
                "original_default":str(nested_value(oldvals,path))[:120],
                "injected":injected,"old_template_ok":old["ok"],
            }
            if not old["ok"] or not has_value(old["documents"],injected):
                audited["decision"]="excluded_old_render_failed_or_value_not_exposed"
                audited["error"]=old.get("error","")[:350]
                audit.append(audited)
                continue
            audited["decision"]="included_old_only"
            audit.append(audited)
            included+=1
            newer = frozen.render(helm,newpath,user)
            oldpaths=frozen.effect(oldbase,frozen.flatten_docs(old["documents"]))
            newpaths=(frozen.effect(newbase,frozen.flatten_docs(newer["documents"]))
                      if newer["ok"] else set())
            drift=(frozen.effect(frozen.flatten_docs(old["documents"]),
                                 frozen.flatten_docs(newer["documents"]))
                   if newer["ok"] else set())
            lost=oldpaths-newpaths
            gained=newpaths-oldpaths
            vanished=frozen.lost_literals(user,old,newer)
            score=(100.0*bool(oldpaths and not newpaths)
                   +10.0*len(lost)/max(len(oldpaths),1)
                   +1.0*min(len(gained),100)/max(len(newpaths),1)
                   +60.0*bool(vanished))
            present=bool(newer["ok"] and has_value(newer["documents"],injected))
            status=("preserved" if present else
                    ("silent_value_loss" if newer["ok"] else "hard_render_failure"))
            allrows.append({
                "case":f"H-{family}-{included:02d}","family":family,
                "path":".".join(path),"path_keys":list(path),"value":injected,
                "contract_status":status,"old_present":True,"new_present":present,
                "score_counterfactual":round(score,7),"cid_flag":score>=5,
                "score_manifest_diff":len(drift),
                "missing_new_default_flag":missing_new_key(newvals,path),
                "vanished_operator_literals":vanished,
                "old_effect_positions":len(oldpaths),
                "new_effect_positions":len(newpaths),
                "lost_effect_positions":len(lost),
                "render_old":summarize(old),"render_new":summarize(newer),
                "source":"selection depended ONLY on old version and visible injection",
            })
        frec["included_states"]=included
        frec["attempted_paths"]=sum(x["family"]==family for x in audit)
        print(f"HOLDOUT {family}: {included} accepted/{frec['attempted_paths']} attempted",flush=True)
    (output/"charts_provenance.json").write_text(json.dumps(releases,indent=2))
    (output/"selection_audit.json").write_text(json.dumps(audit,indent=2))
    (output/"holdout_cases.jsonl").write_text(
        "\n".join(json.dumps(x) for x in allrows)+"\n")
    summary=compute_metrics(allrows,releases)
    (output/"holdout_summary.json").write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary["aggregate"],indent=2),flush=True)


if __name__=="__main__":
    run()
