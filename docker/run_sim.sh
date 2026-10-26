#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# The Docker container uses host networking, so its lo interface is the host's
# loopback interface. Keep ROS 2 on domain 1; the Unitree SDK in robot_state
# uses its own CycloneDDS domain 0 to communicate with MuJoCo.
export G1_INTERFACE=lo
if [[ "${ROS_DOMAIN_ID:-1}" == "0" ]]; then
    echo "ROS_DOMAIN_ID=0 clashes with the Unitree SDK's domain 0; using 1 instead." >&2
    ROS_DOMAIN_ID=1
fi
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-1}"

# CycloneDDS only uses multicast discovery on lo if the flag is set when a
# process starts, so the simulator must be (re)started after enabling it.
if ! ip link show lo | grep -q MULTICAST; then
    echo "Enabling multicast on lo (needs sudo)..." >&2
    sudo ip link set lo multicast on
    echo "Multicast was off: restart unitree_mujoco and g1_ctrl before launching g1pilot." >&2
fi

exec "${SCRIPT_DIR}/run.sh"
