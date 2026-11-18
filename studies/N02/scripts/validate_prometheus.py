#!/usr/bin/env python3
"""Independent Prometheus application parser check of generated real configs.

This invokes the *real promtool binary* (version matching the new chart's
appVersion, v3.8.1) in syntax-only mode.  It proves parser acceptance and the
job inventory; it does NOT prove that a live server scraped these targets.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import yaml

from run_study import deep_merge, find_resource, render


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--promtool", type=Path, default=None)
    args = parser.parse_args()
    root = args.root.resolve()
    promtool = (args.promtool or root/"toolchain/prometheus-3.8.1.linux-amd64/promtool").resolve()
    helm = root/"toolchain/linux-amd64/helm"
    if not promtool.is_file():
        raise SystemExit("Official Prometheus v3.8.1 promtool binary missing; see README.md")
    scenarios = yaml.safe_load((root/"cases.yaml").read_text())
    case = next(c for c in scenarios["cases"] if c["id"]=="P01_legacy_scrape_map")
    charts = scenarios["families"]["prometheus"]
    old = root/"charts"/charts["from"]
    new = root/"charts"/charts["to"]
    old_default = yaml.safe_load(subprocess.run(
        [str(helm), "show", "values", str(old)],
        capture_output=True, text=True, check=True,
    ).stdout)
    arms = {
        "old_chart_explicit_user": (old, case["old_user"]),
        "new_reset_then_reuse_emulated": (new, case["old_user"]),
        "new_reuse_old_defaults_emulated": (new, deep_merge(old_default, case["old_user"])),
        "new_manually_migrated": (new, case["migrated_user"]),
    }
    version = subprocess.run([str(promtool), "--version"], capture_output=True,
                             text=True, check=True).stdout.strip()
    output_dir = root/"results"/"prometheus_configs"
    output_dir.mkdir(parents=True, exist_ok=True)
    records = {"promtool_version": version, "validation_mode": "--syntax-only",
               "new_chart_appVersion": "v3.8.1",
               "limitation": "no Kubernetes cluster, network scrape, or live process",
               "configurations": []}
    for name, (chart, user) in arms.items():
        result = render(helm, chart, user)
        if not result["ok"]:
            raise RuntimeError(f"{name} Helm error: {result['error']}")
        cm = find_resource(result["documents"], kind="ConfigMap", data_key="prometheus.yml")
        if not cm:
            raise RuntimeError(f"{name}: generated ConfigMap lacks prometheus.yml")
        content = cm["data"]["prometheus.yml"]
        config = yaml.safe_load(content)
        jobs = [j["job_name"] for j in config.get("scrape_configs", [])]
        outfile = output_dir/(name+".yml")
        outfile.write_text(content)
        parsed = subprocess.run(
            [str(promtool), "check", "config", "--syntax-only", str(outfile)],
            capture_output=True, text=True, timeout=30,
        )
        data = {
            "arm": name, "chart": chart.name, "render_success": True,
            "promtool_exit_code": parsed.returncode,
            "promtool_stdout": parsed.stdout[-1600:],
            "promtool_stderr": parsed.stderr[-1600:],
            "config_path": str(outfile.relative_to(root)),
            "config_sha256": hashlib.sha256(content.encode()).hexdigest(),
            "job_count": len(jobs), "job_names": jobs,
            "custom_job_present": "n02-contract" in jobs,
            "extra_jobs": sorted(set(jobs)-{"n02-contract"}),
        }
        records["configurations"].append(data)
        print(f"{name}: parser_exit={parsed.returncode}, jobs={len(jobs)}, "
              f"extra={len(data['extra_jobs'])}", flush=True)
    (root/"results"/"promtool_parser_audit.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2)
    )
    # Do not claim success just because templates rendered.  The actual app
    # parser must accept the YAML, and both contrasts must expose the drift.
    arms_by_name = {x["arm"]: x for x in records["configurations"]}
    assert all(x["promtool_exit_code"]==0 for x in records["configurations"])
    assert arms_by_name["old_chart_explicit_user"]["job_count"]==1
    assert arms_by_name["new_reset_then_reuse_emulated"]["job_count"] > 1
    assert arms_by_name["new_manually_migrated"]["job_count"]==1
    print("PASS: real Prometheus parser accepted all four configs; "
          "new reset-then-reuse silently added scrape jobs.", flush=True)


if __name__ == "__main__":
    main()
