"""
Downloads pretrained yolov8n.pt into models/pretrained/.
Run once before anything else:
    python download_pretrained.py
"""
from pathlib import Path
from ultralytics import YOLO

TARGET = Path(__file__).resolve().parent / "models" / "pretrained" / "yolov8n.pt"
TARGET.parent.mkdir(parents=True, exist_ok=True)

if TARGET.exists():
    print(f"[OK] Already present: {TARGET}")
else:
    print("[INFO] Downloading yolov8n.pt ...")
    model = YOLO("yolov8n.pt")     # Ultralytics downloads this to the current working dir
    cwd_copy = Path.cwd() / "yolov8n.pt"
    if cwd_copy.exists() and cwd_copy != TARGET:
        cwd_copy.replace(TARGET)   # move it into models/pretrained/ instead of leaving it in root
    else:
        model.save(str(TARGET))
    print(f"[OK] Saved to {TARGET}")
