#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# IRIS — host backend + current frontend preview
#
# This is the launcher used by the `iris` alias in ~/.bashrc.
# It runs the host FastAPI backend, rebuilds the current frontend
# workspace, then serves the built UI on :4173.
# ─────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"

PIDS=()
CLEANED=0

resolve_node() {
  if command -v node >/dev/null 2>&1; then
    command -v node
    return 0
  fi

  local candidates=(
    /home/thor/.vscode-server/cli/servers/Stable-*/server/node
    /home/thor/.antigravity-server/bin/*/node
    /home/thor/.cache/ms-playwright-go/*/node
  )

  local path
  for path in "${candidates[@]}"; do
    for resolved in $path; do
      if [ -x "$resolved" ]; then
        printf '%s\n' "$resolved"
        return 0
      fi
    done
  done

  return 1
}

cleanup() {
  if [ "$CLEANED" = "1" ]; then
    return
  fi
  CLEANED=1

  echo
  echo "🛑 [iris] shutting down..."
  for pid in "${PIDS[@]:-}"; do
    kill -TERM "$pid" 2>/dev/null || true
  done

  sleep 1
  for pid in "${PIDS[@]:-}"; do
    kill -KILL "$pid" 2>/dev/null || true
  done

  echo "✅ [iris] all stopped."
  exit 0
}

trap cleanup INT TERM EXIT

NODE_BIN="${NODE_BIN:-$(resolve_node || true)}"
if [ -z "${NODE_BIN:-}" ] || [ ! -x "$NODE_BIN" ]; then
  echo "[iris] could not find a usable node runtime"
  exit 1
fi

VITE_BIN="$SCRIPT_DIR/node_modules/vite/bin/vite.js"
if [ ! -f "$VITE_BIN" ]; then
  echo "[iris] vite not found at $VITE_BIN"
  exit 1
fi

echo "🧹 [iris] stopping stale local IRIS services..."
pkill -f "$SCRIPT_DIR/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000" 2>/dev/null || true
pkill -f "$VITE_BIN preview --host 0.0.0.0 --port 4173 --configLoader runner" 2>/dev/null || true
sleep 1

echo "🔧 [iris] building current frontend..."
"$NODE_BIN" "$VITE_BIN" build --configLoader runner

echo "🚀 [iris] starting backend on :8000"
"$SCRIPT_DIR/run-host-backend.sh" > >(sed -u 's/^/[backend]  /') 2>&1 &
PIDS+=($!)

echo "🚀 [iris] starting frontend preview on :4173"
"$NODE_BIN" "$VITE_BIN" preview --host 0.0.0.0 --port 4173 --configLoader runner \
  > >(sed -u 's/^/[frontend] /') 2>&1 &
PIDS+=($!)

echo "🚀 [iris] backend + frontend launched (PIDs: ${PIDS[*]})"
echo "   📺 http://localhost:4173"
echo "   🌐 http://<robot-ip>:4173"
echo "   Ctrl+C to stop all."

wait -n
echo "⚠  [iris] a service exited unexpectedly — cleaning up the rest"
cleanup
