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

## Yêu cầu

- Ubuntu 22.04, ROS 2 Humble
- TurtleBot 4 Simulator: `sudo apt install ros-humble-turtlebot4-simulator`
- Webcam, Python 3

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

Lần chạy đầu, node nhận diện tự tải model `gesture_recognizer.task` về thư mục home (cần internet).

## Chạy

**Terminal 1 – Gazebo:**
```bash
source /opt/ros/humble/setup.bash
ros2 launch turtlebot4_ignition_bringup turtlebot4_ignition.launch.py world:=maze
```
Đợi khoảng 1–2 phút cho mô phỏng ổn định. Nếu robot không chạy, thử:
```bash
ros2 param set /motion_control safety_override full
```

**Terminal 2 – Nhận diện và điều khiển:**
```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 launch turtlebot4_gesture gesture_control.launch.py
```

Quy trình demo: giơ **1 ngón** (hoặc **2 ngón**) → giơ **ngón cái** để xác nhận → robot chạy.
**Xòe tay** để dừng, **nắm tay** để hủy.

## Kiểm tra

```bash
ros2 topic echo /detected_gesture
ros2 topic info /cmd_vel
```

## Lỗi thường gặp

| Lỗi | Cách xử lý |
|---|---|
| Không mở được webcam | Tắt chương trình khác đang dùng webcam, hoặc `--ros-args -p camera_index:=1` |
| Robot không chạy dù log báo `Bắt đầu` | Kiểm tra Gazebo không bị pause/chậm (`ros2 topic echo /clock`), đặt `safety_override` thành `full` |
| `/cmd_vel` là `TwistStamped` | Đổi kiểu message trong `robot_behavior_node.py` sang `TwistStamped` |
| Vòng tròn chạm tường | Giảm tốc độ tiến trong hành vi `circle` (hiện 0.1 m/s, bán kính 0.25 m) |

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
