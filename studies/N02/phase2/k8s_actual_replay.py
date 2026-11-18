#!/usr/bin/env python3
"""Actual-cluster experiment harness: installs OLD release, runs diff, upgrades.

Requires a USER-SUPPLIED DISPOSABLE Kubernetes cluster and kubectl. It does
not execute in this current no-cgroup/no-container workspace.
Never run on production: Helm charts include cluster-scoped API objects.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import time
from urllib.request import urlopen
import yaml

ROOT = Path(__file__).resolve().parent.parent
PHASE = ROOT/"phase2"
CASES = {"A01_url_legacy","A02_rbac_legacy","A03_ingress_hosts",
         "A04_config_enabled","K04_namespace","P01_legacy_scrape_map"}
POLICIES = {"normal":[],"reuse":["--reuse-values"],
            "reset-then-reuse":["--reset-then-reuse-values"],
            "migrated":["--reset-then-reuse-values"]}


def command(cmd:list[str], cwd:Path, out:Path, ident:str,
            *,timeout:int=600, check:bool=False)->dict:
    started=time.monotonic()
    try:
        result=subprocess.run(cmd,cwd=cwd,text=True,capture_output=True,timeout=timeout)
        stdout,stderr,rc=result.stdout,result.stderr,result.returncode
    except subprocess.TimeoutExpired as e:
        stdout=e.stdout.decode(errors="replace") if isinstance(e.stdout,bytes) else (e.stdout or "")
        stderr=e.stderr.decode(errors="replace") if isinstance(e.stderr,bytes) else (e.stderr or "")
        rc=124
    safe=re.sub(r"[^a-zA-Z0-9_-]","_",ident)
    (out/f"{safe}.stdout").write_text(stdout)
    (out/f"{safe}.stderr").write_text(stderr)
    rec={"label":ident,"cmd":cmd,"rc":rc,"seconds":round(time.monotonic()-started,3),
         "stdout_file":f"{safe}.stdout","stderr_file":f"{safe}.stderr",
         "stdout_sha256":hashlib.sha256(stdout.encode()).hexdigest(),
         "stderr_tail":stderr[-700:]}
    if check and rc!=0:
        raise RuntimeError(f"{ident} failed rc={rc}: {stderr[-600:]}")
    return rec


def kubectl_json(args:list[str], out:Path, ident:str, kubeconfig:Path)->tuple[dict,dict]:
    rec=command(["kubectl","--kubeconfig",str(kubeconfig),*args],ROOT,out,ident,timeout=50)
    if rec["rc"]!=0:
        return {},rec
    try:
        return json.loads((out/rec["stdout_file"]).read_text()),rec
    except json.JSONDecodeError:
        return {},rec


def choose_pod_status(pods:dict)->dict:
    return {p["metadata"]["name"]:{
        "phase":p.get("status",{}).get("phase"),
        "ready":all(c.get("ready",False) for c in p.get("status",{}).get("containerStatuses",[]))
                 if p.get("status",{}).get("containerStatuses") else False,
        "containers":[(x.get("name"),x.get("ready")) for x in
                      p.get("status",{}).get("containerStatuses",[])],
    } for p in pods.get("items",[])}


def inspect_contract(case:dict, ns:str, out:Path, kubeconfig:Path, stage:str)->dict:
    typ=case["contract"]["type"]
    expected=case["contract"]["expected"]
    if typ=="ksm_namespace_flag":
        expected="--namespaces="+ns
    if typ in ("argo_url","argo_rbac_default","argo_cm_exists"):
        name="argocd-rbac-cm" if typ=="argo_rbac_default" else "argocd-cm"
        cm,cmd=kubectl_json(["get","cm",name,"-n",ns,"-o","json"],out,stage+"_get_cm_"+name,kubeconfig)
        value=(cm.get("data") or {}).get(
            "policy.default" if typ=="argo_rbac_default" else "url")
        if typ=="argo_cm_exists":
            # An externally owned ConfigMap can exist in the API while the
            # original chart quite intentionally does NOT install/manage it.
            # Distinguish ownership from resource presence to avoid a false
            # "failure" in the old state.
            ann=cm.get("metadata",{}).get("annotations",{}) or {}
            value=ann.get("meta.helm.sh/release-name")=="n02"
            return {"expected":expected,"observed_helm_owns_cm":value,
                    "external_cm_exists":bool(cm),"pass":value==expected,"kubectl":cmd}
        return {"expected":expected,"observed":value,"pass":value==expected,"kubectl":cmd}
    if typ=="argo_ingress_host":
        ing,cmd=kubectl_json(["get","ingress","-n",ns,"-o","json"],out,stage+"_get_ingress",kubeconfig)
        hosts=[r.get("host") for item in ing.get("items",[])
               for r in item.get("spec",{}).get("rules",[])]
        return {"expected":expected,"observed":hosts,"pass":expected in hosts,"kubectl":cmd}
    if typ in ("ksm_namespace_flag","prometheus_job_names"):
        kind="deploy" if typ=="ksm_namespace_flag" else "cm"
        payload,cmd=kubectl_json(["get",kind,"-l","app.kubernetes.io/instance=n02",
                                   "-n",ns,"-o","json"],out,stage+"_get_"+kind,kubeconfig)
        if typ=="ksm_namespace_flag":
            args=[v for item in payload.get("items",[])
                  for c in item.get("spec",{}).get("template",{}).get("spec",{}).get("containers",[])
                  for v in c.get("args",[])]
            raw=[x for x in args if x.startswith("--namespaces=") or x.startswith("--namespace=")]
            observed=["--namespaces="+x.split("=",1)[1] for x in raw]
            return {"expected":expected,"observed_normalized":observed,
                    "raw_args":raw,"pass":expected in observed,
                    "kubectl":cmd}
        jobs=[]
        for item in payload.get("items",[]):
            source=(item.get("data") or {}).get("prometheus.yml")
            if source:
                config=yaml.safe_load(source) or {}
                jobs=[x.get("job_name") for x in config.get("scrape_configs",[])]
                break
        return {"expected":sorted(expected),"observed":sorted(jobs),
                "pass":sorted(jobs)==sorted(expected),"kubectl":cmd}
    return {"error":"unsupported extractor: "+typ}


def port_forward_probe(case:dict,ns:str,out:Path,kubeconfig:Path,stage:str)->dict:
    """Use actual Pod-serving service endpoints; never infer reachability from manifest."""
    services,record=kubectl_json(["get","svc","-l","app.kubernetes.io/instance=n02",
                                  "-n",ns,"-o","json"],out,stage+"_list_services",kubeconfig)
    if not services:
        return {"status":"no_services","kubectl":record}
    fam=case["family"]
    candidates=services.get("items",[])
    def preferred(item:dict)->bool:
        name=item.get("metadata",{}).get("name","")
        return (("argocd-server" in name) if fam=="argo" else
                ("prometheus-server" in name) if fam=="prometheus" else
                ("kube-state-metrics" in name))
    candidates=[item for item in candidates if preferred(item)]
    if not candidates:
        return {"status":"required_service_not_present"}
    svc=candidates[0]
    ports=svc.get("spec",{}).get("ports",[])
    if not ports:
        return {"status":"no_service_port"}
    # Port is a service port, not a pod container port.
    preferred_port=next((x for x in ports if x.get("name") in ("http","http-web","http-metrics")),ports[0])
    with socket.socket() as sk:
        sk.bind(("127.0.0.1",0))
        local=sk.getsockname()[1]
    remote=preferred_port["port"]
    proc=subprocess.Popen(["kubectl","--kubeconfig",str(kubeconfig),
        "port-forward",f"svc/{svc['metadata']['name']}",
        f"{local}:{remote}","-n",ns,"--address","127.0.0.1"],
        cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        ready=False
        for _ in range(30):
            if proc.poll() is not None:break
            try:
                with socket.create_connection(("127.0.0.1",local),timeout=.3):
                    ready=True
                    break
            except OSError:
                time.sleep(.3)
        if not ready:
            return {"status":"port_forward_unavailable","service":svc["metadata"]["name"]}
        paths=("/metrics",) if fam=="ksm" else (
            ("/api/v1/targets","/api/v1/status/config","/-/ready")
            if fam=="prometheus" else ("/healthz","/api/version","/api/v1/settings"))
        data={}
        for path in paths:
            try:
                with urlopen(f"http://127.0.0.1:{local}{path}",timeout=10) as response:
                    body=response.read(5_000_000).decode(errors="replace")
                    (out/f"{stage}_api_{path.strip('/').replace('/','_')}").write_text(body)
                    data[path]={"http":response.status,"bytes":len(body)}
                    if fam=="ksm" and path=="/metrics":
                        metriclines=[x for x in body.splitlines()
                                     if x.startswith("kube_configmap_info{")]
                        data[path]["configmap_namespace_samples"]=[
                            x[:450] for x in metriclines][:30]
                        data[path]["focus_namespace_metric_lines"]=sum(
                            f'namespace="{ns}"' in x for x in metriclines)
                        data[path]["control_namespace_metric_lines"]=sum(
                            f'namespace="{ns}-control"' in x for x in metriclines)
                        data[path]["scope_evidence"]="Old should have focus>0/control==0; new expanded-scope should have control>0. Missing metrics invalidate probe."
                    if fam=="prometheus" and path=="/api/v1/targets":
                        try:
                            parsed=json.loads(body)
                            d=parsed.get("data") or {}
                            data[path]["active_target_count"]=len(d.get("activeTargets",[]))
                            data[path]["dropped_target_count"]=len(d.get("droppedTargets",[]))
                        except json.JSONDecodeError:
                            pass
                    if fam=="prometheus" and path=="/api/v1/status/config":
                        try:
                            config=yaml.safe_load((json.loads(body).get("data") or {}).get("yaml","")) or {}
                            data[path]["loaded_job_names"]=[
                                x.get("job_name") for x in config.get("scrape_configs",[])]
                        except (ValueError,TypeError,yaml.YAMLError):
                            pass
            except Exception as exc:
                data[path]={"error":str(exc)}
        if fam=="argo":
            data["authorization_probe"]="NOT DONE: requires authenticated non-admin Argo account"
            data["ingress_external_route"]="NOT DONE: requires a working ingress controller"
        return {"status":"probed","service":svc["metadata"]["name"],
                "service_port":remote,"endpoints":data}
    finally:
        proc.terminate()
        try:proc.communicate(timeout=6)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()


def main()->None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case",required=True,choices=sorted(CASES))
    parser.add_argument("--policy",required=True,choices=sorted(POLICIES))
    parser.add_argument("--namespace",required=True)
    parser.add_argument("--kubeconfig",type=Path,required=True)
    parser.add_argument("--confirm-disposable-cluster",action="store_true",required=True)
    parser.add_argument("--cleanup-created-namespaces",action="store_true")
    parser.add_argument("--out",type=Path)
    args=parser.parse_args()
    if not args.namespace.startswith("n02-") or len(args.namespace)>62:
        raise SystemExit("Namespace must be a fresh, study-owned n02-* name")
    if not args.kubeconfig.is_file():
        raise SystemExit("No kubeconfig file; cannot perform actual deployment")
    if not os.path.exists("/usr/bin/kubectl") and not shutil_which("kubectl"):
        raise SystemExit("No kubectl; cannot perform actual deployment")
    rows=yaml.safe_load((ROOT/"cases.yaml").read_text())
    case=next(x for x in rows["cases"] if x["id"]==args.case)
    spec=rows["families"][case["family"]]
    out=args.out or PHASE/"results"/"live_cluster"/f"{args.case}_{args.policy}"
    out.mkdir(parents=True,exist_ok=True)
    now=datetime.now(timezone.utc).isoformat()
    report={"date_utc":now,"case":args.case,"policy":args.policy,"namespace":args.namespace,
            "actual_cluster":True,"commands":[],"states":{}}
    try:
        def cmd(args_:list[str],name:str,check:bool=False,timeout:int=600)->dict:
            ret=command(args_,ROOT,out,name,check=check,timeout=timeout)
            report["commands"].append(ret)
            return ret
        K=["kubectl","--kubeconfig",str(args.kubeconfig)]
        H=[str(ROOT/"toolchain/linux-amd64/helm"),"--kubeconfig",str(args.kubeconfig)]
        # Keep Helm diff plugin isolated to supplied toolchain, not user's global install.
        env=os.environ.copy()
        env["HELM_PLUGINS"]=str((ROOT/"toolchain/plugins").resolve())
        # Instead of invoking a shell, run helm through a direct env binary.
        # argv[0] 'env' is a standard executable; no user-provided shell text.
        D=["env",f"HELM_PLUGINS={env['HELM_PLUGINS']}",
           f"KUBECONFIG={args.kubeconfig}",
           str(ROOT/"toolchain/linux-amd64/helm")]
        current=cmd(K+["config","current-context"],"current_context",check=True)
        context=(out/current["stdout_file"]).read_text().strip()
        report["kube_context"]=context
        if not any(token in context.lower() for token in ("kind","minikube","k3d","n02")):
            raise RuntimeError(f"Refusing possibly non-disposable kube context: {context}")
        cmd(K+["get","nodes","-o","json"],"cluster_nodes",check=True)
        checkns=cmd(K+["get","namespace",args.namespace], "namespace_must_not_exist")
        if checkns["rc"]==0:
            raise RuntimeError("Existing namespace; refuse to collide with earlier experiment")
        cmd(K+["create","namespace",args.namespace],"create_namespace",check=True)
        report["created_namespace"]=True
        if args.case=="K04_namespace":
            if len(args.namespace)>54:
                raise RuntimeError("Namespace too long for '-control' suffix")
            other=args.namespace+"-control"
            exists=cmd(K+["get","namespace",other],"other_namespace_must_not_exist")
            if exists["rc"]==0:
                raise RuntimeError("Fixture namespace already exists; refuse collision")
            cmd(K+["create","namespace",other],"create_other_namespace",check=True)
            report["created_other_namespace"]=other
            for target in (args.namespace,other):
                cmd(K+["create","configmap","n02-scope-probe",
                       "--from-literal=study=namespace-filter","-n",target],
                    "fixture_"+target,check=True)
        user=copy.deepcopy(case["old_user"])
        migrated=copy.deepcopy(case["migrated_user"])
        if args.case=="K04_namespace":
            user["namespace"]=args.namespace
            migrated["namespaces"]=[args.namespace]
        if args.case=="A04_config_enabled":
            # Externally supplied config may cause an upgrade OWNERSHIP ERROR,
            # invalidating the previous 'silent' interpretation: keep this.
            cmd(K+["create","configmap","argocd-cm","--from-literal=url=https://external.example.invalid",
                   "-n",args.namespace],"create_external_cm",check=True)
        oldfile=out/"old-user-values.yaml"
        newfile=out/"migrated-values.yaml"
        oldfile.write_text(yaml.safe_dump(user))
        newfile.write_text(yaml.safe_dump(migrated))
        oldchart=ROOT/"charts"/spec["from"]
        newchart=ROOT/"charts"/spec["to"]
        install=cmd(H+["install","n02",str(oldchart),"-n",args.namespace,
                       "-f",str(oldfile),"--wait","--timeout","8m"],
                    "helm_install_old",timeout=540)
        if install["rc"]!=0:
            report["blocked_stage"]="old_install_failed"
            return
        podold,_=kubectl_json(["get","pods","-l","app.kubernetes.io/instance=n02",
                                "-n",args.namespace,"-o","json"],out,"pods_old",args.kubeconfig)
        report["states"]["old_pods"]=choose_pod_status(podold)
        report["states"]["old_contract"]=inspect_contract(case,args.namespace,out,args.kubeconfig,"old")
        report["states"]["old_endpoint"]=port_forward_probe(case,args.namespace,out,args.kubeconfig,"old")
        cmd(H+["get","values","n02","-n",args.namespace,"-o","yaml"],"get_historical_values",check=True)
        cmd(H+["get","manifest","n02","-n",args.namespace],"get_historical_manifest",check=True)
        flags=POLICIES[args.policy]
        newargs=["-f",str(newfile)] if args.policy=="migrated" else []
        diff=cmd(D+["diff","upgrade","n02",str(newchart),"-n",args.namespace,
                    *flags,*newargs,"--no-color"],"native_helm_diff",timeout=180)
        report["native_helm_diff_rc"]=diff["rc"]
        upgrade=cmd(H+["upgrade","n02",str(newchart),"-n",args.namespace,
                       *flags,*newargs,"--wait","--timeout","8m"],
                    "helm_upgrade_new",timeout=540)
        report["upgrade_succeeded"]=upgrade["rc"]==0
        podnew,_=kubectl_json(["get","pods","-l","app.kubernetes.io/instance=n02",
                                "-n",args.namespace,"-o","json"],out,"pods_new",args.kubeconfig)
        report["states"]["new_pods"]=choose_pod_status(podnew)
        report["states"]["new_contract"]=inspect_contract(case,args.namespace,out,args.kubeconfig,"new")
        report["states"]["new_endpoint"]=port_forward_probe(case,args.namespace,out,args.kubeconfig,"new")
        cmd(H+["history","n02","-n",args.namespace,"-o","json"],"release_history")
        report["observed_runtime_level"]="Native Pod readiness and reachable APIs; see missing RBAC/Ingress caveats"
    except Exception as e:
        report["exception"]=str(e)
    finally:
        if args.cleanup_created_namespaces and report.get("created_namespace"):
            report["cleanup_release"]=command(
                [str(ROOT/"toolchain/linux-amd64/helm"),"--kubeconfig",
                 str(args.kubeconfig),"uninstall","n02","-n",args.namespace],
                ROOT,out,"cleanup_research_helm_release",timeout=120)
            report["cleanup_command"]=command(
                ["kubectl","--kubeconfig",str(args.kubeconfig),"delete","namespace",
                 args.namespace,"--wait=true","--timeout=180s"],
                ROOT,out,"cleanup_study_owned_namespace",timeout=220)
        if args.cleanup_created_namespaces and report.get("created_other_namespace"):
            report["cleanup_other_command"]=command(
                ["kubectl","--kubeconfig",str(args.kubeconfig),"delete","namespace",
                 report["created_other_namespace"],"--wait=true","--timeout=180s"],
                ROOT,out,"cleanup_other_study_owned_namespace",timeout=220)
        (out/"actual_cluster_run.json").write_text(json.dumps(report,indent=2))
        print(json.dumps({"case":args.case,"policy":args.policy,"report":str(out/"actual_cluster_run.json"),
                          "blocked_stage":report.get("blocked_stage"),
                          "error":report.get("exception"),
                          "upgrade_succeeded":report.get("upgrade_succeeded")},indent=2))


def shutil_which(name:str)->str|None:
    import shutil
    return shutil.which(name)


if __name__=="__main__":
    main()
