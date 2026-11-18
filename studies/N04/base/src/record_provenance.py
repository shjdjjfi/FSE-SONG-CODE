"""Record pinned public inputs and SHA-256 integrity manifest, no secrets."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess


REPOS={
    "idoft":"TestingResearchIllinois/idoft",
    "flaky-test-dataset":"test-flare/flaky-test-dataset",
    "java-cas-client":"apereo/java-cas-client",
    "delight-nashorn-sandbox":"javadelight/delight-nashorn-sandbox",
    "java-websocket":"TooTallNate/Java-WebSocket",
    "tyrus":"eclipse-ee4j/tyrus",
    "yawp":"feroult/yawp",
    "fluent-logger-java":"fluent/fluent-logger-java",
    "helios":"spotify/helios",
    "nexus-repository-helm":"sonatype-nexus-community/nexus-repository-helm",
    "openhtmltopdf":"danfickle/openhtmltopdf",
    "riptide":"zalando/riptide",
    "json-io":"jdereg/json-io",
    "spring-cloud-kubernetes":"spring-cloud/spring-cloud-kubernetes",
    "graphhopper":"graphhopper/graphhopper",
    "activiti":"Activiti/Activiti",
    "guava":"google/guava",
    "alibaba-druid":"alibaba/druid",
    "c2mon":"c2mon/c2mon",
    "maven-doxia":"apache/maven-doxia",
}


def file_hash(path:Path,algorithm="sha256"):
    h=hashlib.new(algorithm)
    with path.open("rb") as stream:
        for chunk in iter(lambda:stream.read(1<<20), b""):
            h.update(chunk)
    return h.hexdigest()


def record(root:Path,inputs:Path):
    heads={}
    for name,slug in REPOS.items():
        repo=inputs/name
        if not (repo/".git").exists():
            heads[slug]={"present":False}
            continue
        run=subprocess.run(["git","-C",str(repo),"rev-parse","HEAD"],
                           text=True,capture_output=True)
        heads[slug]={"present":run.returncode==0,"git_head":run.stdout.strip() if run.returncode==0 else None,
                     "url":"https://github.com/"+slug}
    versions={}
    for pkg in ("pytest","tree-sitter","tree-sitter-java","numpy","scipy","matplotlib"):
        try:versions[pkg]=importlib.metadata.version(pkg)
        except importlib.metadata.PackageNotFoundError:versions[pkg]=None
    archive=inputs/"flaky_histories_dataset.tgz"
    data={"snapshot_semantics":"Public Git revisions fixed at execution; not exact historical CI runtime",
          "toolchain":{"python":platform.python_version(),"platform":platform.platform(),
                       "packages":versions},
          "repository_heads":heads,
          "ftw_downloaded_archive":{"source_url":"https://zenodo.org/records/10639030",
                                    "present":archive.exists(),
                                    "md5":file_hash(archive,"md5") if archive.exists() else None,
                                    "sha256":file_hash(archive) if archive.exists() else None},
          "bundle_sha256":{str(x.relative_to(root)):file_hash(x)
                           for x in sorted(root.rglob("*")) if x.is_file() and
                           ("__pycache__" not in x.parts) and
                           x!=root/"results"/"provenance.json" and
                           x.suffix not in (".pyc",)}}
    return data


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument("--inputs",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    d=record(a.root.resolve(),a.inputs.resolve())
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(d,indent=2),encoding="utf-8")
    print("Recorded",len(d["repository_heads"]),"public repos and",len(d["bundle_sha256"]),"file SHA256 checksums")
