#!/usr/bin/env python3
"""Run genuine helm-diff against a correctly Helm-encoded synthetic Release Secret.

The Secret is served over a loopback Kubernetes-API *stub*. The plugin sees real
Helm Release JSON/Config/Chart/Manifest and uses its actual native code paths,
but there is NO Kubernetes cluster, Pod, or real Helm install here. This is an
offline plugin-behavior baseline, not a production-deployment comparison.
"""
from __future__ import annotations

import argparse
import base64
import gzip
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
from urllib.parse import urlparse

import yaml

ROOT = Path(__file__).resolve().parent.parent
PHASE = ROOT/"phase2"
sys.path.insert(0,str(ROOT/"scripts"))
import run_study as original


class FauxKubernetesHandler(BaseHTTPRequestHandler):
    server_version = "N02HelmReleaseReadOnly/1"
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        path=urlparse(self.path).path
        self.server.calls.append(path)
        if path in ("/version",):
            return self.write(200,{"major":"1","minor":"30","gitVersion":"v1.30.0",
                                   "gitCommit":"offline-release-stub","platform":"linux/amd64"})
        if path in ("/api","/api/"):
            return self.write(200,{"kind":"APIVersions","versions":["v1"],"serverAddressByClientCIDRs":[]})
        if path == "/apis":
            return self.write(200,{"kind":"APIGroupList","apiVersion":"v1","groups":[]})
        if path == "/api/v1":
            return self.write(200,{"kind":"APIResourceList","apiVersion":"v1","groupVersion":"v1",
                                   "resources":[
                                       {"name":"secrets","namespaced":True,"kind":"Secret","verbs":["get","list"]},
                                       {"name":"namespaces","namespaced":False,"kind":"Namespace","verbs":["get"]},
                                   ]})
        if path == "/api/v1/namespaces/n02-test":
            return self.write(200,{"kind":"Namespace","apiVersion":"v1",
                                   "metadata":{"name":"n02-test"}})
        if path == "/api/v1/namespaces/n02-test/secrets":
            return self.write(200,{"apiVersion":"v1","kind":"SecretList",
                                   "metadata":{"resourceVersion":"1"},
                                   "items":[self.server.secret]})
        if path == "/api/v1/namespaces/n02-test/secrets/sh.helm.release.v1.n02.v1":
            return self.write(200,self.server.secret)
        return self.write(404,{"kind":"Status","apiVersion":"v1","status":"Failure",
                               "reason":"NotFound","code":404,"message":path})

    def write(self,status:int,body:dict):
        data=json.dumps(body,separators=(",",":")).encode()
        self.send_response(status)
        self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def extract_chart(path:Path)->tuple[dict,dict]:
    with tarfile.open(path,"r:gz") as archive:
        files={m.name.split("/",1)[-1]:m for m in archive.getmembers()
               if m.isfile() and "/" in m.name}
        meta=yaml.safe_load(archive.extractfile(files["Chart.yaml"]).read())
        defaults=yaml.safe_load(archive.extractfile(files["values.yaml"]).read()) or {}
    return meta,defaults


def encode_release(manifest:str,values:dict,meta:dict,defaults:dict)->dict:
    rel={
        "name":"n02",
        "info":{"first_deployed":"2024-02-01T00:00:00Z",
                "last_deployed":"2024-02-01T00:00:00Z",
                "deleted":"0001-01-01T00:00:00Z","description":"Synthetic install",
                "status":"deployed"},
        "chart":{"metadata":meta,"values":defaults,"templates":[],"files":[]},
        "config":values,"manifest":manifest,
        "version":1,"namespace":"n02-test"
    }
    packed=gzip.compress(json.dumps(rel,separators=(",",":")).encode(),mtime=0)
    data=base64.b64encode(base64.b64encode(packed)).decode()
    return {"apiVersion":"v1","kind":"Secret",
            "metadata":{"name":"sh.helm.release.v1.n02.v1","namespace":"n02-test",
                        "labels":{"owner":"helm","name":"n02",
                                  "status":"deployed","version":"1",
                                  "createdAt":"1706745600"},"resourceVersion":"1"},
            "type":"helm.sh/release.v1","data":{"release":data}}


def render_exact(helm:Path,chart:Path,values:dict)->str:
    p=subprocess.run([str(helm),"template","n02",str(chart),
                      "--is-upgrade","--namespace","n02-test",
                      "--kube-version","1.30.0","-f","-"],
                     input=yaml.safe_dump(values),text=True,capture_output=True,
                     check=True,timeout=60)
    return p.stdout


def main()->None:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--concise",action="store_true",
                    help="Produce normalized 3-context-line diffs: a stronger reviewer baseline")
    args=ap.parse_args()
    helm=ROOT/"toolchain/linux-amd64/helm"
    plugins=ROOT/"toolchain/plugins"
    assert helm.is_file() and (plugins/"helm-diff").exists()
    cases=yaml.safe_load((ROOT/"cases.yaml").read_text())
    out=PHASE/"results"/"helm_diff_transcripts"
    out.mkdir(parents=True,exist_ok=True)
    server=ThreadingHTTPServer(("127.0.0.1",0),FauxKubernetesHandler)
    server.secret={}
    server.calls=[]
    thread=threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    allresults=[]
    with tempfile.TemporaryDirectory(prefix="n02-helm-diff-") as td:
        kubeconfig=Path(td)/"kubeconfig.yaml"
        kubeconfig.write_text(yaml.safe_dump({
            "apiVersion":"v1","kind":"Config",
            "current-context":"local","clusters":[
                {"name":"loopback","cluster":{"server":f"http://127.0.0.1:{server.server_port}"}}
            ],"users":[{"name":"unprivileged","user":{}}],
            "contexts":[{"name":"local","context":{"cluster":"loopback",
                                                  "user":"unprivileged","namespace":"n02-test"}}],
        }))
        env=os.environ.copy()
        env["HELM_PLUGINS"]=str(plugins.resolve())
        env["HELM_CACHE_HOME"]=str((Path(td)/"cache").resolve())
        env["HELM_CONFIG_HOME"]=str((Path(td)/"config").resolve())
        env["KUBECONFIG"]=str(kubeconfig)
        env["HELM_DIFF_COLOR"]="false"
        print(f"Loopback ONLY: 127.0.0.1:{server.server_port}; simulated release storage",flush=True)
        for case in cases["cases"]:
            family=case["family"]
            familymeta=cases["families"][family]
            oldchart=ROOT/"charts"/familymeta["from"]
            newchart=ROOT/"charts"/familymeta["to"]
            chartmeta,chartdefaults=extract_chart(oldchart)
            oldvalues=case["old_user"]
            oldmanifest=render_exact(helm,oldchart,oldvalues)
            server.secret=encode_release(oldmanifest,oldvalues,chartmeta,chartdefaults)
            server.calls=[]
            cmd=[str(helm),"diff","upgrade","n02",str(newchart),
                 "--namespace","n02-test","--reset-then-reuse-values",
                 "--disable-validation","--kube-version","1.30.0",
                 "--no-color"]
            if args.concise:
                cmd.extend(["--normalize-manifests","--context","3"])
            started=time.monotonic()
            r=subprocess.run(cmd,env=env,cwd=str(ROOT),text=True,
                             capture_output=True,timeout=90)
            elapsed=time.monotonic()-started
            transcript=out/f"{case['id']}{'.concise' if args.concise else ''}.diff"
            transcript.write_text(r.stdout)
            row={
                "case":case["id"],"family":family,"label":case["label"],
                "release_history":"synthetically encoded Helm v3 Secret; not installed in Kubernetes",
                "helm_diff_plugin":"installed plugin (native binary)",
                "method":"helm diff upgrade ... --reset-then-reuse-values --disable-validation",
                "exit_code":r.returncode,
                "stdout_lines":len(r.stdout.splitlines()),
                "stdout_bytes":len(r.stdout.encode()),
                "plugin_wall_seconds":round(elapsed,4),
                "plus_lines":sum(line.startswith("+") and not line.startswith("++")
                                 for line in r.stdout.splitlines()),
                "minus_lines":sum(line.startswith("-") and not line.startswith("--")
                                  for line in r.stdout.splitlines()),
                "stderr":r.stderr[-2400:],
                "api_requests":server.calls.copy(),
                "transcript":transcript.name,
                "documented_actionable_migration":
                    bool(case.get("documented_actionable_migration")),
            }
            allresults.append(row)
            print(f"{case['id']:<26} exit={r.returncode} lines={row['stdout_lines']}"
                  f" secret_reads={sum('/secrets' in s for s in server.calls)}",flush=True)
    server.shutdown()
    reportpath=("helm_diff_concise_replay.json" if args.concise
                else "helm_diff_replay.json")
    (PHASE/"results"/reportpath).write_text(
        json.dumps({"mode":"GENUINE PLUGIN AGAINST SYNTHETIC READONLY RELEASE SECRET",
                    "no_cluster_or_live_pods":True,
                    "strong_baseline_settings":"normalize + context 3" if args.concise else "plugin defaults",
                    "rows":allresults},
                   indent=2,ensure_ascii=False))
    print(f"SUCCESSFUL native plugin calls: "
          f"{sum(x['exit_code']==0 for x in allresults)}/{len(allresults)}",flush=True)


if __name__=="__main__":
    main()
