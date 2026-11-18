#!/usr/bin/env bash
# Rebuild exact native helm-diff baseline without touching the user's Helm profile.
set -euo pipefail

n02_project_root="$(cd "$(dirname "$0")/.." && pwd)"
n02_helm_bin="$n02_project_root/toolchain/linux-amd64/helm"
n02_plugin_dir="$n02_project_root/toolchain/plugins"
test -x "$n02_helm_bin" || {
  echo "Install Helm first: bash scripts/bootstrap_tools.sh" >&2
  exit 2
}
mkdir -p "$n02_plugin_dir"
if [ ! -x "$n02_plugin_dir/helm-diff/bin/diff" ]; then
  HELM_PLUGINS="$n02_plugin_dir" "$n02_helm_bin" plugin install \
    https://github.com/databus23/helm-diff --version v3.12.0
fi
n02_actual_version="$(HELM_PLUGINS="$n02_plugin_dir" "$n02_helm_bin" diff version)"
test "$n02_actual_version" = "3.12.0" || {
  echo "Plugin version drift: expected 3.12.0, got $n02_actual_version" >&2
  exit 3
}
echo "Pinned helm-diff v$n02_actual_version ready"
