#!/usr/bin/env bash
set -euo pipefail

NVIDIA_IP="${NVIDIA_IP:-192.168.78.10}"
NVIDIA_USER="${NVIDIA_USER:-nvidia}"
REMOTE="${NVIDIA_USER}@${NVIDIA_IP}"
LOCAL_PIDS=()
CLEANED=0

STARTUP_PATTERNS=(
  "bringup_combined.launch.py"
  "rviz_MID360_launch.py"
  "99_teleoperation"
  "joy_node"
  "joy_process_killer.py"
  "gripper_node"
)

CLEANUP_PATTERNS=(
  "bringup_combined.launch.py"
  "rviz_MID360_launch.py"
  "livox_ros_driver2_node"
  "99_teleoperation"
  "rby1_subscriber_pkg/99_teleoperation"
  "joy_node"
  "/lib/joy/joy_node"
  "joy_process_killer.py"
  "gripper_node"
  "gripper_driver/gripper_node"
)

COMMANDS=(
  "ros2 launch rby1_bringup bringup_combined.launch.py cmd_vel_topic:=/cmd_vel"
  "ros2 launch livox_ros_driver2 rviz_MID360_launch.py"
  "ros2 run rby1_subscriber_pkg 99_teleoperation"
  "ros2 run joy joy_node"
  "python3 ~/joy_process_killer.py"
  "ros2 run gripper_driver gripper_node"
)

TAGS=(
  "bringup"
  "livox"
  "teleop"
  "joy"
  "joy_kill"
  "gripper"
)

log() {
  printf '%s\n' "$*"
}

to_safe_pgrep_pattern() {
  local pattern=$1
  local first=${pattern:0:1}
  local rest=${pattern:1}
  printf '[%s]%s' "$first" "$rest"
}

remote_has_pattern() {
  local pattern=$1
  local safe_pattern
  safe_pattern=$(to_safe_pgrep_pattern "$pattern")
  ssh -q -o BatchMode=yes -o ConnectTimeout=2 "$REMOTE" "pgrep -f '$safe_pattern' >/dev/null"
}

verify_remote_patterns() {
  local missing=0
  local pattern

  for pattern in "${STARTUP_PATTERNS[@]}"; do
    if ! remote_has_pattern "$pattern"; then
      log "[verify] missing remote process: $pattern"
      missing=1
    fi
  done

  return "$missing"
}

remote_pgid_kill_verified() {
  local pattern=$1
  local safe_pattern
  safe_pattern=$(to_safe_pgrep_pattern "$pattern")
  ssh -q -o BatchMode=yes -o ConnectTimeout=2 "$REMOTE" "
    set -eu
    PIDS=\$(pgrep -f '$safe_pattern' || true)
    if [ -z \"\$PIDS\" ]; then
      exit 0
    fi
    PGIDS=\$(printf '%s\n' \$PIDS | xargs -r ps -o pgid= | tr -d ' ' | sort -u)

    for pid in \$PIDS; do kill -INT \$pid 2>/dev/null || true; done
    for pgid in \$PGIDS; do kill -INT -\$pgid 2>/dev/null || true; done
    sleep 2
    for pid in \$PIDS; do kill -TERM \$pid 2>/dev/null || true; done
    for pgid in \$PGIDS; do kill -TERM -\$pgid 2>/dev/null || true; done
    sleep 2
    for pid in \$PIDS; do kill -KILL \$pid 2>/dev/null || true; done
    for pgid in \$PGIDS; do kill -KILL -\$pgid 2>/dev/null || true; done
    pkill -f '$safe_pattern' 2>/dev/null || true
    sleep 1

    if pgrep -f '$safe_pattern' >/dev/null; then
      exit 1
    fi
  "
}

cleanup_remote_patterns() {
  local output
  local status

  set +e
  output=$(
    ssh -q -o BatchMode=yes -o ConnectTimeout=2 "$REMOTE" bash -s -- "${CLEANUP_PATTERNS[@]}" <<'EOF'
set -euo pipefail

safe_pattern() {
  local pattern=$1
  local first=${pattern:0:1}
  local rest=${pattern:1}
  printf '[%s]%s' "$first" "$rest"
}

signal_patterns() {
  local sig=$1
  shift
  local pattern safe pids filtered_pids pgids pid pgid self_pid parent_pid
  self_pid=$$
  parent_pid=$PPID

  for pattern in "$@"; do
    safe=$(safe_pattern "$pattern")
    pids=$(pgrep -f "$safe" || true)
    [ -z "$pids" ] && continue
    filtered_pids=$(printf '%s\n' $pids | awk -v self="$self_pid" -v parent="$parent_pid" '$1 != self && $1 != parent')
    [ -z "$filtered_pids" ] && continue
    pgids=$(printf '%s\n' $filtered_pids | xargs -r ps -o pgid= | tr -d ' ' | sort -u || true)

    for pid in $filtered_pids; do
      kill "-$sig" "$pid" 2>/dev/null || true
    done
    for pgid in $pgids; do
      kill "-$sig" -- "-$pgid" 2>/dev/null || true
    done
    pkill "-$sig" -f "$safe" 2>/dev/null || true
  done
}

signal_patterns INT "$@"
sleep 2
signal_patterns TERM "$@"
sleep 2
signal_patterns KILL "$@"
sleep 1

failed=0
for pattern in "$@"; do
  safe=$(safe_pattern "$pattern")
  if pgrep -f "$safe" >/dev/null; then
    echo "$pattern"
    failed=1
  fi
done
exit "$failed"
EOF
  )
  status=$?
  set -e

  if [ "$status" -ne 0 ]; then
    while IFS= read -r pattern; do
      [ -z "$pattern" ] && continue
      log "[cleanup] remote process still alive after kill: $pattern"
    done <<< "$output"
    return 1
  fi

  return 0
}

cleanup() {
  local status=${1:-$?}
  if [ "$CLEANED" = "1" ]; then
    return "$status"
  fi
  CLEANED=1
  trap - EXIT INT TERM

  log ""
  log "🛑 [bringup-daemon] cleanup..."

  for pid in "${LOCAL_PIDS[@]:-}"; do
    kill -TERM "$pid" 2>/dev/null || true
  done

  if ! cleanup_remote_patterns; then
    log "❌ [bringup-daemon] cleanup verification failed"
    exit 1
  fi

  log "✅ [bringup-daemon] cleanup complete"
  exit "$status"
}

trap 'cleanup $?' EXIT INT TERM

start_remote_job() {
  local tag=$1
  local command=$2
  ssh "$REMOTE" "bash -ic '$command'" > >(sed -u "s/^/[$tag]   /") 2>&1 &
  LOCAL_PIDS+=($!)
}

log "🚀 [bringup-daemon] starting remote bringup jobs..."

log "🧹 [bringup-daemon] clearing stale remote bringup jobs..."
cleanup_remote_patterns || true

for index in "${!COMMANDS[@]}"; do
  start_remote_job "${TAGS[$index]}" "${COMMANDS[$index]}"
done

sleep 3
if ! verify_remote_patterns; then
  log "❌ [bringup-daemon] startup verification failed"
  exit 1
fi

log "✅ [bringup-daemon] startup verified"
wait
