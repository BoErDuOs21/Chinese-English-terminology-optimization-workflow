#!/bin/bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

if [ "$COZE_PROJECT_ENV" = "DEV" ]; then
  if [ ! -d "${PROJECT_DIR}/assets" ]; then
    mkdir -p "${PROJECT_DIR}/assets"
  fi
fi

if [ -n "$PIP_TARGET" ]; then
  echo "[setup] Deploy mode (uv): installing to PIP_TARGET=$PIP_TARGET"
  if [ -f "uv.lock" ]; then
    uv export --frozen --no-hashes --no-dev | uv pip install --no-cache --target "$PIP_TARGET" -r -
  else
    uv export --no-hashes --no-dev | uv pip install --no-cache --target "$PIP_TARGET" -r -
  fi
else
  echo "[setup] Devbox mode (uv): installing to .venv"
  if [ -f "uv.lock" ]; then
    uv sync --frozen || uv sync
  else
    uv sync
  fi
  touch .venv/.uv_ready
fi

# ============================================================
# 修复：平台 AI 可能将 project_type 从 "web" 改为 "backend"，
# 导致预览功能被禁用。此处强制改回 "web" 以确保预览可用。
# ============================================================
if [ -f .coze ]; then
  if grep -q 'project_type.*=.*"backend"' .coze 2>/dev/null; then
    echo "[setup] Fixing project_type: backend -> web (required for preview)"
    sed -i 's/project_type[[:space:]]*=[[:space:]]*"backend"/project_type = "web"/' .coze
  fi
  if grep -q 'preview_enable.*=.*"disabled"' .coze 2>/dev/null; then
    echo "[setup] Fixing preview_enable: disabled -> enabled"
    sed -i 's/preview_enable[[:space:]]*=[[:space:]]*"disabled"/preview_enable = "enabled"/' .coze
  fi
fi