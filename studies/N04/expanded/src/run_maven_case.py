"""Run a pinned 2018 Java-WebSocket refactoring case with Maven, CPU-only.

Automatically uses only the currently configured HTTPS proxy, if present.
The source checkout is not modified. Maven build logs and return codes are
archived even if upstream dependencies or old Java compatibility block tests.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import tempfile
import time
import re
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path


def run(root:Path, maven:Path, source:Path, repo:Path, timeout:int, repeat:int,
        java_home:Path|None=None, goal:str="test"):
    root.mkdir(parents=True, exist_ok=True)
    maven = maven.resolve()
    source = source.resolve()
    repo = repo.resolve()
    environment=os.environ.copy()
    if java_home is not None:
        jdk=java_home.resolve()
        environment["JAVA_HOME"]=str(jdk)
        environment["PATH"]=str(jdk/"bin")+os.pathsep+environment.get("PATH","")
    proxy = urllib.parse.urlparse(os.environ.get("HTTPS_PROXY", ""))
    settings = ET.Element("settings", xmlns="http://maven.apache.org/SETTINGS/1.2.0")
    if proxy.hostname and proxy.port:
        container = ET.SubElement(settings, "proxies")
        for proto in ("http", "https"):
            p = ET.SubElement(container, "proxy")
            for key, val in (("id", "configured-network-route"), ("active", "true"),
                             ("protocol", proto), ("host", proxy.hostname), ("port", str(proxy.port))):
                ET.SubElement(p, key).text=val
    with tempfile.TemporaryDirectory(prefix="n04-maven-settings-") as temp:
        settings_file = Path(temp) / "settings.xml"
        ET.ElementTree(settings).write(settings_file,encoding="utf-8",xml_declaration=True)
        results=[]
        per_case=[]
        for iteration in range(1,repeat+1):
            args = [str(maven), "--batch-mode", "-s", str(settings_file),
                    "-f", str(source / "pom.xml"), "-Dmaven.repo.local="+str(repo),
                    "-Dtest=Issue256Test,Issue580Test", "-DfailIfNoTests=false",
                    "-Dmaven.compiler.source=8", "-Dmaven.compiler.target=8", goal]
            start=time.perf_counter()
            try:
                proc=subprocess.run(args,capture_output=True,text=True,timeout=timeout,env=environment)
                code=proc.returncode
                logs=proc.stdout+"\n"+proc.stderr
            except subprocess.TimeoutExpired as exc:
                code=124
                logs=(exc.stdout or b"").decode(errors="replace") if isinstance(exc.stdout,bytes) else (exc.stdout or "")
            logpath=root / f"attempt_{iteration:02d}.log"
            logpath.write_text(logs,encoding="utf-8")
            totals=re.findall(r"Tests run:\s*(\d+), Failures:\s*(\d+), Errors:\s*(\d+), Skipped:\s*(\d+)",logs)
            for klass in ("Issue256Test","Issue580Test"):
                report=source/"target"/"surefire-reports"/("TEST-org.java_websocket.issues."+klass+".xml")
                if report.is_file():
                    suite=ET.parse(report).getroot()
                    for test in suite.findall("testcase"):
                        status="passed"
                        if test.find("failure") is not None:
                            status="failed"
                        elif test.find("error") is not None:
                            status="error"
                        elif test.find("skipped") is not None:
                            status="skipped"
                        per_case.append({"iteration":iteration,"class":klass,
                                         "test":test.attrib.get("name",""),"status":status,
                                         "seconds":test.attrib.get("time","")})
            record={"iteration":iteration,"return_code":code,
                    "elapsed_seconds":round(time.perf_counter()-start,3),
                    "log_filename":logpath.name,
                    "dependency_resolution_failure": "Could not resolve" in logs or "could not be resolved" in logs.lower(),
                    "compiler_source_level_failure":"Source option 6 is no longer supported" in logs or "Source option 1.6 is no longer supported" in logs,
                    "tests_ran": "Tests run:" in logs,
                    "overall_test_summary":list(map(int,totals[-1])) if totals else None}
            results.append(record)
            print(json.dumps(record),flush=True)
            # A real test failure is an observation, not an infrastructure
            # failure. Continue until N repetitions even if Surefire exits 1.
            if code and not record["tests_ran"]:
                break
        sha=subprocess.run(["git","-C",str(source),"rev-parse","HEAD"],capture_output=True,text=True).stdout.strip()
        summary={"source_commit":sha,
                 "maven_goal":goal,
                 "source_unmodified":not bool(subprocess.run(["git","-C",str(source),"status","--porcelain"],capture_output=True,text=True).stdout),
                 "java":subprocess.run(["java","-version"],capture_output=True,text=True,env=environment).stderr.splitlines()[0],
                 "network_proxy_configured":bool(proxy.hostname),
                 "results":results,"attempted_post_refactor_test_execution":True,
                 "successful_maven_invocations":sum(r["return_code"]==0 for r in results)}
        if per_case:
            with (root/"junit_cases.csv").open("w",newline="",encoding="utf-8") as f:
                w=csv.DictWriter(f,fieldnames=list(per_case[0]))
                w.writeheader();w.writerows(per_case)
        summary["collected_junit_case_rows"]=len(per_case)
        (root / "maven_attempts.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")


if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path,default=Path("results/java_post"))
    p.add_argument("--maven",type=Path,default=Path("data/tools/apache-maven-3.9.11/bin/mvn"))
    p.add_argument("--source",type=Path,default=Path("data/javawebsocket_post"))
    p.add_argument("--repo",type=Path,default=Path("data/m2"))
    p.add_argument("--timeout",type=int,default=180)
    p.add_argument("--repeat",type=int,default=1)
    p.add_argument("--java-home",type=Path)
    p.add_argument("--goal",choices=["test","surefire:test"],default="test")
    args=p.parse_args()
    run(args.out,args.maven,args.source,args.repo,args.timeout,args.repeat,args.java_home,args.goal)
