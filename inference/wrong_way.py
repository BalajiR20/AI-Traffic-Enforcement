"""
Wrong-way driving detection.
Pure geometry — no model training required.

We track each vehicle's center-point history and compare its overall
movement vector against the allowed direction defined in configs/camera.yaml.
"""
import math


class WrongWayDetector:
    def __init__(self, allowed_direction_deg: float, angle_tolerance_deg: float = 60.0,
                 min_track_points: int = 8):
        """
        allowed_direction_deg: 0 = right, 90 = down, 180 = left, 270 = up
            (standard image coordinate convention)
        angle_tolerance_deg: how far off "allowed" before it counts as wrong-way
        min_track_points: minimum position history needed before judging
        """
        self.allowed_direction = allowed_direction_deg
        self.tolerance = angle_tolerance_deg
        self.min_points = min_track_points
        self.history = {}  # track_id -> list of (x, y)

    def update(self, track_id, bbox):
        x1, y1, x2, y2 = bbox
        center = ((x1 + x2) / 2, (y1 + y2) / 2)
        self.history.setdefault(track_id, []).append(center)
        # keep last 20 points only
        if len(self.history[track_id]) > 20:
            self.history[track_id] = self.history[track_id][-20:]

    def is_wrong_way(self, track_id) -> bool:
        points = self.history.get(track_id, [])
        if len(points) < self.min_points:
            return False

        start, end = points[0], points[-1]
        dx, dy = end[0] - start[0], end[1] - start[1]
        distance = math.hypot(dx, dy)
        if distance < 15:  # not enough movement to judge direction reliably
            return False

        movement_angle = math.degrees(math.atan2(dy, dx)) % 360
        diff = abs(movement_angle - self.allowed_direction) % 360
        diff = min(diff, 360 - diff)

        return diff > (180 - self.tolerance)
