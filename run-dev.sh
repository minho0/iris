#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# IRIS — development launcher
#
# Starts the in-container components:
#   1. rosbridge_websocket     :9090
#   2. web_video_server        :18081
#   3. SvelteKit dev server    :1352 by default, or $FRONTEND_PORT
#
# The FastAPI launcher backend (:8000) runs on the HOST via
# ./run-host-backend.sh — it spawns host scripts so it cannot live in
# the container.
#
# All services log to ./logs/ and are killed together on Ctrl+C.
#
# Prerequisites:
#   sudo apt install ros-jazzy-rosbridge-suite ros-jazzy-web-video-server
#   npm install
# ─────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"

FRONTEND_PORT="${FRONTEND_PORT:-1352}"

# Source ROS 2 Jazzy in a clean environment. Sourcing local workspaces here can
# mix DDS/Fast-CDR libraries and break rosbridge.
set +u
unset AMENT_PREFIX_PATH CMAKE_PREFIX_PATH COLCON_PREFIX_PATH
unset LD_LIBRARY_PATH PYTHONPATH
source /opt/ros/jazzy/setup.bash
set -u

PIDS=()

cleanup() {
    echo ""
    echo "[run-dev] shutting down..."
    for pid in "${PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            kill -SIGINT "$pid" 2>/dev/null || true
        fi
    done
    # Give them 3s to exit gracefully
    sleep 3
    for pid in "${PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            kill -SIGKILL "$pid" 2>/dev/null || true
        fi
    done
    echo "[run-dev] bye"
}
trap cleanup EXIT INT TERM

echo "[run-dev] starting rosbridge_websocket on :9090"
ros2 launch rosbridge_server rosbridge_websocket_launch.xml \
    > "$LOG_DIR/rosbridge.log" 2>&1 &
PIDS+=($!)

echo "[run-dev] starting web_video_server on :18081"
ros2 run web_video_server web_video_server \
    --ros-args -p port:=18081 \
    > "$LOG_DIR/web_video_server.log" 2>&1 &
PIDS+=($!)

echo "[run-dev] starting SvelteKit dev server on :$FRONTEND_PORT"
npx vite dev --host 0.0.0.0 --port "$FRONTEND_PORT" > "$LOG_DIR/frontend.log" 2>&1 &
PIDS+=($!)

sleep 2
echo ""
echo "──────────────────────────────────────────"
echo "  IRIS — development"
echo ""
echo "  Frontend:        http://localhost:$FRONTEND_PORT"
echo "  Backend API:     http://localhost:8000  (host-side, run ./run-host-backend.sh)"
echo "  rosbridge WS:    ws://localhost:9090"
echo "  Video streams:   http://localhost:18081"
echo ""
echo "  Logs in: $LOG_DIR"
echo "  Ctrl+C to stop everything"
echo "──────────────────────────────────────────"
echo ""

# Wait for any child to exit, then cleanup kicks in
wait -n
