"""CPU-only Maven rerun of pinned Java test snapshots.

The tool records compilation/runtime failures as failures to obtain evidence,
not as flaky-test outcomes. Run data are available only if Surefire emitted a
valid test report. Do not mistake this for an actual historical CI trace.
"""

import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
from urllib.parse import urlparse
import xml.etree.ElementTree as ET


def export(repo: Path, sha: str, dest: Path):
    p = subprocess.Popen(["git", "-C", str(repo), "archive", sha],stdout=subprocess.PIPE)
    q = subprocess.run(["tar", "-x", "-C", str(dest)],stdin=p.stdout,capture_output=True,text=True)
    p.stdout.close()
    rc = p.wait()
    if q.returncode or rc:
        raise RuntimeError(f"Could not export {sha}: git={rc} tar={q.stderr[:400]}")


def run_once(repo: Path, sha: str, maven: Path, test_name: str, timeout: int):
    with tempfile.TemporaryDirectory(prefix="n04-maven-") as folder:
        dest = Path(folder)
        export(repo,sha,dest)
        # Historic snapshots target Java 6; our only installed runtime is
        # Java 21, which rejects -source 6.  Record the reversible build-only
        # adaptation explicitly.  This is not an unmodified historical build.
        pom=dest / "pom.xml"
        build_compat="unmodified"
        if pom.exists():
            original=pom.read_text(encoding="utf-8")
            adapted=original.replace("<source>1.6</source>","<source>1.8</source>").replace(
                                   "<target>1.6</target>","<target>1.8</target>")
            if adapted != original:
                pom.write_text(adapted,encoding="utf-8")
                build_compat="build-only Java 6 to Java 8 compiler level adjustment"
        # CORBA was removed from the JDK after Java 8. The *unrelated*
        # InvalidEncodingExceptionTest imports it, preventing every target
        # class from compiling on Java 21. This is an explicitly documented
        # compatibility exclusion confined to the temporary test snapshot.
        unrelated=dest / "src/test/java/org/java_websocket/exceptions/InvalidEncodingExceptionTest.java"
        if unrelated.is_file() and "InvalidEncodingExceptionTest" not in test_name:
            unrelated.unlink()
            build_compat+="; excluded unrelated CORBA-dependent test file"
            # The old test-suite aggregator hard-references the excluded class.
            # It is also unrelated to the requested Issue256Test replay.
            aggregator=dest / "src/test/java/org/java_websocket/exceptions/AllExceptionsTests.java"
            if aggregator.is_file():
                aggregator.unlink()
                build_compat+="; excluded its dependent suite aggregator"
            parent_aggregator=dest / "src/test/java/org/java_websocket/AllTests.java"
            if parent_aggregator.is_file():
                parent_aggregator.unlink()
                build_compat+="; excluded top-level suite aggregator"
        cmd=[str(maven),"--batch-mode","--no-transfer-progress",
             "-U","-Dcheckstyle.skip=true","-Dmaven.javadoc.skip=true",
             "-Dmaven.compiler.source=8","-Dmaven.compiler.target=8",
             f"-Dtest={test_name}","-DfailIfNoTests=false", "test"]
        start=time.perf_counter()
        env=dict(os.environ)
        # The shell's HTTPS proxy is respected by curl, not automatically by
        # the JVM.  Reuse the normally configured session proxy without
        # recording its endpoint or credentials in experiment artifacts.
        proxy=urlparse(env.get("HTTPS_PROXY", ""))
        if proxy.hostname and proxy.port and not proxy.username:
            opts=(f" -Dhttps.proxyHost={proxy.hostname} -Dhttps.proxyPort={proxy.port}"
                  f" -Dhttp.proxyHost={proxy.hostname} -Dhttp.proxyPort={proxy.port}")
            env["MAVEN_OPTS"]=env.get("MAVEN_OPTS", "")+opts
            # Maven Resolver uses its own proxy settings independent of the
            # JVM's java.net system properties.
            settings=dest / "session_maven_settings.xml"
            settings.write_text(
                "<settings><proxies>"+
                "".join("<proxy><id>session-"+protocol+"</id><active>true</active>"+
                        "<protocol>"+protocol+"</protocol><host>"+proxy.hostname+
                        "</host><port>"+str(proxy.port)+"</port></proxy>"
                        for protocol in ("http", "https"))+
                "</proxies></settings>",encoding="utf-8")
            cmd=[cmd[0],"--settings",str(settings),*cmd[1:]]
        try:
            p=subprocess.run(cmd,cwd=dest,capture_output=True,text=True,timeout=timeout,env=env)
            rc=p.returncode
            logs=(p.stdout + "\n" + p.stderr)[-9000:]
        except subprocess.TimeoutExpired as e:
            rc=124
            logs=f"Local timeout after {timeout}s; not treated as test failure. {e}"
        reports=[]
        for xml in sorted(dest.rglob("surefire-reports/TEST-*.xml")):
            try:
                tree=ET.parse(xml)
                root=tree.getroot()
                tests=[]
                for c in root.findall("testcase"):
                    if test_name.split(".")[-1] not in c.get("classname", ""):
                        continue
                    status=("failure" if c.find("failure") is not None else
                            "error" if c.find("error") is not None else
                            "skipped" if c.find("skipped") is not None else "passed")
                    tests.append({"classname":c.get("classname"),
                                  "name":c.get("name"),"status":status})
                if tests:
                    reports.append({"path":str(xml.relative_to(dest)),
                                    "tests":tests,"suite_attrs":dict(root.attrib)})
            except ET.ParseError:
                continue
        return {"git_sha":sha,"returncode":rc,
                "build_compatibility_adjustment":build_compat,
                "elapsed_seconds":round(time.perf_counter()-start,3),
                "test_executions":reports,"test_count":sum(len(x["tests"]) for x in reports),
                "log_tail":logs}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repo",type=Path,required=True)
    p.add_argument("--revisions",nargs="+",required=True)
    p.add_argument("--maven",type=Path,required=True)
    p.add_argument("--test",default="Issue256Test")
    p.add_argument("--repeats",type=int,default=1)
    p.add_argument("--timeout",type=int,default=240)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    entries=[]
    for rev in a.revisions:
        for repeat in range(a.repeats):
            result=run_once(a.repo.resolve(),rev,a.maven.resolve(),a.test,a.timeout)
            result["repeat_index"]=repeat
            entries.append(result)
            print(rev[:12],"repeat",repeat,"rc",result["returncode"],
                  "n_tests",result["test_count"],flush=True)
    output={"type":"offline_CPU_only_Maven_reexecution",
            "not_historical_CI":True,"revisions":a.revisions,"maven_test":a.test,
            "repeats":a.repeats,"outcomes":entries}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(output,indent=2),encoding="utf-8")


if __name__=="__main__":
    main()
