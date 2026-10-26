import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import EnvironmentVariable, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    package_share = get_package_share_directory('g1pilot')
    urdf_path = os.path.join(
        package_share, 'description_files', 'urdf', 'g1_23dof_rev_1_0.urdf'
    )
    rviz_path = os.path.join(package_share, 'config', '23dof.rviz')

    with open(urdf_path, 'r', encoding='utf-8') as urdf_file:
        robot_description = urdf_file.read()

    interface = LaunchConfiguration('interface')
    use_robot = LaunchConfiguration('use_robot')
    use_sim_time = LaunchConfiguration('use_sim_time')
    publish_joint_states = LaunchConfiguration('publish_joint_states')
    sim_rate_hz = LaunchConfiguration('sim_rate_hz')
    config_path = os.path.join(package_share, 'config', 'config_23dof.yaml')

    return LaunchDescription([
        DeclareLaunchArgument(
            'interface',
            default_value=EnvironmentVariable('G1_INTERFACE'),
            description='Network interface connected to the Unitree G1',
        ),
        DeclareLaunchArgument('use_robot', default_value='true'),
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument('publish_joint_states', default_value='true'),
        DeclareLaunchArgument('sim_rate_hz', default_value='50.0'),
        DeclareLaunchArgument('use_rviz', default_value='true'),
        Node(
            package='g1pilot',
            executable='robot_state',
            name='robot_state',
            parameters=[config_path, {
                'model': '23dof',
                'interface': interface,
                'use_robot': ParameterValue(use_robot, value_type=bool),
                'publish_joint_states': ParameterValue(publish_joint_states, value_type=bool),
                'sim_rate_hz': ParameterValue(sim_rate_hz, value_type=float),
            }],
            output='screen',
        ),
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='pelvis_to_base_link_tf',
            arguments=['0', '0', '0', '0', '0', '0', 'base_link', 'pelvis'],
        ),
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            parameters=[{
                'use_sim_time': ParameterValue(use_sim_time, value_type=bool),
                'robot_description': robot_description,
            }],
        ),
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2_23dof',
            condition=IfCondition(LaunchConfiguration('use_rviz')),
            arguments=['-d', rviz_path],
        ),
    ])
