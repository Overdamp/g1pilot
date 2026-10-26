import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import EnvironmentVariable, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    package_share = get_package_share_directory('g1pilot')
    config_path = os.path.join(package_share, 'config', 'config_23dof.yaml')
    interface = LaunchConfiguration('interface')
    use_robot = LaunchConfiguration('use_robot')

    def include_launch(filename, condition=None, launch_arguments=None):
        path = os.path.join(package_share, 'launch', filename)
        return IncludeLaunchDescription(
            PythonLaunchDescriptionSource(path),
            condition=condition,
            launch_arguments=launch_arguments,
        )

    return LaunchDescription([
        DeclareLaunchArgument(
            'interface', default_value=EnvironmentVariable('G1_INTERFACE')
        ),
        DeclareLaunchArgument('use_robot', default_value='true'),
        DeclareLaunchArgument('use_livox', default_value='true'),
        DeclareLaunchArgument('use_mola', default_value='true'),
        DeclareLaunchArgument('use_rviz', default_value='true'),
        include_launch(
            'robot_state_23dof.launch.py',
            launch_arguments={
                'interface': interface,
                'use_robot': use_robot,
                'use_rviz': LaunchConfiguration('use_rviz'),
            }.items(),
        ),
        Node(
            package='g1pilot',
            executable='mola_fixed',
            name='mola_fixed',
            condition=IfCondition(LaunchConfiguration('use_mola')),
            output='screen',
        ),
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='mid360_to_livox_tf',
            condition=IfCondition(LaunchConfiguration('use_livox')),
            arguments=['0', '0', '0', '0', '0', '3.14159265', 'mid360_link', 'livox_frame'],
        ),
        Node(
            package='g1pilot',
            executable='loco_client',
            name='loco_client',
            parameters=[
                config_path,
                {
                    'interface': interface,
                    'use_robot': ParameterValue(use_robot, value_type=bool),
                    'enable_arm_ui': False,
                },
            ],
            output='screen',
        ),
        Node(
            package='g1pilot',
            executable='dijkstra_planner',
            name='dijkstra_planner',
            parameters=[config_path],
            output='screen',
        ),
        Node(
            package='g1pilot',
            executable='nav2point',
            name='nav2point',
            parameters=[config_path],
            output='screen',
        ),
        Node(
            package='g1pilot',
            executable='joystick',
            name='joystick',
            parameters=[config_path],
            output='screen',
        ),
        Node(
            package='g1pilot',
            executable='joy_mux',
            name='joy_mux',
            parameters=[config_path],
            output='screen',
        ),
        include_launch('livox_launcher.launch.py', IfCondition(LaunchConfiguration('use_livox'))),
        include_launch('mola_launcher.launch.py', IfCondition(LaunchConfiguration('use_mola'))),
    ])
