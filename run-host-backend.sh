#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# IRIS — launcher backend (host-side)
#
# Runs the FastAPI launcher on the HOST, not in Docker, so the
# spawned scripts (e.g. /home/thor/inha_scripts/...) see the host
# filesystem, devices, and privileges.
#
# One-time setup:
#   (이미 ~/.venv 에 설치 완료)
# ─────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/backend"

# VENV 경로를 방금 패키지를 설치한 ui_ws 안의 .venv로 변경합니다.
VENV="$SCRIPT_DIR/.venv"

if [ ! -x "$VENV/bin/uvicorn" ]; then
    echo "[host-backend] venv not found or uvicorn not installed at $VENV"
    echo "  Please run: $VENV/bin/pip install fastapi uvicorn pyyaml"
    exit 1
fi

# Source ROS so spawned scripts inherit ROS env (optional).
if [ -f /opt/ros/jazzy/setup.bash ]; then
    set +u
    source /opt/ros/jazzy/setup.bash
    set -u
fi
if [ -f "$HOME/inha_ws/install/setup.bash" ]; then
    set +u
    source "$HOME/inha_ws/install/setup.bash"
    set -u
fi

UVICORN_ARGS=(main:app --host 0.0.0.0 --port 8000)

# The FastAPI reloader spawns a parent/child process pair that can interact
# badly with shell job control on this kiosk host. Keep reload opt-in.
if [ "${IRIS_BACKEND_RELOAD:-0}" = "1" ]; then
    UVICORN_ARGS+=(--reload)
fi

# This backend doesn't need terminal input once started.
# Keep Ctrl+C / normal terminal control working, but disconnect stdin so
# accidental tty reads from dependencies don't suspend the process.
exec </dev/null

exec "$VENV/bin/uvicorn" "${UVICORN_ARGS[@]}"
