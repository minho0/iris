#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# IRIS — production launcher
#
# Designed to run on the Jetson Thor at boot. Starts all backend
# services, serves the pre-built frontend, then launches Chromium
# on the robot touchscreen.
#
# Prerequisites (once):
#   sudo apt install ros-jazzy-rosbridge-suite ros-jazzy-web-video-server chromium-browser
#   npm install && npm run build
#   cd backend && pip install -r requirements.txt
#
# Install as a systemd service:
#   See systemd/iris.service
# ─────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"
SCREEN_QUERY="${SCREEN_QUERY:-landing}"
FRONTEND_URL="${IRIS_URL:-http://localhost:4173/?screen=$SCREEN_QUERY}"

# Which display to open Chromium on (primary touchscreen)
export DISPLAY="${DISPLAY:-:0}"

# Source ROS 2 + workspace
set +u
if [ -f /opt/ros/jazzy/setup.bash ]; then
    source /opt/ros/jazzy/setup.bash
fi
if [ -f "$HOME/ros2_ws/install/setup.bash" ]; then
    source "$HOME/ros2_ws/install/setup.bash"
fi
if [ -f "$HOME/inha_ws/install/setup.bash" ]; then
    source "$HOME/inha_ws/install/setup.bash"
fi
set -u

PIDS=()

cleanup() {
    echo "[run] shutting down..."
    for pid in "${PIDS[@]}"; do
        kill -SIGINT "$pid" 2>/dev/null || true
    done
    sleep 3
    for pid in "${PIDS[@]}"; do
        kill -SIGKILL "$pid" 2>/dev/null || true
    done
}
trap cleanup EXIT INT TERM

# ── 1. rosbridge ─────────────────────────────────────────────
ros2 launch rosbridge_server rosbridge_websocket_launch.xml \
    > "$LOG_DIR/rosbridge.log" 2>&1 &
PIDS+=($!)

# ── 2. web_video_server ──────────────────────────────────────
ros2 run web_video_server web_video_server \
    --ros-args -p port:=8080 \
    > "$LOG_DIR/web_video_server.log" 2>&1 &
PIDS+=($!)

# ── 3. FastAPI backend ───────────────────────────────────────
(cd backend && uvicorn main:app --host 0.0.0.0 --port 8000) \
    > "$LOG_DIR/backend.log" 2>&1 &
PIDS+=($!)

# ── 4. Static frontend (SvelteKit build output) ──────────────
# `npm run preview` serves `build/` on :4173 — small and fast.
if [ ! -d "build" ]; then
    echo "[run] build/ not found, running `npm run build` first..."
    npm run build
fi
npm run preview > "$LOG_DIR/frontend.log" 2>&1 &
PIDS+=($!)

# Wait for the frontend to come up before opening the browser
echo "[run] waiting for frontend..."
for _ in $(seq 1 30); do
    if curl -sf "$FRONTEND_URL" > /dev/null; then
        break
    fi
    sleep 0.5
done

# ── 5. Chromium ──────────────────────────────────────────────
# Flags tuned for a touchscreen window:
#   --noerrdialogs     suppress error popups
#   --touch-events     force touchscreen input handling
#   --disable-pinch    no accidental zoom from multi-touch
#   --disable-gpu      avoid Jetson Chromium EGL init failures
#   --overscroll-*     no "swipe back" navigation
#   --disable-features=Translate,TouchpadOverscrollHistoryNavigation
#   --autoplay-policy=no-user-gesture-required  for video streams
CHROME_DIR="$SCRIPT_DIR/.chrome-profile"
mkdir -p "$CHROME_DIR"

chromium-browser \
    --user-data-dir="$CHROME_DIR" \
    --noerrdialogs \
    --disable-infobars \
    --disable-session-crashed-bubble \
    --touch-events=enabled \
    --disable-pinch \
    --disable-features=Translate,TouchpadOverscrollHistoryNavigation \
    --disable-gpu \
    --overscroll-history-navigation=0 \
    --autoplay-policy=no-user-gesture-required \
    --check-for-update-interval=31536000 \
    --window-size=1280,720 \
    --window-position=40,40 \
    --app="$FRONTEND_URL" \
    > "$LOG_DIR/chromium.log" 2>&1 &
PIDS+=($!)

echo ""
echo "──────────────────────────────────────────"
echo "  IRIS — running"
echo "  Logs: $LOG_DIR"
echo "──────────────────────────────────────────"

wait -n
