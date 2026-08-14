"""
Vehicle tracking using ByteTrack (built into Ultralytics).

This replaces plain detection once you move past Phase A Step 1 —
it gives every vehicle a stable ID across frames, which is required
before you can link a violation to a specific plate.
"""
from ultralytics import YOLO
from inference.detector import COCO_CLASSES_OF_INTEREST


class VehicleTracker:
    def __init__(self, weights_path: str = "models/pretrained/yolov8n.pt", conf: float = 0.35):
        self.model = YOLO(weights_path)
        self.conf = conf

    def track(self, frame):
        """
        Run detection + ByteTrack tracking on a single BGR frame.
        Returns a list of dicts: {track_id, bbox, cls_id, cls_name, conf}
        track_id is None for detections that haven't been assigned an ID yet.
        """
        results = self.model.track(
            frame,
            conf=self.conf,
            persist=True,          # keep track state across calls
            tracker="bytetrack.yaml",
            verbose=False,
        )[0]

        tracked = []
        if results.boxes is None or results.boxes.id is None:
            return tracked

        ids = results.boxes.id.int().tolist()
        for box, track_id in zip(results.boxes, ids):
            cls_id = int(box.cls[0])
            if cls_id not in COCO_CLASSES_OF_INTEREST:
                continue
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            tracked.append({
                "track_id": track_id,
                "bbox": [x1, y1, x2, y2],
                "cls_id": cls_id,
                "cls_name": COCO_CLASSES_OF_INTEREST[cls_id],
                "conf": float(box.conf[0]),
            })
        return tracked
