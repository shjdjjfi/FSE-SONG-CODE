#!/usr/bin/env python3
"""Start real Prometheus v3.8.1 locally and probe its /api/v1/status/config.

The server listens ONLY on 127.0.0.1 and is terminated after each probe.
Its Kubernetes service discovery cannot contact a cluster here; we are
validating *loaded configuration and startup*, not live scrape success.
"""
from __future__ import annotations

import json
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

import yaml

ROOT = Path(__file__).resolve().parent.parent


def unused_loopback_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def adapt_for_no_kubernetes(original: Path, destination: Path) -> dict:
    config=yaml.safe_load(original.read_text())
    count=0
    for job in config.get("scrape_configs",[]):
        # Preserve *only* the job inventory and its job_name.  Prometheus
        # Kubernetes SD and serviceaccount paths cannot be used off-cluster.
        for key in ("kubernetes_sd_configs","file_sd_configs","dns_sd_configs",
                    "ec2_sd_configs","gce_sd_configs","tls_config","authorization",
                    "bearer_token_file","bearer_token"):
            job.pop(key,None)
        job["static_configs"]=[{"targets":["127.0.0.1:65535"]}]
        count+=1
    config["alerting"]={"alertmanagers":[]}
    config["rule_files"]=[]
    destination.write_text(yaml.safe_dump(config,sort_keys=False))
    return {
        "sanitized_jobs":count,
        "transformations":[
            "removed cluster-dependent discovery and credential file fields",
            "replaced each discovery target with unreachable loopback address",
            "disabled rule file loading and alertmanager discovery",
            "preserved each job_name; not an exact chart workload",
        ]
    }


def probe(binary: Path, config: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix="n02-prometheus-") as folder:
        port=unused_loopback_port()
        cmd=[
            str(binary),
            "--config.file="+str(config),
            "--storage.tsdb.path="+folder,
            "--web.listen-address=127.0.0.1:"+str(port),
            "--log.level=error",
            "--web.enable-lifecycle",
        ]
        started=time.monotonic()
        process=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                                 text=True)
        try:
            config_response=None
            last_error=None
            for _ in range(100):
                if process.poll() is not None:
                    break
                try:
                    req=urllib.request.Request(
                        f"http://127.0.0.1:{port}/api/v1/status/config"
                    )
                    with urllib.request.urlopen(req,timeout=1) as response:
                        data=json.load(response)
                    if data.get("status")=="success":
                        config_response=data
                        break
                except (OSError, urllib.error.URLError, TimeoutError, ValueError) as exc:
                    last_error=str(exc)
                time.sleep(.12)
            if config_response is None:
                log_text=(process.stdout.read()[-4000:]
                          if process.poll() is not None and process.stdout else "")
                return {
                    "started":False,
                    "elapsed_s":round(time.monotonic()-started,3),
                    "error":last_error,
                    "process_exit":process.poll(),
                    "log_tail":log_text,
                }
            running_config=yaml.safe_load(config_response["data"]["yaml"])
            jobs=[job["job_name"] for job in running_config["scrape_configs"]]
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/-/ready",timeout=3) as response:
                readiness=response.status
            return {
                "started":True, "readiness_http_status":readiness,
                "elapsed_s":round(time.monotonic()-started,3),
                "loaded_scrape_jobs":jobs,
                "job_count":len(jobs),
                "custom_job_present":"n02-contract" in jobs,
                "extra_jobs":sorted(set(jobs)-{"n02-contract"}),
                "api":"GET /api/v1/status/config",
                "endpoint_bound_to_loopback_only":True,
            }
        finally:
            process.terminate()
            try:
                process.communicate(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate(timeout=5)


def main() -> None:
    binary=ROOT/"toolchain/prometheus-3.8.1.linux-amd64/prometheus"
    configs=ROOT/"results/prometheus_configs"
    if not binary.is_file():
        raise SystemExit("Official Prometheus v3.8.1 binary missing")
    arms=["new_reset_then_reuse_emulated", "new_manually_migrated"]
    report={
        "binary":"official prometheus v3.8.1",
        "verification":"real localhost process /-/ready and /api/v1/status/config",
        "scope_limit":"exact original chart configs cannot start off-cluster; successful probes use a transparently sanitized job-inventory-only adaptation",
        "results":[],
    }
    for arm in arms:
        original=configs/(arm+".yml")
        raw=probe(binary,original)
        adapted=configs/(arm+"_local_probe.yml")
        modifications=adapt_for_no_kubernetes(original,adapted)
        data=probe(binary,adapted)
        report["results"].append({
            "arm":arm,"original_exact_config":raw,
            "local_probe_transformations":modifications,
            "local_probe_config":str(adapted.relative_to(ROOT)),
            "adapted_probe":data,
        })
        print(arm,"original_started=",raw["started"],
              "adapted_started=",data["started"],
              "adapted_jobs=",data.get("job_count"),flush=True)
    (ROOT/"results/prometheus_runtime_probe.json").write_text(
        json.dumps(report,indent=2,ensure_ascii=False)
    )
    records={r["arm"]:r for r in report["results"]}
    assert all(r["adapted_probe"]["started"] and
               r["adapted_probe"]["readiness_http_status"]==200
               for r in report["results"])
    assert records[arms[0]]["adapted_probe"]["job_count"]==11
    assert records[arms[1]]["adapted_probe"]["job_count"]==1
    print("PASS: Local adapted Prometheus configs started and exposed 11 versus 1 jobs.",
          flush=True)


if __name__=="__main__":
    main()
