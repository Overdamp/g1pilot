#!/usr/bin/env python3
import select
import sys
import termios
import time
import tty

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
from std_msgs.msg import Bool

# Mimics the Joy layout of the PS4 "Wireless Controller" as published by the
# joystick node, so joy_mux and loco_client work unchanged.
NUM_AXES = 8
NUM_BUTTONS = 13
AXIS_LX, AXIS_LY, AXIS_YAW, AXIS_DPAD_Y = 0, 1, 2, 7
BTN_L1, BTN_R2 = 4, 7

# Keys and speeds match unitree_rl_mjlab's g1_ctrl at speed 1.0 (w 0.4 m/s,
# s 0.3 m/s, a/d 0.2 m/s, q/e 0.3 rad/s). loco_client scales axes by -0.5,
# so each value here is -2x the velocity. For safety the scale defaults to
# half of that and is capped at 1.0, never reaching loco_client's 0.5 m/s.
SPEED_MIN, SPEED_MAX = 0.2, 1.0
MOVE_KEYS = {
    'w': (AXIS_LY, -0.8),
    's': (AXIS_LY, 0.6),
    'a': (AXIS_LX, -0.4),
    'd': (AXIS_LX, 0.4),
    'q': (AXIS_YAW, -0.6),
    'e': (AXIS_YAW, 0.6),
}

HELP = """
G1 keyboard teleop  (publishes Joy on {topic})
---------------------------------------------
Same keys as g1_ctrl:
  w / s : forward / backward      u : standby (FSM 4, clears E-stop)
  a / d : strafe left / right     v : stand up, balance and start walking
  q / e : turn left / right       x / space : stop moving
  + / - : speed up / down         p : EMERGENCY STOP (damp motors)
  Ctrl-C: quit

Unlike g1_ctrl, hold a movement key: the robot stops {timeout:.1f} s after it is released.
Start order: u -> v -> w/a/s/d/q/e
"""


class KeyboardTeleop(Node):
    def __init__(self):
        super().__init__('keyboard_teleop')

        self.declare_parameter('topic', '/g1pilot/joy_manual')
        self.declare_parameter('publish_rate', 50.0)
        self.declare_parameter('speed', 0.5)
        self.declare_parameter('key_timeout', 0.7)

        self.topic = self.get_parameter('topic').value
        self.rate = float(self.get_parameter('publish_rate').value)
        self.speed = min(SPEED_MAX, max(SPEED_MIN, float(self.get_parameter('speed').value)))
        self.key_timeout = float(self.get_parameter('key_timeout').value)

        self.publisher = self.create_publisher(Joy, self.topic, 10)
        self.estop_pub = self.create_publisher(Bool, '/g1pilot/emergency_stop', 10)

        self.last_move_key = None
        self.t_last_move_key = 0.0
        # Buttons and the D-pad are held for a few ticks so loco_client sees an edge.
        self.pulse_ticks = max(2, int(0.1 * self.rate))
        self.button_pulses = {}
        self.dpad_up_ticks = 0

        self.create_timer(1.0 / self.rate, self.publish_joy)
        self.log_speed()

    def set_speed(self, speed):
        self.speed = min(SPEED_MAX, max(SPEED_MIN, round(speed, 2)))
        self.log_speed()

    def log_speed(self):
        self.get_logger().info(
            f'Speed {self.speed:.1f}x: w {0.4 * self.speed:.2f} m/s, '
            f'a/d {0.2 * self.speed:.2f} m/s, q/e {0.3 * self.speed:.2f} rad/s')

    def handle_key(self, key):
        if key in MOVE_KEYS:
            self.last_move_key = key
            self.t_last_move_key = time.time()
        elif key in (' ', 'x'):
            self.last_move_key = None
        elif key == 'u':
            self.last_move_key = None
            self.dpad_up_ticks = self.pulse_ticks
            self.get_logger().info('Standby (FSM 4)')
        elif key == 'v':
            self.button_pulses[BTN_L1] = self.pulse_ticks
            self.get_logger().info('Stand up and balance')
        elif key == 'p':
            self.last_move_key = None
            self.estop_pub.publish(Bool(data=True))
            self.get_logger().warn('EMERGENCY STOP sent. Press u to recover.')
        elif key in ('+', '='):
            self.set_speed(self.speed + 0.1)
        elif key in ('-', '_'):
            self.set_speed(self.speed - 0.1)

    def publish_joy(self):
        axes = [0.0] * NUM_AXES
        buttons = [0] * NUM_BUTTONS

        if self.last_move_key and time.time() - self.t_last_move_key > self.key_timeout:
            self.last_move_key = None
        if self.last_move_key:
            axis, value = MOVE_KEYS[self.last_move_key]
            axes[axis] = value * self.speed
            buttons[BTN_R2] = 1

        for idx in list(self.button_pulses):
            buttons[idx] = 1
            self.button_pulses[idx] -= 1
            if self.button_pulses[idx] <= 0:
                del self.button_pulses[idx]

        if self.dpad_up_ticks > 0:
            axes[AXIS_DPAD_Y] = -1.0
            self.dpad_up_ticks -= 1

        msg = Joy()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.axes = axes
        msg.buttons = buttons
        self.publisher.publish(msg)


def main(args=None):
    if not sys.stdin.isatty():
        print('keyboard_teleop needs an interactive terminal: use "ros2 run", not a launch file.',
              file=sys.stderr)
        return

    rclpy.init(args=args)
    node = KeyboardTeleop()
    print(HELP.format(topic=node.topic, timeout=node.key_timeout))

    old_attrs = termios.tcgetattr(sys.stdin)
    try:
        tty.setcbreak(sys.stdin.fileno())
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.0)
            ready, _, _ = select.select([sys.stdin], [], [], 1.0 / node.rate)
            if ready:
                key = sys.stdin.read(1).lower()
                if key == '\x03':
                    break
                node.handle_key(key)
    except KeyboardInterrupt:
        pass
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_attrs)
        # Leave the robot with no movement command.
        node.last_move_key = None
        node.publish_joy()
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
