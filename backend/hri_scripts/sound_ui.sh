#!/usr/bin/env bash

set -Eeuo pipefail

readonly CONTAINER_NAME="mic_whisper"
readonly DISPLAY_VALUE="${DISPLAY:-:0}"
readonly XAUTHORITY_FILE="${XAUTHORITY:-$HOME/.Xauthority}"
readonly XDG_RUNTIME_DIR_VALUE="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
readonly PULSE_SOCKET="${XDG_RUNTIME_DIR_VALUE}/pulse/native"

whisper_pid=""
tts_pid=""

cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM

  if [[ -n "${whisper_pid}" ]]; then
    kill "${whisper_pid}" >/dev/null 2>&1 || true
  fi

  if [[ -n "${tts_pid}" ]]; then
    kill "${tts_pid}" >/dev/null 2>&1 || true
  fi

  wait >/dev/null 2>&1 || true
  docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true
  exit "${exit_code}"
}

trap cleanup EXIT INT TERM

xhost +local:docker >/dev/null 2>&1 || true
docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true

echo "[HRI][sound] starting container"
docker run -d \
  --name "${CONTAINER_NAME}" \
  --rm \
  --runtime nvidia \
  --network host \
  --privileged \
  --device /dev/snd \
  -e "DISPLAY=${DISPLAY_VALUE}" \
  -e QT_X11_NO_MITSHM=1 \
  -e ROS_DOMAIN_ID=101 \
  -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
  -e "PULSE_SERVER=unix:${PULSE_SOCKET}" \
  -v "${PULSE_SOCKET}:${PULSE_SOCKET}" \
  -v "$HOME/.config/pulse/cookie:/root/.config/pulse/cookie" \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v "${XAUTHORITY_FILE}:/root/.Xauthority:rw" \
  -v "$HOME/model_cache:/root/.cache/whisper" \
  -v "$HOME/asoundrc.mic_whisper:/root/.asoundrc:ro" \
  -v "$HOME/temp_cyclone:/root/temp_cyclone" \
  -v "$HOME/mic_ws:/root/mic_ws" \
  -w /root/mic_ws \
  final_whisper_9 \
  tail -f /dev/null >/dev/null

sleep 2

echo "[HRI][sound] starting whisper_node"
docker exec -i "${CONTAINER_NAME}" bash -ic 'ros2 run thor_whisper whisper_node' &
whisper_pid=$!

echo "[HRI][sound] starting tts_node"
docker exec -i "${CONTAINER_NAME}" bash -ic 'ros2 run thor_whisper tts_node' &
tts_pid=$!

wait -n "${whisper_pid}" "${tts_pid}"
exit_code=$?

kill "${whisper_pid}" "${tts_pid}" >/dev/null 2>&1 || true
wait >/dev/null 2>&1 || true

exit "${exit_code}"
