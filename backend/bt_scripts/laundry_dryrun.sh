#!/usr/bin/env bash
set +u
set -eo pipefail

source "$HOME/bt_ws/install/setup.bash"
source "$HOME/inha_ws/install/setup.bash"

exec ros2 run inha_bt_pkg bt_node missions/laundry_dryrun.xml
