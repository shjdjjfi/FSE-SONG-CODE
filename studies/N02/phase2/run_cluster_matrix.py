#!/usr/bin/env python3
"""Sequential actual-cluster 6-case x 4-policy matrix on a DISPOSABLE cluster.

Never execute on production. No simulation or fabricated results.
Each replay creates a new namespace, Helm-installs old, diffs, upgrades, probes,
and removes only its owned release and namespaces on explicit user consent.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import secrets
import subprocess
import sys
from datetime import datetime, timezone

HERE=Path(__file__).resolve().parent
CASES=("A01_url_legacy","A02_rbac_legacy","A03_ingress_hosts",
       "A04_config_enabled","K04_namespace","P01_legacy_scrape_map")
POLICIES=("normal","reuse","reset-then-reuse","migrated")
CODES={"normal":"n","reuse":"u","reset-then-reuse":"r","migrated":"m"}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--kubeconfig",required=True,type=Path)
    p.add_argument("--confirm-disposable-cluster",action="store_true",required=True)
    p.add_argument("--confirm-cleanup",action="store_true",required=True)
    p.add_argument("--cases",nargs="+",choices=CASES,default=list(CASES))
    p.add_argument("--policies",nargs="+",choices=POLICIES,default=list(POLICIES))
    p.add_argument("--run-id",default=secrets.token_hex(3))
    p.add_argument("--out",type=Path,default=HERE/"results"/"live_cluster")
    args=p.parse_args()
    if not args.kubeconfig.is_file():
        raise SystemExit("A real kubeconfig for a disposable cluster is required.")
    if not args.run_id.isalnum() or len(args.run_id)>9:
        raise SystemExit("run-id must be 1 to 9 alphanumeric characters")
    out=args.out/args.run_id
    out.mkdir(parents=True,exist_ok=True)
    matrix=[]
    for case in args.cases:
        for policy in args.policies:
            ns=f"n02-{case[:3].lower()}-{CODES[policy]}-{args.run_id}"
            per=out/f"{case}_{policy}"
            command=[sys.executable,str(HERE/"k8s_actual_replay.py"),
                     "--case",case,"--policy",policy,"--namespace",ns,
                     "--kubeconfig",str(args.kubeconfig),
                     "--confirm-disposable-cluster","--cleanup-created-namespaces",
                     "--out",str(per)]
            print(f"REAL K8S {case} {policy} → {ns}",flush=True)
            process=subprocess.run(command,text=True,capture_output=True)
            reportfile=per/"actual_cluster_run.json"
            payload=json.loads(reportfile.read_text()) if reportfile.exists() else {}
            row={
                "case":case,"policy":policy,"namespace":ns,"subprocess_rc":process.returncode,
                "upgrade_succeeded":payload.get("upgrade_succeeded"),
                "blocked_stage":payload.get("blocked_stage"),
                "exception":payload.get("exception"),
                "result_file":str(reportfile) if reportfile.exists() else None,
                "cleanup_rc":(payload.get("cleanup_command") or {}).get("rc"),
            }
            matrix.append(row)
            (out/"matrix_runs.json").write_text(json.dumps(
                {"started_utc":datetime.now(timezone.utc).isoformat(),
                 "actual_cluster_intended":True,"runs":matrix},indent=2))
    print(json.dumps({
        "runs":len(matrix),"upgraded":sum(x["upgrade_succeeded"] is True for x in matrix),
        "failed_or_blocked":sum(x["upgrade_succeeded"] is not True for x in matrix),
        "result":str(out/"matrix_runs.json"),
    },indent=2))

if __name__=="__main__":
    main()
