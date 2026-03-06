# M3Pro Robot Simulation Run & Installation Tutorial

This tutorial will guide you on how to setup your environment, install dependencies, and start the M3Pro robot's simulation and visualization interface.

## 1. Environment Dependencies Installation (Ubuntu 22.04 + ROS 2 Humble)

Before running the simulation, please assure that your system has installed ROS 2 Humble, and basic Gazebo environment is configured.
The following are the required dependencies needed to run the M3Pro robot. Please execute the following commands in your terminal to install them:

```bash
# Update software sources
sudo apt update

# 1. Install controller_manager core package (used to load and manage control plugins)
sudo apt install ros-humble-controller-manager

# 2. Install common controllers and control interfaces (essential for robotic arm and chassis)
sudo apt install ros-humble-ros2-control
sudo apt install ros-humble-ros2-controllers

# 3. Install bridge plugin between Gazebo and ros2_control (essential for simulation)
sudo apt install ros-humble-gazebo-ros-pkgs

# 4. Install Joint State Publisher GUI (used to control joints via sliders in RViz)
sudo apt install ros-humble-joint-state-publisher-gui

# 5. Install topic_tools (used for topic relaying, such as relaying /cmd_vel)
sudo apt install ros-humble-topic-tools

# 6. Install keyboard control node (used to drive chassis via keyboard inputs)
sudo apt install ros-humble-teleop-twist-keyboard
```

*Note: The `$ROS_DISTRO` in the above commands is explicitly replaced with `humble`, since M3Pro uses the ROS 2 Humble version of Ubuntu 22.04.*

---

## 2. Compile and Configure Workspace

Note that the M3Pro robot mainly contains two packages: `M3Pro_robot_description` and `M3Pro_robot_bringup`.

```bash
# 1. Enter the root directory of the workspace
cd ~/ros2_ws  # Please replace with your actual workspace path

# 2. Compile the workspace
colcon build

# 3. Source environment variables to make packages effective
source install/setup.bash
```

*(Tip: It is recommended to add `source ~/ros2_ws/install/setup.bash` to your `~/.bashrc` file, so that it loads automatically every time you open a terminal.)*

---

## 3. Run Tutorial

### Scenario 1: Verify robot model only in RViz (URDF display)

This function is solely utilized to browse and confirm the robot's URDF model, without physical simulation. Under this mode, it pops up a GUI window equipped with sliders. You can configure and review every joint's movement by dragging the sliders.

**Run Command:**
```bash
ros2 launch M3Pro_robot_description display.launch.py
```

**You will see:**
1. A popped up RViz2 window displaying the M3Pro robot model.
2. A popped up `joint_state_publisher_gui` window, where you can drag sliders to change the pose of the robotic arm and wheels directly.

---

### Scenario 2: Start Complete Gazebo Simulation System

This function will start a physical simulation environment powered by Gazebo, loading the control plugins (Mecanum wheel chassis and robotic arm), and triggering simulations for sensors like depth camera, LiDAR, etc.

**Run Command:**
```bash
ros2 launch M3Pro_robot_bringup M3Pro_robot.launch.py
```

**The system will complete the startup automatically following these steps:**
1. Start Gazebo Sim and load the `M3pro_world.sdf` simulation world.
2. Spawn the M3Pro robot model into Gazebo.
3. Start `ros_gz_bridge` to establish topic bridges between Gazebo and ROS 2 (e.g. sensor data `/scan`, `/camera/image_raw`, clock `/clock`, etc.).
4. Delayed loading of the `controller_manager` as well as various associated controller plugins (joint state publisher, arm controller, mecanum chassis controller, etc.).
5. Automatically open and configure the RViz2 UI for real-time status monitoring.
6. Start `cmd_vel_relay`, allowing users to send commands directly to the standard `/cmd_vel` topic to control the chassis.

---

## 4. Control and Test Simulation Environment

Once **Scenario 2** initiates successfully, you can open a new terminal for the tests stated below (before opening any new terminals, assure you've executed `source install/setup.bash` on them):

### 4.1 Chassis Control

#### 4.1.1 Command Line: Publish Twist to `/cmd_vel`

The chassis is controlled by **libgazebo_ros_planar_move**, and subscribes to `geometry_msgs/msg/Twist`.

**Move forward (linear velocity x=0.2 m/s):**
```bash
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
```

**Turn left (angular velocity z=0.5 rad/s):**
```bash
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.5}}"
```

---

## 5. Robotic Arm Control (Joint Angles)

The robotic arm is controlled by **arm_controller** (JointTrajectoryController), the interface is **position**, unit is **radians (rad)**.

Joint order and names:
- `arm1_Joint` ~ `arm5_Joint`: 5 joints of the robotic arm

### 5.1 Command Line: Send single point target

**Send a target configuration (5 joints, unit rad):**
```bash
ros2 action send_goal /arm_controller/follow_joint_trajectory control_msgs/action/FollowJointTrajectory \
  "{
    trajectory: {
      joint_names: [arm1_Joint, arm2_Joint, arm3_Joint, arm4_Joint, arm5_Joint],
      points: [
        {
          positions: [0.0, 0.0, 0.0, 0.0, 0.0],
          time_from_start: {sec: 2, nanosec: 0}
        }
      ]
    }
  }"
```

**Example: arm1 rotates to 0.5 rad, others to 0:**
```bash
ros2 action send_goal /arm_controller/follow_joint_trajectory control_msgs/action/FollowJointTrajectory \
  "{
    trajectory: {
      joint_names: [arm1_Joint, arm2_Joint, arm3_Joint, arm4_Joint, arm5_Joint],
      points: [
        {
          positions: [0.5, 0.0, 0.0, 0.0, 0.0],
          time_from_start: {sec: 2, nanosec: 0}
        }
      ]
    }
  }"
```

---

## 6. Gripper Control

The gripper is controlled separately by **gripper_controller** (GripperActionController).

- `rlink1_Joint`: Gripper joint

**Command Line: Open/Close Gripper:**
```bash
ros2 action send_goal /gripper_controller/gripper_cmd control_msgs/action/GripperCommand \
  "{
    command: {
      position: 0.0,
      max_effort: 5.0
    }
  }"
```
*(You can adjust the `position` value to open or close the gripper, unit often ranges around 0.0 to -1.54 depending on URDF limits).*

**View current joint status:**
```bash
ros2 topic echo /joint_states
```

---

## 7. How to drive from the application layer

### 7.1 Chassis: Publish `/cmd_vel` (Python)

```python
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

class ChassisDriver(Node):
    def __init__(self):
        super().__init__('chassis_driver')
        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)

    def move(self, linear_x=0.0, linear_y=0.0, angular_z=0.0):
        msg = Twist()
        msg.linear.x = float(linear_x)
        msg.linear.y = float(linear_y)
        msg.angular.z = float(angular_z)
        self.pub.publish(msg)

def main():
    rclpy.init()
    node = ChassisDriver()
    node.move(0.2, 0.0, 0.0)  # Move forward
    rclpy.spin_once(node, timeout_sec=0.5)
    node.destroy_node()
    rclpy.shutdown()
```

### 7.2 Robotic Arm: Send FollowJointTrajectory Action (Python)

```python
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from control_msgs.action import FollowJointTrajectory
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

ARM_JOINTS = ['arm1_Joint', 'arm2_Joint', 'arm3_Joint', 'arm4_Joint', 'arm5_Joint']

class ArmDriver(Node):
    def __init__(self):
        super().__init__('arm_driver')
        self._client = ActionClient(self, FollowJointTrajectory, '/arm_controller/follow_joint_trajectory')

    def go_to_joint_positions(self, positions, time_sec=2.0):
        """positions: array of 5 elements, unit radians (rad)"""
        if len(positions) != 5:
            raise ValueError('5 joint angles are required')
        goal_msg = FollowJointTrajectory.Goal()
        goal_msg.trajectory = JointTrajectory()
        goal_msg.trajectory.joint_names = ARM_JOINTS
        point = JointTrajectoryPoint()
        point.positions = [float(p) for p in positions]
        point.time_from_start.sec = int(time_sec)
        point.time_from_start.nanosec = 0
        goal_msg.trajectory.points = [point]
        self._client.wait_for_server()
        self._send_goal_future = self._client.send_goal_async(goal_msg)
        self._send_goal_future.add_done_callback(self._goal_response_callback)

    def _goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            return
        goal_handle.get_result_async().add_done_callback(self._result_callback)

    def _result_callback(self, future):
        pass  # Handle success/failure here

```

---

## 8. LiDAR and Depth Camera (How to enable and use)

LiDAR and depth camera have been configured as Gazebo plugins in **M3Pro_robot_sensors.xacro**, **as long as the robot is spawned into Gazebo using `M3Pro_robot.launch.py`, they will run automatically**, no extra enable commands are needed.

**(Optional) To visualize LiDAR rays in Gazebo:** You need to explicitly enable them in the Gazebo Sim GUI. Click the top-right menu (3 vertical dots) -> `Plugins` -> `Visualize Lidar`, or press the corresponding shortcut if configured.

### 8.1 LiDAR

| Description | Front LiDAR     | Rear LiDAR      |
|-------------|-----------------|-----------------|
| Topic       | `/scan`         | `/scan_back`    |
| Message Type| `sensor_msgs/msg/LaserScan` | Same as left    |

**View front LiDAR:**
```bash
ros2 topic echo /scan
```

**View in RViz:**
- Add LaserScan display, Topic select `/scan` or `/scan_back`, Fixed Frame select `base_footprint` or `odom`.

### 8.2 Depth Camera

| Topic                 | Type                    | Description |
|-----------------------|-------------------------|-------------|
| `/camera/image_raw`   | `sensor_msgs/msg/Image` | Image       |
| `/camera/camera_info` | `sensor_msgs/msg/CameraInfo` | Camera info |

**View image topic:**
```bash
ros2 topic list | grep camera
ros2 topic echo /camera/camera_info
```

**View image in RViz:**
- Add Image display, Topic select `/camera/image_raw`, Fixed Frame arbitrary (e.g. `Camera`).

### 8.3 Application Layer: Subscribe to LiDAR/Camera

**Python subscribe to front LiDAR:**
```python
from rclpy.node import Node
from sensor_msgs.msg import LaserScan

class LidarSub(Node):
    def __init__(self):
        super().__init__('lidar_sub')
        self.sub = self.create_subscription(LaserScan, '/scan', self.cb, 10)
    def cb(self, msg):
        # msg.ranges is array of distance data, msg.angle_min/angle_increment are angles
        pass
```

**Python subscribe to camera:**
```python
from sensor_msgs.msg import Image
# Subscribe to /camera/image_raw, use cv_bridge to convert to OpenCV format
```

---

## 9. Summary of Common Topics and Actions

| Function           | Type             | Topic / Action |
|--------------------|------------------|----------------|
| Chassis Control    | Topic (Twist)    | `/cmd_vel` |
| Arm Control        | Action           | `/arm_controller/follow_joint_trajectory` |
| Gripper Control    | Action           | `/gripper_controller/gripper_cmd` |
| Joint States       | Topic            | `/joint_states` |
| Odometry           | Topic            | `/odom` |
| Front LiDAR        | Topic (LaserScan) | `/scan` |
| Rear LiDAR         | Topic (LaserScan) | `/scan_back` |
| Camera Image       | Topic (Image)    | `/camera/image_raw` |
| Camera Info        | Topic            | `/camera/camera_info` |

Robotic arm has 5 joints: `arm1_Joint` ~ `arm5_Joint`. Control interface is **position**, unit is **rad**.
Gripper has 1 joint: `rlink1_Joint`.

---

## 10. How to Run Example Scripts

Runnable examples are provided in `M3Pro_robot_bringup/scripts/` (need to `source install/setup.bash` first and simulation must be started):

**Chassis: Move forward and stop**
```bash
cd /path/to/ros2_ws
source install/setup.bash
python3 src/M3Pro_robot_bringup/scripts/drive_chassis_example.py
```

**Robotic Arm: Move to given joint angles (5 radians, order as above)**
```bash
python3 src/M3Pro_robot_bringup/scripts/drive_arm_example.py
python3 src/M3Pro_robot_bringup/scripts/drive_arm_example.py 0.5 0 0 0 0
```

**List LiDAR/Camera Topics**
```bash
python3 src/M3Pro_robot_bringup/scripts/list_sensor_topics.py
```
