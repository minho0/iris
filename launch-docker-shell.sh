#!/usr/bin/env bash
set -euo pipefail

mkdir -p "$HOME/temp_cyclone"

set +e
docker run -it --rm \
  --runtime nvidia \
  --network host \
  --ipc=host \
  -e ROS_DOMAIN_ID=101 \
  -e ROS_LOCALHOST_ONLY=0 \
  -e RMW_IMPLEMENTATION=rmw_fastrtps_cpp \
  -e RMW_FASTRTPS_PUBLICATION_MODE=SYNCHRONOUS \
  -v "$HOME/temp_cyclone:/root/temp_cyclone" \
  -v "$HOME/ui_ws:/root/ui_ws" \
  -w /root/ui_ws/iris \
  --name ui \
  alsgh000118/robot_front_ui:latest \
  /bin/bash
status=$?
set -e

echo
echo "[launcher] docker exited with status $status"
read -r -p "Press Enter to close..." _
exit "$status"
