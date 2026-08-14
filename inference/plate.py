"""
License plate detection — uses the fine-tuned model at models/license_plate/best.pt.
Only invoked when a violation has already been flagged (event-driven),
never on every frame — this is the single biggest cost saver in the pipeline.
"""
from ultralytics import YOLO


class PlateDetector:
    def __init__(self, weights_path: str = "models/license_plate/best.pt", conf: float = 0.4):
        self.model = YOLO(weights_path)
        self.conf = conf

    def detect_plate_crop(self, vehicle_crop):
        """
        Given a cropped vehicle image, find the license plate and return
        the cropped plate image (numpy array) or None if not found.
        """
        results = self.model.predict(vehicle_crop, conf=self.conf, verbose=False)[0]
        if len(results.boxes) == 0:
            return None

        # Take the highest-confidence plate box
        best_box = max(results.boxes, key=lambda b: float(b.conf[0]))
        x1, y1, x2, y2 = [int(v) for v in best_box.xyxy[0].tolist()]
        x1, y1 = max(0, x1), max(0, y1)
        plate_crop = vehicle_crop[y1:y2, x1:x2]
        if plate_crop.size == 0:
            return None
        return plate_crop
