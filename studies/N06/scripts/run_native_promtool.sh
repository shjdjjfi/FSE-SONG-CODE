#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../promtool"
if ! command -v promtool >/dev/null 2>&1; then
  echo 'ERROR: Native Prometheus promtool not installed. No engine test was run.' >&2
  exit 2
fi
promtool --version
promtool check rules alert_rules.yml
promtool test rules tests.yml
promtool test rules generated_owner_cases.yml
