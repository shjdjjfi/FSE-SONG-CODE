#!/usr/bin/env python3
"""Real Helm lint on every pinned upstream chart + a known render-error control."""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import yaml

from run_study import render

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    cases = yaml.safe_load((ROOT/"cases.yaml").read_text())
    helm = ROOT/"toolchain/linux-amd64/helm"
    results = []
    for family, pair in cases["families"].items():
        for stage, basename in (("old",pair["from"]),("new",pair["to"])):
            path = ROOT/"charts"/basename
            process = subprocess.run(
                [str(helm), "lint", str(path), "--with-subcharts"],
                capture_output=True,text=True,timeout=60,
            )
            row={
                "family":family, "stage":stage, "filename":basename,
                "success":process.returncode==0,"exit_code":process.returncode,
                "stdout_tail":process.stdout[-1800:],"stderr_tail":process.stderr[-1800:],
            }
            print(f"lint {family}/{stage}: exit={process.returncode}",flush=True)
            results.append(row)
    # The upstream cert-manager issue #7352 has an explicit null scenario
    # that fails at template evaluation; it is a NON-SILENT negative control.
    # Null can represent a prior release's missing config but is not proof
    # that such release state existed for our constructed chart pair.
    null_case = render(helm,ROOT/"charts/cert-manager-v1.16.0.tgz",
                       {"webhook":{"config":None}})
    data={
        "helm_chart_lint":results,
        "known_hard_failure_control":{
            "source":"https://github.com/cert-manager/cert-manager/issues/7352",
            "intervention":"explicit webhook.config=null on v1.16.0",
            "result":{k:v for k,v in null_case.items() if k!="documents"},
            "is_silent": False,
            "label":"render error, not a runnable application-regression witness",
        },
    }
    (ROOT/"results/lint_and_known_failure.json").write_text(
        json.dumps(data,indent=2,ensure_ascii=False)
    )
    print("cert-manager explicit-null control: "
          f"render_ok={null_case['ok']}, error={null_case.get('error','')[-190:]}",flush=True)
    print(f"LINT COMPLETE: {sum(x['success'] for x in results)}/{len(results)}",flush=True)


if __name__=="__main__":
    main()
