#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${G1_INTERFACE:-}" ]]; then
    echo "Usage: G1_INTERFACE=<host-network-interface> $0" >&2
    echo "Example: G1_INTERFACE=eno2 $0" >&2
    exit 2
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

# Permit the container to display RViz/Qt on the host X server.
if command -v xhost >/dev/null 2>&1 && [[ -n "${DISPLAY:-}" ]]; then
    xhost +local:docker
fi

docker run \
    --interactive --tty --rm \
    --name g1pilot-dev \
    --env DISPLAY="${DISPLAY:-:0}" \
    --env QT_X11_NO_MITSHM=0 \
    --env ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-1}" \
    --env RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
    --env G1_INTERFACE \
    --network host \
    --privileged \
    --device-cgroup-rule='c 81:* rmw' \
    --volume /dev:/dev \
    --volume /tmp/.X11-unix:/tmp/.X11-unix:rw \
    --volume "${PROJECT_DIR}:/ros2_ws/src/g1pilot" \
    --volume "${PROJECT_DIR}/config/livox_mid.json:/ros2_ws/src/livox_ros_driver2/config/MID360_config.json" \
    --volume "${SCRIPT_DIR}/setup_uri.sh:/ros2_ws/setup_uri.sh:ro" \
    --volume "${SCRIPT_DIR}/cbuild:/ros2_ws/cbuild:ro" \
    --workdir /ros2_ws \
    --group-add video \
    --entrypoint /bin/bash \
    g1pilot:latest
