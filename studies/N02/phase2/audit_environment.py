#!/usr/bin/env python3
"""Record only non-sensitive prerequisites that matter for an actual cluster."""
from __future__ import annotations
import json
import os
from pathlib import Path
import shutil
import subprocess

DEST=Path(__file__).resolve().parent/"results"/"execution_prerequisites.json"


def cmd(args:list[str])->dict:
    try:
        p=subprocess.run(args,capture_output=True,text=True,timeout=5)
        return {"exit_code":p.returncode,"stderr_last":p.stderr[-200:]}
    except (FileNotFoundError,subprocess.TimeoutExpired) as e:
        return {"error":type(e).__name__}


def main():
    capline=next((s.split(":",1)[-1].strip() for s in
                  Path("/proc/self/status").read_text().splitlines()
                  if s.startswith("CapEff:")),"unknown")
    data={
        "environment":"this isolated execution workspace, NOT user's own host",
        "docker_cli":bool(shutil.which("docker")),
        "podman_cli":bool(shutil.which("podman")),
        "kubectl_cli":bool(shutil.which("kubectl")),
        "kind_cli":bool(shutil.which("kind")),
        "k3s_cli":bool(shutil.which("k3s")),
        "minikube_cli":bool(shutil.which("minikube")),
        "docker_socket":Path("/var/run/docker.sock").exists(),
        "cgroup2_mount":Path("/sys/fs/cgroup/cgroup.controllers").exists(),
        "effective_capabilities_hex":capline,
        "user_namespace_available":cmd(["unshare","-Ur","true"]),
        "configured_kubeconfig":bool(os.getenv("KUBECONFIG") and
                                     Path(os.environ["KUBECONFIG"]).is_file()),
    }
    data["actual_k8s_cluster_available"]=bool(
        data["kubectl_cli"] and data["configured_kubeconfig"])
    data["interpretation"]="No real Pod / native kubelet experiment conducted if actual_k8s_cluster_available=false"
    DEST.parent.mkdir(parents=True,exist_ok=True)
    DEST.write_text(json.dumps(data,indent=2))
    print(json.dumps(data,indent=2))


if __name__=="__main__":
    main()
