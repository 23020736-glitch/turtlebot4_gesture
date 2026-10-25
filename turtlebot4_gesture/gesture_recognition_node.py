#!/usr/bin/env python3
"""gesture_recognition_node: webcam -> MediaPipe Gesture Recognizer -> /detected_gesture

Cử chỉ có sẵn trong model: Closed_Fist, Open_Palm, Pointing_Up, Thumb_Up,
Thumb_Down, Victory, ILoveYou. Model KHÔNG có "Wave", nên Wave được tạo ra bằng
cách phát hiện bàn tay xòe (Open_Palm) có cổ tay dao động ngang qua lại.

Chống nhiễu: một cử chỉ chỉ được publish khi (a) độ tin cậy >= min_confidence và
(b) giữ ổn định liên tiếp `stable_frames` frame.
"""
import collections
import os
import time
import urllib.request

import cv2
import mediapipe as mp
import rclpy
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision
from rclpy.node import Node
from std_msgs.msg import String

MODEL_URL = ('https://storage.googleapis.com/mediapipe-models/gesture_recognizer/'
             'gesture_recognizer/float16/1/gesture_recognizer.task')


class GestureRecognitionNode(Node):
    def __init__(self):
        super().__init__('gesture_recognition_node')
        self.declare_parameter('model_path', os.path.expanduser('~/gesture_recognizer.task'))
        self.declare_parameter('camera_index', 0)
        self.declare_parameter('min_confidence', 0.6)
        self.declare_parameter('stable_frames', 6)
        self.declare_parameter('publish_rate', 10.0)   # Hz, heartbeat cho watchdog
        self.declare_parameter('show_window', True)

        model_path = self.get_parameter('model_path').value
        if not os.path.exists(model_path):
            self.get_logger().info(f'Đang tải model về {model_path} ...')
            urllib.request.urlretrieve(MODEL_URL, model_path)

        options = vision.GestureRecognizerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=model_path),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=1)
        self.recognizer = vision.GestureRecognizer.create_from_options(options)

        self.cap = cv2.VideoCapture(self.get_parameter('camera_index').value)
        if not self.cap.isOpened():
            raise RuntimeError('Không mở được webcam (thử đổi camera_index)')

        self.min_conf = self.get_parameter('min_confidence').value
        self.stable_frames = self.get_parameter('stable_frames').value
        self.show = self.get_parameter('show_window').value

        self.pub = self.create_publisher(String, '/detected_gesture', 10)
        self.stable = 'None'
        self.candidate = 'None'
        self.cand_count = 0
        self.last_ts = 0
        self.wrist_hist = collections.deque()
        self.wave_until = 0.0

        self.create_timer(1.0 / 30.0, self.process_frame)
        self.create_timer(1.0 / self.get_parameter('publish_rate').value, self.publish_stable)
        self.get_logger().info('gesture_recognition_node sẵn sàng (nhấn q trong cửa sổ để đóng cửa sổ)')

    # ---- Wave: Open_Palm + cổ tay dao động ngang ----
    def _is_wave(self, thr=0.04, window=1.2):
        now = time.monotonic()
        while self.wrist_hist and now - self.wrist_hist[0][0] > window:
            self.wrist_hist.popleft()
        xs = [x for _, x in self.wrist_hist]
        if len(xs) < 8:
            return False
        ref, direction, reversals = xs[0], 0, 0
        for x in xs[1:]:
            d = x - ref
            if direction <= 0 and d > thr:
                reversals += direction == -1
                direction, ref = 1, x
            elif direction >= 0 and d < -thr:
                reversals += direction == 1
                direction, ref = -1, x
            elif (direction == 1 and x > ref) or (direction == -1 and x < ref):
                ref = x
        return reversals >= 2

    def process_frame(self):
        ok, frame = self.cap.read()
        if not ok:
            self.get_logger().warn('Không đọc được frame từ webcam', throttle_duration_sec=2.0)
            return
        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        ts = max(int(time.monotonic() * 1000), self.last_ts + 1)
        self.last_ts = ts
        result = self.recognizer.recognize_for_video(mp_image, ts)

        raw, conf = 'None', 0.0
        now = time.monotonic()
        if result.gestures and result.hand_landmarks:
            cat = result.gestures[0][0]
            conf = cat.score
            lm = result.hand_landmarks[0]
            h, w = frame.shape[:2]
            for p in lm:
                cv2.circle(frame, (int(p.x * w), int(p.y * h)), 3, (0, 255, 0), -1)
            if cat.category_name != 'None' and conf >= self.min_conf:
                raw = cat.category_name
            if raw == 'Open_Palm':
                self.wrist_hist.append((now, lm[0].x))
                if self._is_wave():
                    self.wave_until = now + 0.8
            else:
                self.wrist_hist.clear()
            if raw == 'Open_Palm' and now < self.wave_until:
                raw = 'Wave'
        else:
            self.wrist_hist.clear()

        # Debounce
        if raw == self.candidate:
            self.cand_count += 1
        else:
            self.candidate, self.cand_count = raw, 1
        if self.cand_count >= self.stable_frames and self.candidate != self.stable:
            self.stable = self.candidate
            self.get_logger().info(f'Cử chỉ ổn định: {self.stable}')

        if self.show:
            cv2.putText(frame, f'Raw: {raw} ({conf:.2f})', (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            cv2.putText(frame, f'Published: {self.stable}', (10, 65),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 0), 2)
            cv2.imshow('Gesture Recognition', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.show = False
                cv2.destroyAllWindows()

    def publish_stable(self):
        self.pub.publish(String(data=self.stable))

    def destroy_node(self):
        self.cap.release()
        cv2.destroyAllWindows()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = GestureRecognitionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
