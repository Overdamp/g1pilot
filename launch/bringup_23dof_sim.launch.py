import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    package_share = get_package_share_directory('g1pilot')
    state_path = os.path.join(package_share, 'launch', 'robot_state_23dof.launch.py')
    interface = LaunchConfiguration('interface')
    use_rviz = LaunchConfiguration('use_rviz')

    return LaunchDescription([
        DeclareLaunchArgument(
            'interface',
            default_value='lo',
            description='Loopback DDS interface for a MuJoCo simulator on this host',
        ),
        DeclareLaunchArgument('use_robot', default_value='true'),
        DeclareLaunchArgument('use_rviz', default_value='true'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(state_path),
            launch_arguments={
                'interface': interface,
                'use_robot': LaunchConfiguration('use_robot'),
                'use_rviz': use_rviz,
            }.items(),
        ),
    ])
