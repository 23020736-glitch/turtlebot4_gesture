from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(package='turtlebot4_gesture', executable='gesture_recognition_node',
             name='gesture_recognition_node', output='screen'),
        Node(package='turtlebot4_gesture', executable='robot_behavior_node',
             name='robot_behavior_node', output='screen'),
    ])
