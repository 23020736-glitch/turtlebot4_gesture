# Điều khiển TurtleBot 4 bằng cử chỉ tay (ROS 2 Humble)

Nhận diện cử chỉ tay qua webcam laptop bằng **MediaPipe Gesture Recognizer**, rồi điều khiển
**TurtleBot 4 trong Gazebo** thông qua ROS 2.

## Kiến trúc

```
Webcam -> gesture_recognition_node -> /detected_gesture (std_msgs/String)
       -> robot_behavior_node      -> /cmd_vel (geometry_msgs/Twist) -> TurtleBot 4 (Gazebo)
```

| Node | Chức năng |
|---|---|
| `gesture_recognition_node` | Đọc webcam (OpenCV), nhận diện cử chỉ, hiển thị tên + độ tin cậy, publish `/detected_gesture` |
| `robot_behavior_node` | Subscribe cử chỉ, máy trạng thái, publish vận tốc lên `/cmd_vel` |

## Cử chỉ và hành vi

| Cử chỉ | Tên trên topic | Hành vi robot |
|---|---|---|
| Vẫy tay | `Wave` | Xoay trái–phải để chào |
| Giơ 1 ngón tay | `Pointing_Up` | Chọn hành vi tiến–lùi 4 lần |
| Giơ 2 ngón tay | `Victory` | Chọn hành vi quỹ đạo tròn |
| Giơ ngón cái | `Thumb_Up` | Xác nhận và chạy hành vi đã chọn |
| Xòe bàn tay | `Open_Palm` | Dừng ngay |
| Nắm tay | `Closed_Fist` | Hủy hành vi, về trạng thái chờ |

Robot chỉ chạy sau khi nhận `Thumb_Up`. Có chống nhiễu (ngưỡng tin cậy, ổn định 6 frame, cooldown 1 s)
và tự dừng nếu mất tín hiệu hơn 2 giây.



## Cài đặt và build

```bash
pip3 install mediapipe opencv-python "numpy<2"

mkdir -p ~/ros2_ws/src && cd ~/ros2_ws/src
git clone https://github.com/23020736-glitch/turtlebot4_gesture.git turtlebot4_gesture

cd ~/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select turtlebot4_gesture
source install/setup.bash
```



## Chạy

**Terminal 1 – Gazebo:**
```bash
source /opt/ros/humble/setup.bash
ros2 launch turtlebot4_ignition_bringup turtlebot4_ignition.launch.py world:=maze
```


**Terminal 2 – Nhận diện và điều khiển:**
```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 launch turtlebot4_gesture gesture_control.launch.py
```


## Kiểm tra

```bash
ros2 topic echo /detected_gesture
ros2 topic info /cmd_vel
```

## Cấu trúc thư mục

```
turtlebot4_gesture/
├── launch/gesture_control.launch.py
├── turtlebot4_gesture/
│   ├── gesture_recognition_node.py
│   └── robot_behavior_node.py
├── package.xml
├── setup.py
└── README.md
```
