"""
Helmet detection — uses the fine-tuned model at models/helmet/best.pt.
Only called on cropped motorcycle+rider regions, not the full frame,
to keep this cheap (event-driven, not run every frame on everything).
"""
from ultralytics import YOLO

HELMET_CLASSES = {
    0: "motorcycle",
    1: "rider",
    2: "helmet",
    3: "no_helmet",
}


class HelmetDetector:
    def __init__(self, weights_path: str = "models/helmet/best.pt", conf: float = 0.4):
        self.model = YOLO(weights_path)
        self.conf = conf

    def check(self, cropped_frame):
        """
        Run helmet detection on a cropped motorcycle region.
        Returns True if a no_helmet violation is found, else False,
        plus the raw detections for evidence/debugging.
        """
        results = self.model.predict(cropped_frame, conf=self.conf, verbose=False)[0]
        detections = []
        violation = False
        for box in results.boxes:
            cls_id = int(box.cls[0])
            cls_name = HELMET_CLASSES.get(cls_id, "unknown")
            detections.append({
                "cls_name": cls_name,
                "conf": float(box.conf[0]),
                "bbox": box.xyxy[0].tolist(),
            })
            if cls_name == "no_helmet":
                violation = True
        return violation, detections
