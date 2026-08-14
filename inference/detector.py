"""
Vehicle + person detector.
Uses pretrained YOLOv8n (COCO classes) — no training required.

COCO classes we care about:
    0  person
    1  bicycle
    2  car
    3  motorcycle
    5  bus
    7  truck
"""
from pathlib import Path
from ultralytics import YOLO

COCO_CLASSES_OF_INTEREST = {
    0: "person",
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}


class VehicleDetector:
    def __init__(self, weights_path: str = "models/pretrained/yolov8n.pt", conf: float = 0.35):
        self.model = YOLO(weights_path)
        self.conf = conf

    def detect(self, frame):
        """
        Run detection on a single BGR frame (numpy array).
        Returns a list of dicts: {bbox: [x1,y1,x2,y2], cls_id, cls_name, conf}
        """
        results = self.model.predict(frame, conf=self.conf, verbose=False)[0]
        detections = []
        for box in results.boxes:
            cls_id = int(box.cls[0])
            if cls_id not in COCO_CLASSES_OF_INTEREST:
                continue
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            detections.append({
                "bbox": [x1, y1, x2, y2],
                "cls_id": cls_id,
                "cls_name": COCO_CLASSES_OF_INTEREST[cls_id],
                "conf": float(box.conf[0]),
            })
        return detections
