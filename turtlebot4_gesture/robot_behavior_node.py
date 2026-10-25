import time
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from geometry_msgs.msg import Twist

COOLDOWN = 1.0          # giây giữa 2 lệnh (chống nhiễu)
SIGNAL_TIMEOUT = 2.0    # giây không có tín hiệu thì dừng robot


class RobotBehaviorNode(Node):
    def __init__(self):
        super().__init__('robot_behavior_node')
        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.create_subscription(String, '/detected_gesture', self.gesture_cb, 10)
        self.create_timer(0.05, self.control_loop)   # 20 Hz

        self.selected = None          # hành vi đã chọn, chờ xác nhận
        self.running = False
        self.current = None           # tên hành vi đang chạy
        self.segments = []            # (linear, angular, thời gian)
        self.idx = 0
        self.seg_end = 0.0
        self.last_gesture = 'None'    # để chỉ xử lý khi cử chỉ THAY ĐỔI
        self.last_cmd_time = 0.0
        self.last_msg_time = time.monotonic()

    # ---------- gửi vận tốc ----------
    def send(self, lin, ang):
        msg = Twist()
        msg.linear.x = float(lin)
        msg.angular.z = float(ang)
        self.pub.publish(msg)

    def stop(self):
        self.running = False
        self.segments = []
        for _ in range(3):
            self.send(0.0, 0.0)

    # ---------- các hành vi ----------
    def build(self, name):
        if name == 'wave':              # xoay trái - phải - về giữa
            return [(0, 0.8, 0.8), (0, -0.8, 1.6), (0, 0.8, 0.8)]
        if name == 'forward_backward':  # 4 lần, mỗi chiều ~0.3 m
            return [(0.15, 0, 2.0), (0, 0, 0.3), (-0.15, 0, 2.0), (0, 0, 0.3)] * 4
        if name == 'circle':            # bán kính 0.25 m, 1 vòng
            return [(0.1, 0.4, 15.7)]
        return []

    def start(self, name):
        self.segments = self.build(name)
        self.idx = 0
        self.seg_end = time.monotonic() + self.segments[0][2]
        self.running = True
        self.current = name
        self.last_cmd_time = time.monotonic()
        self.get_logger().info(f'Bắt đầu: {name}')

    # ---------- nhận cử chỉ ----------
    def gesture_cb(self, msg):
        self.last_msg_time = time.monotonic()
        g = msg.data

        # Chống nhiễu 1: chỉ xử lý khi cử chỉ thay đổi
        if g == self.last_gesture:
            return
        self.last_gesture = g

        # Dừng / hủy: luôn có hiệu lực ngay, bỏ qua cooldown
        if g == 'Open_Palm':
            # Đang chào (Wave) thì bỏ qua: tay vẫy cũng là bàn tay xòe
            if self.running and self.current == 'wave':
                return
            self.stop()
            self.selected = None
            self.get_logger().info('DỪNG NGAY (Open_Palm)')
            return
        if g == 'Closed_Fist':
            self.stop()
            self.selected = None
            self.get_logger().info('HỦY -> TRẠNG THÁI CHỜ (Closed_Fist)')
            return

        if g in ('None', ''):
            return
        if self.running:
            self.get_logger().info(f'Bỏ qua {g}: robot đang chạy')
            return

        # Chống nhiễu 2: cooldown giữa các lệnh
        if time.monotonic() - self.last_cmd_time < COOLDOWN:
            self.get_logger().info(f'Bỏ qua {g} (cooldown)')
            return

        if g == 'Wave':
            self.start('wave')
        elif g == 'Pointing_Up':
            self.selected = 'forward_backward'
            self.last_cmd_time = time.monotonic()
            self.get_logger().info('Đã chọn: tiến-lùi 4 lần. Giơ ngón cái để xác nhận')
        elif g == 'Victory':
            self.selected = 'circle'
            self.last_cmd_time = time.monotonic()
            self.get_logger().info('Đã chọn: quỹ đạo tròn. Giơ ngón cái để xác nhận')
        elif g == 'Thumb_Up':           # xác nhận
            if self.selected is None:
                self.get_logger().warn('Chưa chọn hành vi')
            else:
                self.start(self.selected)
                self.selected = None

    # ---------- vòng điều khiển ----------
    def control_loop(self):
        if not self.running:
            return
        now = time.monotonic()

        # Mất tín hiệu điều khiển -> dừng
        if now - self.last_msg_time > SIGNAL_TIMEOUT:
            self.get_logger().warn('Mất tín hiệu cử chỉ -> DỪNG')
            self.stop()
            self.selected = None
            return

        if now >= self.seg_end:
            self.idx += 1
            if self.idx >= len(self.segments):
                self.stop()
                self.get_logger().info('Hoàn thành hành vi')
                return
            self.seg_end = now + self.segments[self.idx][2]
        lin, ang, _ = self.segments[self.idx]
        self.send(lin, ang)


def main(args=None):
    rclpy.init(args=args)
    node = RobotBehaviorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.stop()
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
