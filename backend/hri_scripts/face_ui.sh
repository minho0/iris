#!/usr/bin/env bash

set -Eeuo pipefail

readonly CONTAINER_NAME="face"
readonly DISPLAY_VALUE="${DISPLAY:-:0}"
readonly XAUTHORITY_FILE="${XAUTHORITY:-$HOME/.Xauthority}"

cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM
  docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true
  exit "${exit_code}"
}

trap cleanup EXIT INT TERM

xhost +local:docker >/dev/null 2>&1 || true
docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true

echo "[HRI][face] starting container"
docker run -d \
  --name "${CONTAINER_NAME}" \
  --rm \
  --net=host \
  --gpus all \
  --ipc=host \
  --ulimit memlock=-1 \
  --ulimit stack=67108864 \
  -v "$HOME/face_ws:/root/face_ws" \
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
  -v "${XAUTHORITY_FILE}:/root/.Xauthority:rw" \
  -v "$HOME/temp_cyclone:/root/temp_cyclone" \
  -e "DISPLAY=${DISPLAY_VALUE}" \
  -e XAUTHORITY=/root/.Xauthority \
  -e ROS_DOMAIN_ID=101 \
  -e QT_X11_NO_MITSHM=1 \
  -w /root/face_ws \
  inha/face \
  tail -f /dev/null >/dev/null

sleep 1

echo "[HRI][face] starting face_node"
docker exec -i "${CONTAINER_NAME}" bash -ic 'ros2 run face_landmark face_node'
