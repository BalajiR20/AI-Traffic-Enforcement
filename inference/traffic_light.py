"""
Traffic light state detection.
No model training required — we crop a fixed ROI (configured per camera
in configs/camera.yaml) and classify the illuminated color via HSV analysis.
If the camera angle makes this unreliable, a small trained detector can be
swapped in later without changing the rest of the pipeline.
"""
import cv2
import numpy as np


class TrafficLightDetector:
    def __init__(self, roi: list):
        """
        roi: [x1, y1, x2, y2] pixel box around the traffic light head,
        pulled from configs/camera.yaml.
        """
        self.roi = roi

    def get_state(self, frame) -> str:
        """
        Returns one of: "RED", "YELLOW", "GREEN", "UNKNOWN"
        """
        x1, y1, x2, y2 = self.roi
        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            return "UNKNOWN"

        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)

        red_mask = cv2.inRange(hsv, (0, 100, 100), (10, 255, 255)) \
            + cv2.inRange(hsv, (160, 100, 100), (180, 255, 255))
        yellow_mask = cv2.inRange(hsv, (20, 100, 100), (35, 255, 255))
        green_mask = cv2.inRange(hsv, (40, 70, 70), (90, 255, 255))

        counts = {
            "RED": int(np.count_nonzero(red_mask)),
            "YELLOW": int(np.count_nonzero(yellow_mask)),
            "GREEN": int(np.count_nonzero(green_mask)),
        }
        best_state = max(counts, key=counts.get)
        if counts[best_state] < 20:  # not enough colored pixels to be confident
            return "UNKNOWN"
        return best_state
