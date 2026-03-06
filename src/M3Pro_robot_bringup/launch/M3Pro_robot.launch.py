import os
import time
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch.substitutions import Command
from launch_ros.parameter_descriptions import ParameterValue

def generate_launch_description():
    # 0. Clean up resources
    print("Cleaning up resources...")
    os.system('pkill -9 gzserver; pkill -9 gzclient; pkill -9 ruby; pkill -9 robot_state_publisher; pkill -9 rviz2 > /dev/null 2>&1')
    time.sleep(2.0)

    # 1. Set package paths
    pkg_description = get_package_share_directory('M3Pro_robot_description')
    pkg_bringup = get_package_share_directory('M3Pro_robot_bringup') 
    
    main_xacro_path = os.path.join(pkg_description, 'urdf', 'M3Pro_robot_main.xacro')
    rviz_config = os.path.join(pkg_description, 'rviz', 'M3Pro.rviz')
    world_path = os.path.join(pkg_description, 'worlds', 'M3pro_world.sdf')

    # 2. Configure environment variables
    install_share_path = os.path.dirname(pkg_description)
    
    # 3. Parse Xacro
    robot_description_value = ParameterValue(
        Command(['xacro ', main_xacro_path]),
        value_type=str
    )

    # 4. Robot State Publisher
    node_robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description_value,
            'use_sim_time': True,
        }]
    )

    # 5. Start Gazebo Sim
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')
        ]),
        launch_arguments={'gz_args': [f'-r {world_path}']}.items()
    )

    # 6. Spawn robot
    spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-name', 'M3Pro',
            '-topic', 'robot_description',
            '-x', '0', '-y', '0', '-z', '0.15'
        ],
        output='screen',
    )

    # 7. ROS-GZ Bridge
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
            '/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan',
            '/scan_back@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan',
            '/camera/image@sensor_msgs/msg/Image[gz.msgs.Image',
            '/camera/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo',
        ],
        output='screen'
    )

    # 8. Delay loading controllers
    def create_controller_spawner(name, delay):
        return TimerAction(
            period=delay,
            actions=[
                Node(
                    package='controller_manager',
                    executable='spawner',
                    arguments=[name, '--controller-manager', '/controller_manager'],
                    output='screen',
                )
            ]
        )

    load_joint_state = create_controller_spawner('joint_state_broadcaster', 4.0)
    load_arm_controller = create_controller_spawner('arm_controller', 6.0)
    load_gripper_controller = create_controller_spawner('gripper_controller', 8.0)
    load_mecanum_controller = create_controller_spawner('mecanum_controller', 10.0)

    # ========================== Core Modifications ==========================
    # 9. Topic relay node (Relay)
    # Since the spawner's remap doesn't work, we directly start a relay node
    # It will continuously forward /cmd_vel messages to the topic listened by the controller
    cmd_vel_relay = Node(
        package='topic_tools',
        executable='relay',
        name='cmd_vel_relay',
        output='screen',
        parameters=[{
            'input_topic': '/cmd_vel',
            'output_topic': '/mecanum_controller/reference_unstamped',
            'type': 'geometry_msgs/msg/Twist',
            'qos_overrides./cmd_vel.subscription.reliability': 'best_effort'
        }]
    )
    # ===============================================================

    # 10. RViz2
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': True}],
    )

    return LaunchDescription([
        SetEnvironmentVariable('GZ_SIM_RESOURCE_PATH', install_share_path),
        SetEnvironmentVariable('GZ_SIM_SYSTEM_PLUGIN_PATH', '/opt/ros/humble/lib'),
        
        node_robot_state_publisher,
        bridge,
        gazebo,
        spawn_entity,
        load_joint_state,
        load_arm_controller,
        load_gripper_controller,
        load_mecanum_controller,
        cmd_vel_relay,  # Ensure this node is added
        rviz,
    ])