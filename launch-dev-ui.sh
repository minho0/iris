#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

FRONTEND_PORT="${FRONTEND_PORT:-55173}"
SCREEN_QUERY="${SCREEN_QUERY:-landing}"
URL="${IRIS_URL:-http://localhost:${FRONTEND_PORT}/?screen=${SCREEN_QUERY}}"
LOG_DIR="$SCRIPT_DIR/logs"
CONTAINER_NAME="ui-dev-${USER:-thor}-$$"
CHROME_DIR="$(mktemp -d /tmp/robot-ui-chrome.XXXXXX)"

mkdir -p "$HOME/temp_cyclone" "$LOG_DIR"
export DISPLAY="${DISPLAY:-:0}"

if ! command -v chromium-browser >/dev/null 2>&1; then
  echo "[launcher] chromium-browser not found" >> "$LOG_DIR/desktop-launcher.log"
  exit 1
fi

PIDS=()

cleanup() {
  echo "[launcher] shutting down..."
  pkill -f -- "--user-data-dir=$CHROME_DIR" 2>/dev/null || true

  for pid in "${PIDS[@]}"; do
    if kill -0 "$pid" 2>/dev/null; then
      kill -TERM "$pid" 2>/dev/null || true
    fi
  done

  docker stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

docker run --rm \
  --runtime nvidia \
  --network host \
  --ipc=host \
  -e ROS_DOMAIN_ID=101 \
  -e ROS_LOCALHOST_ONLY=0 \
  -e RMW_IMPLEMENTATION=rmw_fastrtps_cpp \
  -e RMW_FASTRTPS_PUBLICATION_MODE=SYNCHRONOUS \
  -e FRONTEND_PORT="$FRONTEND_PORT" \
  -v "$HOME/temp_cyclone:/root/temp_cyclone" \
  -v "$HOME/ui_ws:/root/ui_ws" \
  -w /root/ui_ws/iris \
  --name "$CONTAINER_NAME" \
  alsgh000118/robot_front_ui:latest \
  /bin/bash -lc './run-dev.sh' \
  > "$LOG_DIR/desktop-dev-container.log" 2>&1 &
DEV_PID=$!
PIDS+=($DEV_PID)

ready=0
for _ in $(seq 1 90); do
  if curl -sf "$URL" >/dev/null; then
    ready=1
    break
  fi

  if ! kill -0 "$DEV_PID" 2>/dev/null; then
    echo "[launcher] dev container exited before frontend was ready" >> "$LOG_DIR/desktop-launcher.log"
    exit 1
  fi

  sleep 1
done

if [ "$ready" -ne 1 ]; then
  echo "[launcher] frontend did not become ready in time" >> "$LOG_DIR/desktop-launcher.log"
  exit 1
fi

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
  --app="$URL" \
  > "$LOG_DIR/chromium-dev.log" 2>&1 &
BROWSER_PID=$!
PIDS+=($BROWSER_PID)

browser_started=0
for _ in $(seq 1 20); do
  if pgrep -f -- "--user-data-dir=$CHROME_DIR" >/dev/null; then
    browser_started=1
    break
  fi

  if ! kill -0 "$BROWSER_PID" 2>/dev/null; then
    break
  fi

  sleep 0.5
done

if [ "$browser_started" -ne 1 ]; then
  echo "[launcher] browser did not stay open" >> "$LOG_DIR/desktop-launcher.log"
  exit 1
fi

while kill -0 "$DEV_PID" 2>/dev/null; do
  if ! pgrep -f -- "--user-data-dir=$CHROME_DIR" >/dev/null; then
    break
  fi
  sleep 1
done
