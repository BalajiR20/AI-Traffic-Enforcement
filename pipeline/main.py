"""
Main pipeline entry point.

Usage:
    python pipeline/main.py --source datasets/my_test_videos/junction_day.mp4
    python pipeline/main.py --source 0        # laptop webcam

Run from the project root (AI-Traffic-Enforcement/) so relative model/config
paths resolve correctly.
"""
import argparse
import sys
import time
from pathlib import Path

import cv2
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from inference.tracker import VehicleTracker
from inference.helmet import HelmetDetector
from inference.plate import PlateDetector
from inference.ocr import PlateOCR
from inference.traffic_light import TrafficLightDetector
from inference.wrong_way import WrongWayDetector
from inference.triple_riding import count_riders
from inference.violations import ViolationEngine
from evidence.hashing import generate_evidence, save_record_json
from pipeline.config import load_camera_config, load_rules_config, load_blacklist

BACKEND_URL = "http://127.0.0.1:8000/violations"

COLORS = {
    "NO_HELMET": (0, 0, 255),
    "RED_LIGHT": (0, 140, 255),
    "WRONG_WAY": (255, 0, 255),
    "TRIPLE_RIDING": (0, 255, 255),
    "OK": (0, 255, 0),
}


def crop(frame, bbox, pad=0):
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = [int(v) for v in bbox]
    x1, y1 = max(0, x1 - pad), max(0, y1 - pad)
    x2, y2 = min(w, x2 + pad), min(h, y2 + pad)
    return frame[y1:y2, x1:x2]


def send_to_backend(record: dict):
    try:
        requests.post(BACKEND_URL, json=record, timeout=1.5)
    except requests.exceptions.RequestException:
        # Backend not running — fall back to local JSON so nothing is lost.
        save_record_json(record)


def make_optional_detector(weights_path: Path, detector_factory, conf: float):
    if not weights_path.exists():
        print(f"[WARN] Missing model: {weights_path}. Skipping detector initialization.")
        return None
    return detector_factory(weights_path=str(weights_path), conf=conf)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=str, default="0",
                         help="Video file path, or '0' for webcam")
    parser.add_argument("--no-display", action="store_true",
                         help="Run headless (no cv2.imshow window)")
    args = parser.parse_args()

    source = 0 if args.source == "0" else args.source

    cam_cfg = load_camera_config()
    rules_cfg = load_rules_config()
    blacklist = load_blacklist()

    tracker = VehicleTracker(
        weights_path=str(PROJECT_ROOT / "models" / "pretrained" / "yolov8n.pt"),
        conf=rules_cfg["detection_conf_threshold"],
    )
    helmet_detector = make_optional_detector(
        PROJECT_ROOT / "models" / "helmet" / "best.pt",
        HelmetDetector,
        rules_cfg["helmet_conf_threshold"],
    )
    plate_detector = make_optional_detector(
        PROJECT_ROOT / "models" / "license_plate" / "best.pt",
        PlateDetector,
        rules_cfg["plate_conf_threshold"],
    )
    ocr = PlateOCR() if (PROJECT_ROOT / "models" / "license_plate" / "best.pt").exists() else None
    light_detector = TrafficLightDetector(roi=cam_cfg["traffic_light_roi"])
    wrong_way_detector = WrongWayDetector(
        allowed_direction_deg=cam_cfg["allowed_direction_deg"],
        angle_tolerance_deg=cam_cfg["wrong_way_angle_tolerance_deg"],
    )
    engine = ViolationEngine(
        confirm_frames=rules_cfg["confirm_frames"],
        max_riders=rules_cfg["max_riders_allowed"],
    )

    stop_line_y = cam_cfg["stop_line"]["y"]
    prev_center_y = {}  # track_id -> last frame's center y, for stop-line crossing

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"[ERROR] Could not open video source: {source}")
        return

    print("[INFO] Pipeline running. Press 'q' to quit.")
    frame_count = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            print("[INFO] End of video / camera stream.")
            break
        frame_count += 1

        tracked_objects = tracker.track(frame)
        light_state = light_detector.get_state(frame)

        motorcycles = [d for d in tracked_objects if d["cls_name"] == "motorcycle"]

        for obj in tracked_objects:
            track_id = obj["track_id"]
            bbox = obj["bbox"]
            x1, y1, x2, y2 = [int(v) for v in bbox]
            center_y = (y1 + y2) / 2

            box_color = COLORS["OK"]
            label = f"{obj['cls_name']} #{track_id}"

            # ---- Wrong-way (applies to any vehicle) ----
            wrong_way_detector.update(track_id, bbox)
            is_wrong = wrong_way_detector.is_wrong_way(track_id)
            if engine.check_wrong_way(track_id, is_wrong):
                box_color = COLORS["WRONG_WAY"]
                vehicle_crop = crop(frame, bbox, pad=10)
                plate_crop = plate_detector.detect_plate_crop(vehicle_crop)
                plate_text, plate_conf = ("", 0.0)
                if plate_crop is not None:
                    plate_text, plate_conf = ocr.read_plate(plate_crop)
                record = generate_evidence(
                    frame, "WRONG_WAY", plate_text, plate_conf,
                    cam_cfg["camera_id"], cam_cfg["location"],
                )
                if plate_text.upper() in blacklist:
                    record["blacklist_alert"] = True
                send_to_backend(record)
                print(f"[VIOLATION] WRONG_WAY track#{track_id} plate={plate_text or 'UNREADABLE'}")

            # ---- Red light (stop-line crossing while red) ----
            prev_y = prev_center_y.get(track_id)
            crossed = prev_y is not None and prev_y < stop_line_y <= center_y
            prev_center_y[track_id] = center_y
            if engine.check_red_light(track_id, light_state, crossed):
                box_color = COLORS["RED_LIGHT"]
                vehicle_crop = crop(frame, bbox, pad=10)
                plate_crop = plate_detector.detect_plate_crop(vehicle_crop)
                plate_text, plate_conf = ("", 0.0)
                if plate_crop is not None:
                    plate_text, plate_conf = ocr.read_plate(plate_crop)
                record = generate_evidence(
                    frame, "RED_LIGHT", plate_text, plate_conf,
                    cam_cfg["camera_id"], cam_cfg["location"],
                )
                if plate_text.upper() in blacklist:
                    record["blacklist_alert"] = True
                send_to_backend(record)
                print(f"[VIOLATION] RED_LIGHT track#{track_id} plate={plate_text or 'UNREADABLE'}")

            # ---- Helmet + triple-riding (motorcycles only) ----
            if obj["cls_name"] == "motorcycle":
                rider_count, triple_violation = count_riders(
                    bbox, tracked_objects, max_allowed=rules_cfg["max_riders_allowed"]
                )
                if engine.check_triple_riding(track_id, rider_count):
                    box_color = COLORS["TRIPLE_RIDING"]
                    record = generate_evidence(
                        frame, "TRIPLE_RIDING", "", 0.0,
                        cam_cfg["camera_id"], cam_cfg["location"],
                    )
                    send_to_backend(record)
                    print(f"[VIOLATION] TRIPLE_RIDING track#{track_id} riders={rider_count}")

                if helmet_detector is not None:
                    moto_crop = crop(frame, bbox, pad=15)
                    if moto_crop.size > 0:
                        no_helmet, _ = helmet_detector.check(moto_crop)
                        if engine.check_helmet(track_id, no_helmet):
                            box_color = COLORS["NO_HELMET"]
                            vehicle_crop = crop(frame, bbox, pad=10)
                            if plate_detector is not None:
                                plate_crop = plate_detector.detect_plate_crop(vehicle_crop)
                                plate_text, plate_conf = ("", 0.0)
                                if plate_crop is not None and ocr is not None:
                                    plate_text, plate_conf = ocr.read_plate(plate_crop)
                            else:
                                plate_text, plate_conf = ("", 0.0)
                            record = generate_evidence(
                                frame, "NO_HELMET", plate_text, plate_conf,
                                cam_cfg["camera_id"], cam_cfg["location"],
                            )
                            if plate_text.upper() in blacklist:
                                record["blacklist_alert"] = True
                            send_to_backend(record)
                            print(f"[VIOLATION] NO_HELMET track#{track_id} plate={plate_text or 'UNREADABLE'}")

            cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
            cv2.putText(frame, label, (x1, max(0, y1 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 2)

        # Draw stop line + light state for visual debugging
        cv2.line(frame, (cam_cfg["stop_line"]["x_start"], stop_line_y),
                  (cam_cfg["stop_line"]["x_end"], stop_line_y), (255, 255, 0), 2)
        cv2.putText(frame, f"Light: {light_state}", (20, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        if not args.no_display:
            cv2.imshow("Traffic Violation Detection", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cap.release()
    cv2.destroyAllWindows()
    print(f"[INFO] Processed {frame_count} frames.")


if __name__ == "__main__":
    main()
