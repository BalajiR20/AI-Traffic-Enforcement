"""
Triple-riding detection.
Reuses the existing person detections from detector/tracker — no new model.
Counts how many person-box centers fall inside a motorcycle's bounding box.
"""


def _center(bbox):
    x1, y1, x2, y2 = bbox
    return (x1 + x2) / 2, (y1 + y2) / 2


def _inside(point, bbox):
    x, y = point
    x1, y1, x2, y2 = bbox
    return x1 <= x <= x2 and y1 <= y <= y2


def count_riders(motorcycle_bbox, all_detections, max_allowed: int = 2):
    """
    motorcycle_bbox: [x1, y1, x2, y2] of one motorcycle
    all_detections: full list of detections for the frame (from detector/tracker)
    Returns (rider_count, is_violation)
    """
    rider_count = 0
    for det in all_detections:
        if det["cls_name"] != "person":
            continue
        if _inside(_center(det["bbox"]), motorcycle_bbox):
            rider_count += 1

    return rider_count, rider_count > max_allowed
