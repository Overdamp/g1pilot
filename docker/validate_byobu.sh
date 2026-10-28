#!/usr/bin/env bash
# Byobu dashboard for G1 joint validation. Run on the host while the
# g1pilot-dev container (run_real.sh) and robot_state_23dof are running.
#
#   ┌────────────────────┬────────────────────┐
#   │ /joint_states      │ /g1pilot/motor_state│
#   ├────────────────────┼────────────────────┤
#   │ /g1pilot/imu       │ shell (notes, bag) │
#   └────────────────────┴────────────────────┘
#
# Usage: ./validate_byobu.sh            (attach with: byobu attach -t g1val)
#        CONTAINER=name SESSION=name ./validate_byobu.sh
set -euo pipefail

CONTAINER="${CONTAINER:-g1pilot-dev}"
SESSION="${SESSION:-g1val}"
VIEWER=/ros2_ws/src/g1pilot/docker/validate_viewer.py

if ! docker ps --format '{{.Names}}' | grep -qx "${CONTAINER}"; then
    echo "Container '${CONTAINER}' is not running. Start it with ./run_real.sh first." >&2
    exit 1
fi

if byobu has-session -t "${SESSION}" 2>/dev/null; then
    exec byobu attach -t "${SESSION}"
fi

# Source ROS, the workspace and the CycloneDDS interface inside the container.
ros_env='cd /ros2_ws && source setup_uri.sh "${G1_INTERFACE:-lo}" >/dev/null'
in_container() {
    echo "docker exec -it ${CONTAINER} bash -c '${ros_env} && $1'"
}

byobu new-session -d -s "${SESSION}" -n validate "$(in_container "python3 ${VIEWER} joints")"
byobu split-window -h -t "${SESSION}:validate" "$(in_container "python3 ${VIEWER} motors")"
byobu select-pane -t "${SESSION}:validate.0"
byobu split-window -v -l 9 -t "${SESSION}:validate.0" "$(in_container "python3 ${VIEWER} imu")"
byobu select-pane -t "${SESSION}:validate.2"
byobu split-window -v -l 9 -t "${SESSION}:validate.2" "$(in_container "exec bash")"

exec byobu attach -t "${SESSION}"
