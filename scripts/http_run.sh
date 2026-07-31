#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

EXPOSE_PORT=$(awk -F '[ =]+' '/^expose_port/ {gsub(/[^0-9]/, "", $2); print $2; exit}' "$PROJECT_DIR/.preview" 2>/dev/null || echo 5000)
PORT="${DEPLOY_RUN_PORT:-$EXPOSE_PORT}"

export COZE_WORKSPACE_PATH="$PROJECT_DIR"
export COZE_PROJECT_TYPE="workflow"

usage() {
  echo "Usage: $0 -p <port>"
  exit 1
}

while getopts "p:h" opt; do
  case "$opt" in
    p) PORT="$OPTARG" ;;
    h) usage ;;
    *) usage ;;
  esac
done

if [ -f "${PROJECT_DIR}/.venv/bin/activate" ]; then
  source "${PROJECT_DIR}/.venv/bin/activate"
fi

cd "$PROJECT_DIR"
python src/main.py -m http -p "$PORT"
