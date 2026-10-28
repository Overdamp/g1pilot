#!/usr/bin/env python3
"""Compact terminal view of one robot_state topic, for joint validation.

Run inside the g1pilot container (after sourcing the workspace):
  python3 validate_viewer.py joints   # /joint_states
  python3 validate_viewer.py motors   # /g1pilot/motor_state
  python3 validate_viewer.py imu      # /g1pilot/imu

Read-only: it only subscribes. validate_byobu.sh opens all three side by side.
"""

import math
import sys
import time

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from astroviz_interfaces.msg import MotorStateList
from sensor_msgs.msg import Imu, JointState

MOVING_RAD_S = 0.2  # highlight joints moved by hand
REFRESH_S = 0.2


def short(name: str) -> str:
    return name.removesuffix("_joint")


class Viewer(Node):
    def __init__(self, mode: str):
        super().__init__(f"validate_viewer_{mode}")
        self.mode = mode
        self.msg = None
        self.stamps = []
        self.first_q = {}
        self.q_min = {}
        self.q_max = {}
        topic, msg_type = {
            "joints": ("/joint_states", JointState),
            "motors": ("/g1pilot/motor_state", MotorStateList),
            "imu": ("/g1pilot/imu", Imu),
        }[mode]
        self.topic = topic
        # Sensor-data QoS (best effort) also receives from reliable publishers.
        self.create_subscription(msg_type, topic, self.on_msg, qos_profile_sensor_data)
        self.create_timer(REFRESH_S, self.draw)

    def on_msg(self, msg):
        now = time.monotonic()
        self.stamps.append(now)
        while self.stamps and now - self.stamps[0] > 1.0:
            self.stamps.pop(0)
        self.msg = msg
        if self.mode == "joints":
            pairs = zip(msg.name, msg.position)
        elif self.mode == "motors":
            pairs = ((m.name, m.position) for m in msg.motor_list)
        else:
            return
        for name, q in pairs:
            self.first_q.setdefault(name, q)
            self.q_min[name] = min(self.q_min.get(name, q), q)
            self.q_max[name] = max(self.q_max.get(name, q), q)

    def header(self) -> list[str]:
        since = None if not self.stamps else time.monotonic() - self.stamps[-1]
        stale = "  STALE" if since is not None and since > 0.5 else ""
        return [f"{self.topic}  {len(self.stamps)} Hz{stale}", ""]

    def draw(self):
        lines = self.header()
        if self.msg is None:
            lines.append("waiting for messages ...")
        elif self.mode == "joints":
            lines += self.draw_joints()
        elif self.mode == "motors":
            lines += self.draw_motors()
        else:
            lines += self.draw_imu()
        sys.stdout.write("\x1b[H\x1b[2J" + "\n".join(lines) + "\n")
        sys.stdout.flush()

    def draw_joints(self) -> list[str]:
        out = [f"{'joint':<22}{'q rad':>8}{'deg':>8}{'Δ start':>9}{'min':>8}{'max':>8}"]
        for name, q in zip(self.msg.name, self.msg.position):
            d = q - self.first_q[name]
            out.append(
                f"{short(name):<22}{q:8.3f}{math.degrees(q):8.1f}{d:9.3f}"
                f"{self.q_min[name]:8.3f}{self.q_max[name]:8.3f}"
            )
        return out

    def draw_motors(self) -> list[str]:
        out = [f"{'motor':<22}{'q':>8}{'dq':>8}{'temp':>6}{'volt':>7}  flag"]
        for m in self.msg.motor_list:
            flag = "<< moving" if abs(m.velocity) > MOVING_RAD_S else ""
            out.append(
                f"{short(m.name):<22}{m.position:8.3f}{m.velocity:8.3f}"
                f"{m.temperature:6.0f}{m.voltage:7.1f}  {flag}"
            )
        temps = [m.temperature for m in self.msg.motor_list]
        if temps:
            out.append("")
            out.append(f"temp max {max(temps):.0f}  min {min(temps):.0f}")
        return out

    def draw_imu(self) -> list[str]:
        o = self.msg.orientation
        w, x, y, z = o.w, o.x, o.y, o.z
        roll = math.atan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y))
        pitch = math.asin(max(-1.0, min(1.0, 2 * (w * y - z * x))))
        yaw = math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))
        # World gravity (0, 0, -1) in the body frame, same as the policy obs.
        g = (2 * (w * y - x * z), -2 * (w * x + y * z), -(w * w - x * x - y * y + z * z))
        av, la = self.msg.angular_velocity, self.msg.linear_acceleration
        return [
            f"rpy deg      {math.degrees(roll):8.2f} {math.degrees(pitch):8.2f} {math.degrees(yaw):8.2f}",
            f"gyro rad/s   {av.x:8.3f} {av.y:8.3f} {av.z:8.3f}",
            f"acc m/s^2    {la.x:8.3f} {la.y:8.3f} {la.z:8.3f}",
            f"proj gravity {g[0]:8.3f} {g[1]:8.3f} {g[2]:8.3f}   (upright ≈ 0 0 -1)",
            f"quat wxyz    {w:8.4f} {x:8.4f} {y:8.4f} {z:8.4f}",
        ]


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode not in ("joints", "motors", "imu"):
        print(__doc__)
        sys.exit(2)
    rclpy.init()
    node = Viewer(mode)
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    except Exception:
        # A signal can shut the context down mid-spin; only re-raise real errors.
        if rclpy.ok():
            raise
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
