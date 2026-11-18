#!/usr/bin/env python3
"""Native helm-diff v3.12 on synthetic (never installed) Helm v3 releases.

Transcript evidence for the release-history diff component of a practical
reviewer baseline. The official release notes must be reviewed separately.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
from http.server import ThreadingHTTPServer

import yaml

ROOT = Path(__file__).resolve().parent.parent
HERE = ROOT / "phase3"
sys.path.insert(0, str(ROOT / "phase2"))
sys.path.insert(0, str(HERE))
import helm_diff_historical_replay as hd
import run_external_challenge as ext


def main():
    helm = ROOT / "toolchain/linux-amd64/helm"
    plugins = ROOT / "toolchain/plugins"
    assert helm.is_file() and (plugins / "helm-diff").exists()
    transcript_dir = HERE / "results/helm_diff_transcripts"
    transcript_dir.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", 0), hd.FauxKubernetesHandler)
    server.secret = {}
    server.calls = []
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    rows = []
    try:
        with tempfile.TemporaryDirectory(prefix="n02-phase3-diff-") as td:
            tmp = Path(td)
            kubeconfig = tmp / "kubeconfig.yaml"
            kubeconfig.write_text(yaml.safe_dump({
                "apiVersion": "v1", "kind": "Config", "current-context": "local",
                "clusters": [{"name": "loopback", "cluster": {
                    "server": f"http://127.0.0.1:{server.server_port}"}}],
                "users": [{"name": "unprivileged", "user": {}}],
                "contexts": [{"name": "local", "context": {
                    "cluster": "loopback", "user": "unprivileged",
                    "namespace": "n02-test"}}],
            }))
            env = os.environ.copy()
            env["HELM_PLUGINS"] = str(plugins.resolve())
            env["HELM_CACHE_HOME"] = str((tmp / "cache").resolve())
            env["HELM_CONFIG_HOME"] = str((tmp / "config").resolve())
            env["KUBECONFIG"] = str(kubeconfig)
            env["HELM_DIFF_COLOR"] = "false"
            for case in ext.CASES:
                oldchart = ext.chart(case, case["old"])
                newchart = ext.chart(case, case["new"])
                oldvals = ext.overlay(ext.context(case), case["values"])
                meta, defaults = hd.extract_chart(oldchart)
                try:
                    manifest = hd.render_exact(helm, oldchart, oldvals)
                except subprocess.CalledProcessError as err:
                    rows.append({"case": case["id"], "status": "old_render_failed",
                                 "stderr": err.stderr[-2000:]})
                    continue
                server.secret = hd.encode_release(manifest, oldvals, meta, defaults)
                server.calls = []
                command = [str(helm), "diff", "upgrade", "n02", str(newchart),
                           "--namespace", "n02-test", "--reset-then-reuse-values",
                           "--disable-validation", "--kube-version", "1.30.0",
                           "--normalize-manifests", "--context", "3", "--no-color"]
                started = time.monotonic()
                try:
                    p = subprocess.run(command, env=env, cwd=str(ROOT),
                                       text=True, capture_output=True, timeout=120)
                    elapsed = time.monotonic() - started
                    transcript = transcript_dir / f"{case['id']}.diff"
                    transcript.write_text(p.stdout)
                    rows.append({
                        "case": case["id"], "status": "plugin_executed",
                        "exit_code": p.returncode,
                        "plugin_wall_seconds": round(elapsed, 4),
                        "lines": len(p.stdout.splitlines()),
                        "plus": sum(line.startswith("+") and not line.startswith("++")
                                    for line in p.stdout.splitlines()),
                        "minus": sum(line.startswith("-") and not line.startswith("--")
                                     for line in p.stdout.splitlines()),
                        "stderr": p.stderr[-2000:],
                        "api_reads": server.calls.copy(),
                        "transcript": transcript.name,
                        "release_type": "SYNTHETIC encoded Secret on localhost; no Pods",
                        "history_values": oldvals,
                    })
                except subprocess.TimeoutExpired:
                    rows.append({"case": case["id"], "status": "plugin_timeout"})
                print(f"{case['id']}: {rows[-1]['status']}, "
                      f"lines={rows[-1].get('lines','?')}, "
                      f"exit={rows[-1].get('exit_code','?')}", flush=True)
    finally:
        server.shutdown()
    result = {
        "condition": "native helm-diff v3.12 + synthetic historical release",
        "production_cluster": False,
        "real_operator_decisions": False,
        "reviewer_must_read_diff_and_official_docs": True,
        "cases": rows,
    }
    (HERE / "results/native_diff_external.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False))
    print(f"Plugin returned 0 on "
          f"{sum(x.get('exit_code') == 0 for x in rows)}/{len(rows)} cases")


if __name__ == "__main__":
    main()
