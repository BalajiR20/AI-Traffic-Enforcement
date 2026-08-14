"""
Speed estimation (Phase E — optional, build last).
Uses two virtual reference lines a known real-world distance apart.
When a tracked vehicle's center crosses each line, we record the frame
timestamp; speed = distance / time_between_crossings.

No model training needed — reuses the tracker's position history.
"""
import time


class SpeedEstimator:
    def __init__(self, line1_y: int, line2_y: int, real_world_distance_m: float,
                 speed_limit_kmh: float = 40.0):
        """
        line1_y, line2_y: pixel y-coordinates of two horizontal reference lines
            (assumes roughly top-down/oblique camera where vehicles cross
            horizontal lines as they travel — adjust to vertical lines if
            your camera angle needs it).
        real_world_distance_m: actual distance between the two lines in meters,
            measured on-site or estimated from camera calibration.
        """
        self.line1_y = line1_y
        self.line2_y = line2_y
        self.distance_m = real_world_distance_m
        self.speed_limit_kmh = speed_limit_kmh
        self.crossings = {}  # track_id -> {"line1": ts, "line2": ts}

    def update(self, track_id, bbox, frame_timestamp: float = None):
        if frame_timestamp is None:
            frame_timestamp = time.time()

        _, y1, _, y2 = bbox
        center_y = (y1 + y2) / 2
        rec = self.crossings.setdefault(track_id, {})

        if "line1" not in rec and abs(center_y - self.line1_y) < 8:
            rec["line1"] = frame_timestamp
        if "line2" not in rec and abs(center_y - self.line2_y) < 8:
            rec["line2"] = frame_timestamp

    def get_speed_kmh(self, track_id):
        rec = self.crossings.get(track_id)
        if not rec or "line1" not in rec or "line2" not in rec:
            return None
        dt = abs(rec["line2"] - rec["line1"])
        if dt <= 0:
            return None
        speed_mps = self.distance_m / dt
        return speed_mps * 3.6

    def is_overspeeding(self, track_id):
        speed = self.get_speed_kmh(track_id)
        if speed is None:
            return False, None
        return speed > self.speed_limit_kmh, speed
