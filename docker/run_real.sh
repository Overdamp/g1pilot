#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# Ethernet port wired to the G1. Override with: G1_INTERFACE=<iface> ./run_real.sh
export G1_INTERFACE="${G1_INTERFACE:-enp43s0}"

# The Livox MID-360 config (config/livox_mid.json) sends data to this host IP.
HOST_IP=192.168.123.123
ROBOT_IP=192.168.123.161

# Keep ROS 2 off domain 0; the Unitree SDK uses domain 0 to talk to the robot.
if [[ "${ROS_DOMAIN_ID:-1}" == "0" ]]; then
    echo "ROS_DOMAIN_ID=0 clashes with the Unitree SDK's domain 0; using 1 instead." >&2
    ROS_DOMAIN_ID=1
fi
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-1}"

if ! ip link show "${G1_INTERFACE}" >/dev/null 2>&1; then
    echo "Interface '${G1_INTERFACE}' not found. Available interfaces:" >&2
    ip -br link >&2
    exit 1
fi

if ! ip -br link show "${G1_INTERFACE}" | grep -q 'UP'; then
    echo "WARNING: ${G1_INTERFACE} is down. Is the Ethernet cable plugged into the robot?" >&2
fi

if ! ip -4 addr show "${G1_INTERFACE}" | grep -q "inet ${HOST_IP}/"; then
    echo "WARNING: ${G1_INTERFACE} has no ${HOST_IP}/24 (needed by the robot and Livox). Set it with:" >&2
    echo "  sudo ip addr add ${HOST_IP}/24 dev ${G1_INTERFACE} && sudo ip link set ${G1_INTERFACE} up" >&2
elif ping -c 1 -W 1 "${ROBOT_IP}" >/dev/null 2>&1; then
    echo "Robot reachable at ${ROBOT_IP} via ${G1_INTERFACE}." >&2
else
    echo "WARNING: robot ${ROBOT_IP} does not answer ping. Is the G1 powered on?" >&2
fi

exec "${SCRIPT_DIR}/run.sh"
