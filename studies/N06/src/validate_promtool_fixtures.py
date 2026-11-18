"""Static cross-check of promtool YAML with a restricted reference evaluator.

It does NOT run PromQL, check `keep_firing_for`, or substitute for promtool.
Use the actual Prometheus binary to obtain native-engine evidence.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

import yaml

from simulator import PendingFor

ROOT = Path(__file__).resolve().parent.parent
_RE_SERIES = re.compile(r'^up\{([^}]+)\}$')
_RE_LABEL = re.compile(r'(\w+)="([^"]*)"')
_RE_TOKEN = re.compile(r'^([01_])(?:x(\d+))?$')


def parse_series(statement: dict) -> tuple[dict[str, str], list[str]]:
    found = _RE_SERIES.fullmatch(statement["series"])
    if not found:
        raise ValueError("This checker only accepts the exact up{...} fixture subset")
    labels = dict(_RE_LABEL.findall(found.group(1)))
    values: list[str] = []
    for token in statement["values"].split():
        match = _RE_TOKEN.fullmatch(token)
        if not match:
            raise ValueError(f"bad value token: {token}")
        values.extend([match.group(1)] * (1 + int(match.group(2) or 0)))
    return labels, values


def check() -> dict:
    file = ROOT / "promtool" / "tests.yml"
    cases = yaml.safe_load(file.read_text(encoding="utf-8"))
    alerts = yaml.safe_load((ROOT / "promtool" / "alert_rules.yml").read_text(encoding="utf-8"))
    assert cases["evaluation_interval"] == "1m"
    assert len(alerts["groups"][0]["rules"]) == 4
    verified = []
    for test in cases["tests"]:
        series = [parse_series(s) for s in test["input_series"]]
        checks = test["alert_rule_test"]
        max_min = max(int(c["eval_time"].removesuffix("m")) for c in checks)
        state = {k: PendingFor(10) for k in
                 ("N06InstanceDown", "N06ServiceDown", "N06InstanceWithKeepFiring")}
        states_at_time: dict[int, dict[str, list[dict[str, str]]]] = {}
        for t in range(max_min + 1):
            source = [(labels, values[t]) for labels, values in series if t < len(values) and values[t] != "_"]
            bad_instances: set[str] = set()
            instance_labels: dict[str, dict[str, str]] = {}
            ratios: dict[tuple[str, str], tuple[int, int]] = {}
            for labels, val in source:
                if labels["job"] == "n06":
                    key = (labels["namespace"], labels["service"])
                    count_bad, count_total = ratios.get(key, (0, 0))
                    ratios[key] = (count_bad + int(val == "0"), count_total + 1)
                if val == "0":
                    fingerprint = "|".join(f"{key}={value}" for key, value in sorted(labels.items()))
                    instance_labels[fingerprint] = {**labels, "severity": "test"}
                    if labels["job"] == "n06":
                        bad_instances.add(fingerprint)
            service_active = {f"{ns}|{service}" for (ns, service), (bad, total) in ratios.items()
                              if bad / total > 0.1}
            firing_instances = state["N06InstanceDown"].step(t, bad_instances)
            firing_service = state["N06ServiceDown"].step(t, service_active)
            keep_active = {key for key in instance_labels if instance_labels[key]["job"] == "n06-keep"}
            firing_keep = state["N06InstanceWithKeepFiring"].step(t, keep_active)
            states_at_time[t] = {
                "N06InstanceDown": [instance_labels[k] for k in sorted(firing_instances)],
                "N06ServiceDown": [dict(namespace=k.split("|")[0], service=k.split("|")[1],
                                        severity="test") for k in sorted(firing_service)],
                "N06InstanceWithKeepFiring": [instance_labels[k] for k in sorted(firing_keep)],
            }
        for check in checks:
            minute = int(check["eval_time"].removesuffix("m"))
            actual = states_at_time[minute][check["alertname"]]
            expected = [item["exp_labels"] for item in check["exp_alerts"]]
            if actual != expected:
                raise AssertionError(f"{test['name']} @ {minute}m expected {expected}, got {actual}")
            verified.append({"case": test["name"], "alert": check["alertname"],
                             "eval_minute": minute, "expected_firing": len(expected),
                             "restricted_model_match": True})
    result = {
        "result": "PASS_RESTRICTED_REFERENCE_ONLY",
        "promtool_executed": False,
        "promql_executed": False,
        "tests": len(cases["tests"]),
        "assertions": len(verified),
        "cases": verified,
    }
    target = ROOT / "results_v2" / "restricted_fixture_validation.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    try:
        print(json.dumps(check(), indent=2))
    except (AssertionError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise
