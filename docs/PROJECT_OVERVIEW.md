# ภาพรวมโปรเจกต์ G1Pilot

เอกสารนี้สรุปโครงสร้างและเส้นทางการทำงานของซอร์สในแพ็กเกจ `g1pilot` เพื่อช่วยให้เริ่มอ่านและพัฒนาต่อได้ง่ายขึ้น

## ขอบเขตของรีโปนี้

มีสอง checkout ที่มีวัตถุประสงค์คนละแบบ:

- รีโป/checkout เดิมใช้กับ `lo g1` และการจำลองใน MuJoCo
- รีโปใหม่ branch `g1-23dof` ใช้พัฒนาและเชื่อมต่อกับหุ่นจริง

เอกสารและขั้นตอน Docker สำหรับการเชื่อมต่อหุ่นจริงด้านล่างหมายถึง checkout `g1-23dof` เท่านั้น ปัจจุบัน checkout ใน workspace นี้รายงาน branch `g1-23dof` และ remote `https://github.com/Overdamp/g1pilot.git`; `docker/run.sh` mount โฟลเดอร์ repository ที่อยู่ข้าง `docker/` เข้า container จึงทำงานกับ source checkout ปัจจุบันโดยตรง ไม่ได้ mount repo จำลองจากที่อื่นให้อัตโนมัติ

## G1Pilot คืออะไร

`g1pilot` เป็น ROS 2 Python package สำหรับควบคุมและติดตามหุ่นยนต์ humanoid Unitree G1 โดยเชื่อม ROS 2 เข้ากับ Unitree SDK ผ่าน DDS ใช้ Unitree locomotion controller ดูแลการเดิน/การทรงตัว และมีโหนดในแพ็กเกจสำหรับสถานะหุ่นยนต์ การควบคุมแขนและมือ การรับคำสั่งจาก joystick และการนำทางจาก LiDAR

โค้ดและ Dockerfile ปัจจุบันอ้างอิง ROS 2 Jazzy (`osrf/ros:jazzy-desktop`) ส่วน README เดิมยังมีข้อความเรื่อง Humble ในส่วน Docker จึงควรยืนยันเวอร์ชันสภาพแวดล้อมจาก Docker และ dependency ที่ติดตั้งจริงก่อนนำคำสั่งเดิมไปใช้บนเครื่องอื่น

## ภาพรวมเส้นทางข้อมูล

```text
Unitree SDK ──> robot_state ──> /joint_states, /g1pilot/imu, /g1pilot/motor_state, TF
      ▲                                  │
      │                                  └──> robot_state_publisher / RViz
      │
      ├── loco_client <── /g1pilot/joy <── joy_mux <── joystick
      │                                     ▲
      │                                     └── nav2point <── dijkstra_planner
      │                                                          ▲
      │                                                  /map, odometry, goal
      │
      └── opensot_solver <── เป้าหมายมือ / interactive marker
                    └── dx3_controller ควบคุมมือ DEX3

Livox ──> MOLA LiDAR odometry ──> mola_fixed ──> odometry สำหรับ planner/controller
```

แผนภาพเป็นภาพรวมเชิงหน้าที่ ชื่อ topic และชนิดข้อความที่ใช้จริงอาจต่างกันตามโหนดและค่าพารามิเตอร์ ให้ตรวจ source/config ก่อนเชื่อมระบบเพิ่มเติม

## โครงสร้างไดเรกทอรี

| ที่อยู่ | หน้าที่ |
|---|---|
| `g1pilot/state/` | อ่านสถานะ G1 และจัดรูปเป็นข้อความ ROS 2 |
| `g1pilot/manipulation/` | เป้าหมายปลายแขน, inverse kinematics/OpenSoT, การควบคุม DX3 |
| `g1pilot/navigation/` | Unitree loco client, planner, waypoint tracking, map ตัวอย่าง และแก้กรอบ odometry |
| `g1pilot/teleoperation/` | joystick, การเลือก manual/autonomous และ GUI |
| `g1pilot/utils/` | ฟังก์ชันช่วย, รายชื่อ joints, GUI แขน และการอ่าน config |
| `launch/` | รวมโหนดเป็น launch สำหรับ state, teleoperation, navigation, manipulation และ bringup |
| `config/` | พารามิเตอร์หลักและไฟล์ RViz |
| `description_files/urdf/`, `description_files/meshes/` | คำอธิบายโมเดลและ mesh ของหุ่นยนต์ |
| `pipelines/` | การตั้งค่า MOLA |
| `docker/` | Dockerfile, compose, entrypoint และสคริปต์เชื่อมต่อเครือข่าย |
| `docs/` | วิธีใช้งานเดิมและเอกสารภาพรวมนี้ |

แพ็กเกจใช้ `ament_python`; `setup.py` ประกาศ executable ของ ROS 2 ผ่าน `console_scripts` เช่น `robot_state`, `loco_client`, `opensot_solver` และ `dijkstra_planner`

## โหนดสำคัญ

### สถานะหุ่นยนต์

`robot_state` สมัครรับ Unitree `rt/lowstate` เมื่อ `use_robot=true` และเผยแพร่ข้อมูล IMU, motor state, joint state (ตามการตั้งค่า) และ TF โหมด `use_robot=false` ใช้ timer สร้างสถานะจำลองอย่างง่าย ไม่ใช่ physics simulator

### การควบคุมแขนและมือ

- `opensot_solver` เป็น loop ควบคุมแขน/แก้ inverse kinematics และรับคำสั่งเริ่มกับหยุดฉุกเฉิน รวมทั้งสามารถเปิด collision avoidance ได้
- `interactive_marker` สร้าง marker สำหรับกำหนด pose ของมือใน RViz และส่ง `PoseStamped`
- `dx3_controller` เชื่อมต่อมือ Unitree DEX3 ผ่าน SDK และเผยแพร่สถานะมือ

หมายเหตุ: executable `interactive_marker` มีใน `setup.py` แต่ไม่ได้ถูกเพิ่มใน `manipulation_launcher.launch.py` ปัจจุบัน หากต้องการใช้งานให้เปิดโหนดแยกหรือปรับ launch ตามการใช้งานจริง

### การนำทางและ teleoperation

- `joystick` อ่านอุปกรณ์ joystick และส่งคำสั่ง manual รวมถึงเปิด/ปิดโหมด autonomous
- `joy_mux` รวมคำสั่ง manual กับคำสั่งจาก autonomous controller แล้วส่ง `/g1pilot/joy`
- `loco_client` แปลง joystick/คำสั่ง ROS ให้เป็นคำสั่ง Unitree loco รวมถึง start, balance และ emergency stop
- `dijkstra_planner` ใช้ occupancy grid, odometry และ goal เพื่อสร้างเส้นทาง โดยรองรับการขยายสิ่งกีดขวางและปรับเส้นทางให้เรียบ
- `nav2point` ติดตาม path แล้วสร้างคำสั่ง `Joy` สำหรับการเคลื่อนที่
- `fix_mola_odometry` แปลง/จัดกรอบข้อความ odometry จาก MOLA เพื่อเผยแพร่ `/lidar_odometry/pose_fixed`
- `create_map` สร้าง occupancy grid แบบง่ายสำหรับทดลอง ไม่ใช่ระบบทำแผนที่จาก sensor

### GUI และ state

`ui_interface` เป็น GUI ปุ่มกดสำหรับเริ่มระบบ, balance, เปิดแขน, home, เปิด/ปิด solver และ emergency stop ทั้งนี้ topic ที่ GUI ใช้บางตัวอาจไม่ตรงกับ topic ใน node อื่นหรือ config ปัจจุบัน จึงควรตรวจ topic ด้วย `ros2 topic list` และ source ก่อนนำ GUI ไปใช้ควบคุมหุ่นยนต์จริง

## Launch files

| Launch | สิ่งที่เริ่ม |
|---|---|
| `bringup_launcher.launch.py` | รวม navigation, robot state, teleoperation และ manipulation |
| `bringup_opensot.launch.py` | Bringup ทางเลือกสำหรับ OpenSoT โดยไม่ส่งคำสั่งแขนจริงตามค่า launch เริ่มต้น |
| `robot_state_launcher.launch.py` | robot state, TF คงที่, robot_state_publisher และ RViz |
| `robot_state_23dof.launch.py` | URDF 23 DOF Rev 1.0, motor index map 23 DOF, TF และ RViz |
| `navigation_launcher.launch.py` | `loco_client` และ `nav2point` |
| `teleoperation_launcher.launch.py` | joystick, joy mux และ UI |
| `manipulation_launcher.launch.py` | OpenSoT solver และ DX3 controller |
| `bringup_23dof.launch.py` | state, loco client, navigation/joystick, Livox และ MOLA ตาม config 23 DOF; ไม่เปิด controller แขน 29 DOF/DX3 |
| `bringup_23dof_sim.launch.py` | robot state + robot_state_publisher + RViz สำหรับรับ lowstate จาก MuJoCo ผ่าน `lo`; ไม่เริ่ม Loco RPC |
| `livox_launcher.launch.py` | Livox ROS driver |
| `mola_launcher.launch.py` | MOLA odometry และค่าตั้งต้นผ่าน environment variables |

Launch หลายไฟล์ตรวจว่าตั้ง `G1_INTERFACE` แล้ว แม้จะส่ง `interface` เป็น launch argument ได้ก็ตาม ตัวอย่าง:

```bash
export G1_INTERFACE=ชื่ออินเทอร์เฟซเครือข่าย
ros2 launch g1pilot bringup_launcher.launch.py
```

ชื่อ interface ขึ้นอยู่กับเครื่อง (เช่น `eno2` หรือ `enp...`) ควรตรวจด้วย `ip link` และเลือก interface ที่ต่อกับหุ่นยนต์

## การตั้งค่าหลัก

ไฟล์ `config/config.yaml` จัดกลุ่มค่าหลักเป็น:

- `general`: โหมด simulation/robot, การเผยแพร่ joint state, interface, โมเดลและการเปิด component
- `inverse_kinematics`: gain, จำกัดความเร็ว และขนาดการเปลี่ยนคำสั่ง IK
- `home`: ตำแหน่ง home ของมอเตอร์แขนแต่ละข้าง
- `workspace`: จุดขอบเขต workspace ที่ใช้กับแขน
- `robot`, `state`: topic และ frame ที่ใช้กับ robot/state
- `dex3`: topic และค่าท่ามือเปิด/ปิด
- `manipulation`, `navigation`: topic และขีดจำกัดความเร็ว

การมีค่าใน YAML ไม่ได้แปลว่า launch ทุกตัวโหลดไฟล์นี้โดยอัตโนมัติ: launch บางตัวกำหนดค่าผ่าน argument โดยตรง และบางโหนดประกาศพารามิเตอร์พร้อมค่า default ใน Python ดังนั้นให้ตรวจทั้ง launch file และ node ก่อนเปลี่ยนค่า

เส้นทาง 23 DOF ใช้ `config/config_23dof.yaml` ซึ่งเป็น ROS 2 parameter file ที่ launch แยกโหลดโดยตรง ส่วน URDF ที่ติดตั้งกับแพ็กเกจคือ `description_files/urdf/g1_23dof_rev_1_0.urdf`; มาจากโมเดลใน `g1_description/` และปรับ mesh URI ให้ resolve ผ่าน package `g1pilot`

## Workflow พัฒนาใน Docker และเชื่อม G1 จริง

`docker/run.sh` เปิด shell แบบ interactive และ mount repository ทั้งโฟลเดอร์จาก host ไปที่ `/ros2_ws/src/g1pilot` ใน container ดังนั้นการแก้หรือเพิ่มไฟล์บน host จะเห็นได้ทันทีใน container และการแก้ไฟล์จาก container ก็เขียนกลับมายัง host ได้ ใช้ Docker image `g1pilot:latest` ซึ่งสร้างจาก `docker/Dockerfile` ก่อน

### 1. ตรวจ interface และสร้าง image

บน host ให้หา interface ที่ต่อกับหุ่นยนต์ด้วย `ip link` แล้วเข้าโฟลเดอร์ `docker` ของ repository:

```bash
cd /path/to/g1pilot/docker
ip link
./build.sh
```

สคริปต์ build image ต้องรันจากโฟลเดอร์ `docker` เพราะ Dockerfile ใช้ชื่อ/บริบทไฟล์ในโฟลเดอร์นั้น

### 2. เปิด development container จาก checkout `g1-23dof`

```bash
G1_INTERFACE=<ชื่อ-interface-ที่ต่อกับ-G1> ./run.sh
```

ตัวอย่าง: `G1_INTERFACE=eno2 ./run.sh`. ให้รันคำสั่งนี้จาก `docker/` ภายใน checkout `g1-23dof` ที่ต้องการพัฒนา ไม่ใช่ checkout MuJoCo เดิม Container ใช้ host networking, `ROS_DOMAIN_ID` ค่าเริ่มต้น `1`, CycloneDDS และส่ง `G1_INTERFACE` เข้าไปใน container เพื่อให้เลือก network interface เดียวกับ host ได้ `run.sh` เปิด shell เท่านั้น ไม่ได้สั่งให้หุ่นยนต์เคลื่อนที่เอง

### 3. Build และตั้งค่า DDS ใน container

เมื่ออยู่ใน shell ของ container:

```bash
./cbuild
source /ros2_ws/setup_uri.sh "$G1_INTERFACE"
```

หลังแก้ Python/launch/config ให้ build ซ้ำตามต้องการ เช่น `./cbuild g1pilot`; ถ้าเพิ่ม ROS package ใหม่ให้ build package นั้นหรือใช้ `./cbuild` เพื่อ build workspace ตามค่าเริ่มต้น จากนั้น source setup อีกครั้งใน terminal ใหม่ก่อนเรียก ROS 2

### 4. เริ่มระบบบนหุ่นยนต์

```bash
ros2 launch g1pilot bringup_23dof.launch.py
```

Bringup 23 DOF ใช้ URDF/joint map รุ่น 23 DOF และเปิด loco client, state, joystick, planner, Livox กับ MOLA (ค่าเริ่มต้นเปิด sensor ทั้งคู่) แต่ไม่เปิด OpenSoT หรือ DX3 ซึ่งยังเป็น 29 DOF/มือรุ่นอื่น เส้นทางนี้รองรับ locomotion และ telemetry; การควบคุมแขนผ่าน OpenSoT ต้องปรับ solver เป็น 23 DOF ก่อนเปิดใช้งาน Planner ต้องมี occupancy grid บน `/map` จาก map server ภายนอก เพราะ MOLA ในชุดนี้ให้ odometry ไม่ได้สร้าง `/map` ให้อัตโนมัติ

### ทดสอบกับ MuJoCo simulator ผ่าน loopback ก่อน

ต้องเปิด simulator บน host แยกต่างหากและตั้ง Unitree DDS ให้ใช้ `lo`; Docker ใช้ `--network host` จึงเห็น loopback เดียวกับ host ใช้ wrapper เพื่อเปิด shell ด้วย interface `lo` และ ROS domain เริ่มต้น `1`:

```bash
cd /path/to/g1pilot/docker
./build.sh
./run_sim.sh
```

ใน container:

```bash
./cbuild g1pilot
source /ros2_ws/setup_uri.sh lo
ros2 launch g1pilot bringup_23dof_sim.launch.py
```

Simulation launch ตั้ง `use_robot=true` เพื่อให้ `robot_state` สมัคร Unitree `rt/lowstate` ผ่าน `lo`; MuJoCo simulator ควบคุมหุ่นตาม input ของมันเองและ RViz แสดง joint state ตาม simulator Launch นี้ไม่เปิด `loco_client` เพราะ simulator ที่ใช้ใน workflow นี้ไม่ได้ตอบ Loco RPC รวมถึงไม่เปิด Livox/MOLA ส่วน `use_robot=false` เป็นเพียง dummy state ใน package นี้ ไม่ได้เชื่อม MuJoCo ตรวจให้ simulator ใช้ Unitree SDK domain `0` ตามค่าเริ่มต้นของ package

### Mount และเพิ่มโปรแกรม

ตำแหน่ง host ที่ mount คือ root ของ repository (`docker/..`); ตำแหน่งเดียวกันใน container คือ `/ros2_ws/src/g1pilot`. เพิ่ม node ใหม่ใน `g1pilot/` แล้วประกาศ executable ใน `setup.py` และเพิ่มไฟล์ launch/config ที่ต้องติดตั้งใน `data_files`/launch ตามรูปแบบของแพ็กเกจ จากนั้นรัน `./cbuild <ชื่อ-package>` ใน container เพื่อให้ `ros2 run`/`ros2 launch` เห็น entry point ล่าสุด

> หมายเหตุ: `docker-compose.yml` ปัจจุบันอ้าง `env.conf` ซึ่งไม่มีใน repository และใช้ `entrypoint.sh` ที่ build แล้วเปิด bringup ทันที จึงไม่ใช่เส้นทาง development แบบ interactive ที่อธิบายข้างต้น ให้ใช้ `run.sh` สำหรับพัฒนา หรือเตรียมไฟล์ environment ของ Compose ให้ครบก่อนใช้งาน Compose

ให้ดู `README.md`, `docs/INSTRUCTIONS.md` และ `docs/CHEATS.md` สำหรับคำสั่งเดิมเพิ่มเติม แต่ควรตรวจชื่อ topic และชนิดข้อความก่อนใช้ เพราะเอกสารเดิมบางส่วนไม่สอดคล้องกับซอร์สปัจจุบัน เช่น `config.yaml` ระบุ `/g1pilot/left_hand_goal` ขณะที่ interactive marker ใช้ `/g1pilot/hand_goal/left`; และคำสั่ง DEX3 ใน cheats ใช้ `std_msgs/String` ขณะที่ `dx3_hand.py` ปัจจุบันสมัครรับ `geometry_msgs/PointStamped` บน topic อื่น

## ข้อควรตรวจสอบก่อนใช้งานจริง

1. ยืนยัน interface, ROS domain, CycloneDDS และการเชื่อมต่อเครือข่ายกับ G1 ให้ตรงกับ `docker-compose.yml`/`cyclonedds.xml` และค่าจริงของเครื่อง
2. ตรวจว่ามี dependencies นอกแพ็กเกจ โดยเฉพาะ Unitree SDK Python, `astroviz_interfaces`, Livox driver, MOLA, RViz และ OpenSoT/HPP-FCL ที่ Dockerfile เตรียมไว้
3. เทียบ topic/type ระหว่าง publisher กับ subscriber ก่อนส่งคำสั่ง เพราะชื่อและชนิดในเอกสารเก่า, config และโค้ดบางจุดไม่ตรงกัน
4. ตรวจค่า `use_robot` และ `send_cmds_to_robot` ให้เหมาะกับการทดลอง Launch เริ่มต้นของ bringup ส่งคำสั่งไปยังหุ่นยนต์จริง
5. สำหรับหุ่น 23 DOF ให้ใช้ `bringup_23dof.launch.py`; `bringup_launcher.launch.py` เดิมยังใช้ state/manipulation ของ 29 DOF และไม่ควรใช้กับหุ่นรุ่นนี้

## แหล่งอ่านต่อใน repository

- [`README.md`](../README.md) — ภาพรวมและ workflow ที่ผู้พัฒนาเดิมบันทึกไว้
- [`docs/INSTRUCTIONS.md`](INSTRUCTIONS.md) และ [`docs/CHEATS.md`](CHEATS.md) — คำแนะนำและคำสั่งตัวอย่างเดิม
- [`config/config.yaml`](../config/config.yaml) — ค่าพารามิเตอร์และ topic ที่บันทึกไว้
- [`setup.py`](../setup.py) — รายการ executable และไฟล์ที่ติดตั้ง
- [`launch/`](../launch/) — การประกอบ node และค่า launch argument
