#!/usr/bin/env bash
set -euo pipefail

N22_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_DIR="${N22_ROOT}/_upstreams"
mkdir -p "${SRC_DIR}"

# Version-lock external source; this script never checks out untrusted input
# into the author's existing workspace or touches a production database.
if [[ ! -d "${SRC_DIR}/open-webui/.git" ]]; then
  git clone --depth 1 --filter=blob:none --sparse --branch v0.9.6 \
    https://github.com/open-webui/open-webui.git "${SRC_DIR}/open-webui"
  git -C "${SRC_DIR}/open-webui" sparse-checkout set backend/open_webui/migrations/versions
fi

if [[ ! -d "${SRC_DIR}/django-demo-app/.git" ]]; then
  git clone --depth 1 https://github.com/PetterS/django-demo-app.git \
    "${SRC_DIR}/django-demo-app"
fi
PETTER_SHA="8c62fd7c54a894d251679ab2b2f27138166380f9"
if [[ "$(git -C "${SRC_DIR}/django-demo-app" rev-parse HEAD)" != "${PETTER_SHA}" ]]; then
  git -C "${SRC_DIR}/django-demo-app" fetch --depth 1 origin "${PETTER_SHA}"
  git -C "${SRC_DIR}/django-demo-app" checkout --detach "${PETTER_SHA}"
fi

mkdir -p "${N22_ROOT}/results"
python "${N22_ROOT}/experiments/openwebui_replay.py" \
  --source "${SRC_DIR}/open-webui/backend/open_webui/migrations/versions/b10670c03dd5_update_user_table.py" \
  --output "${N22_ROOT}/results/openwebui"
python "${N22_ROOT}/experiments/django_replay.py" \
  --petter-source "${SRC_DIR}/django-demo-app" \
  --output "${N22_ROOT}/results/django"
node "${N22_ROOT}/experiments/drizzle_replay.mjs" \
  --output "${N22_ROOT}/results/drizzle"
python "${N22_ROOT}/experiments/evaluate.py" \
  --results "${N22_ROOT}/results" --output "${N22_ROOT}/results"
python "${N22_ROOT}/experiments/performance.py" \
  --output "${N22_ROOT}/results/performance"
python -m pytest "${N22_ROOT}/tests" -q
