#!/usr/bin/env bash
# Reproduce the pinned external executables. Charts are already included
# with this experiment archive; the heavyweight tool binaries are not.
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
target_dir="$project_dir/toolchain"
mkdir -p "$target_dir"

helm_tgz="$target_dir/helm-v3.17.0-linux-amd64.tar.gz"
if [ ! -x "$target_dir/linux-amd64/helm" ]; then
  curl -fL --retry 3 --connect-timeout 20 \
    https://get.helm.sh/helm-v3.17.0-linux-amd64.tar.gz -o "$helm_tgz"
  tar -xzf "$helm_tgz" -C "$target_dir" linux-amd64/helm
fi
"$target_dir/linux-amd64/helm" version --short

if [ "${1:-}" = "--with-prometheus" ]; then
  prom_tgz="$target_dir/prometheus-3.8.1.linux-amd64.tar.gz"
  if [ ! -x "$target_dir/prometheus-3.8.1.linux-amd64/promtool" ] || \
     [ ! -x "$target_dir/prometheus-3.8.1.linux-amd64/prometheus" ]; then
    curl -fL --retry 3 --connect-timeout 30 \
      https://github.com/prometheus/prometheus/releases/download/v3.8.1/prometheus-3.8.1.linux-amd64.tar.gz \
      -o "$prom_tgz"
    tar -xzf "$prom_tgz" -C "$target_dir" \
      prometheus-3.8.1.linux-amd64/promtool \
      prometheus-3.8.1.linux-amd64/prometheus
  fi
  "$target_dir/prometheus-3.8.1.linux-amd64/promtool" --version
fi
