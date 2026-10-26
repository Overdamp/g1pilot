# G1Pilot

[![License](https://img.shields.io/badge/License-BSD%203--Clause-blue.svg)](
https://opensource.org/licenses/BSD-3-Clause)
[![Ros Version](https://img.shields.io/badge/ROS2-Jazzy-green)](
https://docs.ros.org/en/jazzy/index.html)
[![GitHub Stars](https://img.shields.io/github/stars/Hucebot/g1pilot?style=social)](https://github.com/Hucebot/g1pilot/stargazers)

<img src="https://github.com/hucebot/g1pilot/blob/main/images/g1pilot.png" alt="G1Pilot" width="800" height="500">

G1Pilot is an open‑source ROS 2 package for Unitree G1 humanoid robots. Basically is made to leave the robot lower body to the controller of unitree while providing all necessary tools to control the upper body and teleoperate the robot. It exposes two complementary control Joint (low‑level, per‑joint) and Cartesian (end‑effector) and continuously publishes core robot state for monitoring and visualization in RViz.

## Highlights

- Dual controller: Unitree’s built‑in loco controller for walking + custom upper‑body controller for arm manipulation.

- Dual control modes: switch between Joint and Cartesian control on the fly.

- Always‑on telemetry: IMU, odometry, and per‑motor feedback (temperature, voltage, position, velocity).

- RViz‑ready: packaged URDF + RViz config for immediate visualization of the real robot.

- Docker‑first workflow: reproducible build/run scripts for Ubuntu 22.04 + ROS 2 Humble.

- Extensible: clear node boundaries and parameters make it easy to add behaviors or swap planners.

- Navigation stack integrated: MOLA odometry and path planner for autonomous navigation.

## G1Pilot Flow

<img src="https://github.com/hucebot/g1pilot/blob/main/images/g1pilot_flow.jpg" alt="G1Pilot Flow" width="800">

## G1Pilot Features


| **Joint Controller** | **Cartesian Controller** |
|---------------------|--------------------|
| <img src="https://github.com/hucebot/g1pilot/blob/main/images/joint_controller.gif" alt="Static Sensors" width="380"> | <img src="https://github.com/hucebot/g1pilot/blob/main/images/cartesian_controller.gif" alt="Moving Sensors" width="380"> |
| **Path Planner & Odometry** | **Control Interface** |
| <img src="https://github.com/hucebot/g1pilot/blob/main/images/odometry_and_pathplanner.gif" alt="Path Planner" width="380"> | <img src="https://github.com/hucebot/g1pilot/blob/main/images/fake_streamdeck.png" alt="Control Interface" width="380">  |

## Table of Contents
- [Pre-requisites](#pre-requisites)
- [Quick Start](#quick-start)
- [Nodes Overview](#-nodes-overview)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)

## Pre-requisites
- Be connected to the robot via Ethernet. **It's important to know which interface you are using.**

## Quick Start
### Docker (recommended)
We prepare two docker images to build and run the package. One is for building in the teleoperation station, and the other is for running in the robot. Both images
are located in the `docker` folder. You can build and run the images with the provided scripts.
To build the docker image in the laptop, run the following command:
  ```bash
  sh build.sh
  ```

To build the docker image in the robot, run the following command:
  ```bash
  sh build_camera.sh
  ```

Then, you can run the docker image in the laptop with the following command:
  ```bash
  sh run.sh
  ```

To run the docker image in the robot with the following command:
  ```bash
  sh run_camera.sh
  ```

## 🧠 Nodes Overview

- **robot_state**: Publishes the state of the robot, including joint positions, velocities, and efforts and custom message to visualize the temperature and voltage of each motor.
- **interactive_marker**: Provides an interactive marker in RViz to control the end-effector position and orientation in Cartesian space.
- **dx3_controller**: Node to control the DEX3 Unitree hand, allowing to open and close the hand using ROS2 commands.
- **joystick**: Node to teleoperate the robot using a joystick, mapping joystick inputs to robot commands.
- **joy_mux**: Multiplexer for joystick inputs, allowing to switch between different control modes, specifcally made to provide autonomous navigation and teleoperation using the same joystick.
- **loco_client**: Client node to communicate with the Unitree loco controller, providing high-level commands for walking and balancing and low-level commands for joint control and cartesian control.
- **dijkstra_planner**: Custom path planner using Dijkstra's algorithm to compute optimal paths for the robot to follow in a given environment with a look ahead distance parameter to smooth the path and improve navigation performance.
- **nav2point**: Node to integrate the planner with the navigation stack, converting navigation goals into waypoints for the robot to follow.
- **create_map**: Dummy node to create a 2D occupancy grid map from the robot's sensors, used for navigation and obstacle avoidance. 
- **mola_fixed**: Node to interface with the MOLA odometry system, transform the odometry data into g1 frame.
- **arm_controller**: Node to control the upper body of the robot, providing joint and cartesian control modes for the arms.
- **ui_interface**: Node to provide a user interface to control the main functionalities of the robot.
## Usage

### Configuration File
The configuration file is located in the `config` folder. You can modify the parameters according to your needs. It's important to set up all the correct information for your robot.

### Instructions
Once you have the docker image running, you can run the following command to start the unitree node: For this we implement a custom build command to build the packages inside the docker.
If you want to build all the packages, you can run the following command:
```bash
./cbuild 
```
If you want to build only the g1pilot package, you can run the following command:
```bash
./cbuild g1pilot
```

Then, source the workspace:

```bash
source install/setup.bash
```

Also if you are connected to the robot, you need to source the way to connecto the robot, for example:

```bash
source setup_uri.sh <interface>
``` 

For the real Unitree G1 **23 DOF Rev 1.0** in this `g1-23dof` checkout, use the dedicated launch and configuration.

Wire the PC to the robot over Ethernet and give that port `192.168.123.123/24` (the IP `config/livox_mid.json` expects). Then start the container with `run_real.sh`, which checks the interface, IP and that the robot (`192.168.123.161`) answers ping. It defaults to `enp43s0`; override with `G1_INTERFACE=<iface>`:

```bash
sudo ip addr add 192.168.123.123/24 dev enp43s0 && sudo ip link set enp43s0 up
cd docker
./run_real.sh
```

Inside the container, first check that state arrives without starting any motion node (`G1_INTERFACE` is passed in by the script):

```bash
./cbuild g1pilot
source /ros2_ws/setup_uri.sh $G1_INTERFACE
ros2 launch g1pilot robot_state_23dof.launch.py use_rviz:=false
# another shell: ros2 topic hz /joint_states
```

Then the full bringup (starts `loco_client`, which can move the robot):

```bash
ros2 launch g1pilot bringup_23dof.launch.py
```

`loco_client` damps the motors when it starts, so the robot must hang on its gantry before launching.

#### Keyboard teleoperation

Without a PS4 controller, drive the robot from a terminal. It publishes the same `Joy` layout as the joystick node on `/g1pilot/joy_manual`, so `joy_mux` and `loco_client` work unchanged. Run it in its own shell (it needs a TTY, so it cannot run from a launch file):

```bash
docker exec -it g1pilot-dev bash
ros2 run g1pilot keyboard_teleop
```

The keys are the same as `g1_ctrl` in `unitree_rl_mjlab`:

| Key | Action |
|---|---|
| `u` | Standby (FSM 4), also clears an emergency stop |
| `v` | Stand up, balance and enable walking |
| `w`/`s` | Forward 0.4 m/s / backward 0.3 m/s (hold the key) |
| `a`/`d` | Strafe left/right 0.2 m/s (hold the key) |
| `q`/`e` | Turn left/right 0.3 rad/s (hold the key) |
| `x` / `space` | Stop moving |
| `+` / `-` | Speed scale (0.25 to 1.25, default 1.0) |
| `p` | Emergency stop (damps the motors) |

Unlike `g1_ctrl`, movement keys must be held: the robot stops `key_timeout` (0.7 s) after a key is released. Do not use it together with a connected PS4 controller, since both publish on the same topic.

This launch uses `config/config_23dof.yaml` and `g1_23dof_rev_1_0.urdf`. It starts robot state, locomotion, joystick, Livox, and MOLA by default. It does not start the 29 DOF OpenSoT arm solver or the DX3 hand controller. Autonomous path planning also needs an occupancy grid on `/map` from a map server.

The older `bringup_launcher.launch.py` remains for the 29 DOF setup; do not use it for the 23 DOF robot.

### Connect to a local MuJoCo DDS simulator first

Start the 23 DOF MuJoCo simulator on the host and configure its Unitree DDS transport to use loopback (`lo`, `domain_id: 0`). The Docker container uses host networking, so `lo` is shared with the host.

Order matters: `lo` must have multicast enabled **before** the simulator starts, otherwise CycloneDDS discovery never finds `robot_state` and no `/joint_states` are published. After a reboot, run this on the host first:

```bash
sudo ip link set lo multicast on
```

Then start `unitree_mujoco` (and `g1_ctrl --network=lo`). `run_sim.sh` also enables the flag if it is missing, but then you must restart the simulator. In another host terminal:

```bash
cd docker
./build.sh
./run_sim.sh
```

`run_sim.sh` forces `ROS_DOMAIN_ID=1` (ROS 2 must not share domain `0` with the Unitree SDK inside `robot_state`). The container is started with `--rm`, so `./cbuild g1pilot` is needed every time a new container is started.

Inside the container, build the mounted workspace, select `lo` for CycloneDDS, then launch the 23 DOF simulation profile:

```bash
./cbuild g1pilot
source /ros2_ws/setup_uri.sh lo
ros2 launch g1pilot bringup_23dof_sim.launch.py
```

This profile keeps `use_robot:=true` so `robot_state` subscribes to the simulator's Unitree `rt/lowstate` channel on loopback; it does not start the `loco_client` RPC node, Livox, or MOLA. The MuJoCo simulator's own controls move the simulated robot, and RViz mirrors its joint state. This is different from `use_robot:=false`, which only generates local dummy state and does not connect to a simulator. The simulator and SDK channel must use Unitree DDS domain `0`, matching the package default.

Or you can run each node separately according to your needs.

1.- To run the Livox LiDAR, you can run the following command:

```bash
ros2 launch g1pilot livox_launcher.launch.py
```

2.- To run the mola odometry, you can run the following command:

```bash
ros2 launch g1pilot mola_launcher.launch.py
```

3.- To run the navigation stack and enable the locomotion of the robot, you can run the following command:

```bash
ros2 launch g1pilot navigation_launcher.launch.py
```

4.- To run the manipulation stack, you can run the following command:

```bash
ros2 launch g1pilot manipulation_launcher.launch.py
```

5.- To run the teleoperation stack, you can run the following command:

```bash
ros2 launch g1pilot teleoperation_launcher.launch.py
```

6.- You can run the depth camera on the robot with the following command:
```bash
ros2 launch realsense2_camera rs_launch.py depth_module.depth_profile:=1280x720x30 pointcloud.enable:=true
```

For more details on how to use the package, please refer to the [instructions](docs/INSTRUCTIONS.md) document. Also you can check the [cheats](docs/CHEATS.md) document for quick commands and tips to use the package.

## Contributing
We welcome contributions to **G1Pilot**! If you have suggestions, improvements, or bug fixes, please follow these steps:

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Make your changes and commit them with clear messages.
4. Submit a pull request detailing your changes.


## Maintainer
This package is maintained by:

**Clemente Donoso**  
Email: [clemente.donoso@inria.fr](mailto:clemente.donoso@inria.fr)
GitHub: [CDonosoK](https://github.com/CDonosoK)  

## License
BSD‑3‑Clause. See [LICENSE](LICENSE) for details.
