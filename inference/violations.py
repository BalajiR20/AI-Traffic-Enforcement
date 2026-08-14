"""
Violation rule engine.
Combines detector+tracker output with the individual rule modules
(helmet, red-light, wrong-way, triple-riding, speed) and decides
when something becomes a confirmed VIOLATION worth generating evidence for.

Key design choice: a violation must be seen for N consecutive frames
before it's confirmed. This directly mitigates ByteTrack ID switches
and one-off false detections — cheap insurance, real impact.
"""
from collections import defaultdict


class ViolationEngine:
    def __init__(self, confirm_frames: int = 5, max_riders: int = 2):
        self.confirm_frames = confirm_frames
        self.max_riders = max_riders
        # track_id -> violation_type -> consecutive frame count
        self._streak = defaultdict(lambda: defaultdict(int))
        # track_id -> set of violation types already confirmed & sent
        self._already_reported = defaultdict(set)

    def _confirm(self, track_id, violation_type) -> bool:
        """Increment streak; return True only on the exact frame it crosses the threshold."""
        self._streak[track_id][violation_type] += 1
        if violation_type in self._already_reported[track_id]:
            return False
        if self._streak[track_id][violation_type] >= self.confirm_frames:
            self._already_reported[track_id].add(violation_type)
            return True
        return False

    def reset_if_absent(self, track_id, violation_type):
        """Call when a check is NOT triggered this frame, to decay the streak."""
        if self._streak[track_id][violation_type] > 0:
            self._streak[track_id][violation_type] = max(
                0, self._streak[track_id][violation_type] - 1
            )

    def check_helmet(self, track_id, no_helmet_flag: bool):
        if no_helmet_flag:
            return self._confirm(track_id, "NO_HELMET")
        self.reset_if_absent(track_id, "NO_HELMET")
        return False

    def check_red_light(self, track_id, light_state: str, crossed_stop_line: bool):
        if light_state == "RED" and crossed_stop_line:
            return self._confirm(track_id, "RED_LIGHT")
        self.reset_if_absent(track_id, "RED_LIGHT")
        return False

    def check_wrong_way(self, track_id, is_wrong_way: bool):
        if is_wrong_way:
            return self._confirm(track_id, "WRONG_WAY")
        self.reset_if_absent(track_id, "WRONG_WAY")
        return False

    def check_triple_riding(self, track_id, rider_count: int):
        if rider_count > self.max_riders:
            return self._confirm(track_id, "TRIPLE_RIDING")
        self.reset_if_absent(track_id, "TRIPLE_RIDING")
        return False

    def check_overspeeding(self, track_id, is_overspeeding: bool):
        if is_overspeeding:
            return self._confirm(track_id, "OVERSPEEDING")
        self.reset_if_absent(track_id, "OVERSPEEDING")
        return False
