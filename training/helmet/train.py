"""
Fine-tune YOLOv8n on the helmet-violation dataset.

Usage:
    python train.py --epochs 60 --imgsz 640 --batch 16

Before running:
    1. Populate datasets/helmet/{train,val,test}/{images,labels}
       with images + YOLO-format .txt labels.
    2. Make sure models/pretrained/yolov8n.pt exists
       (downloads automatically on first run if missing).
"""
import argparse
from pathlib import Path
from ultralytics import YOLO

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=60)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--data", type=str, default=str(THIS_DIR / "data.yaml"))
    parser.add_argument(
        "--weights",
        type=str,
        default=str(PROJECT_ROOT / "models" / "pretrained" / "yolov8n.pt"),
        help="Starting weights (pretrained COCO YOLOv8n). Never train from scratch.",
    )
    args = parser.parse_args()

    model = YOLO(args.weights)

    results = model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        project=str(PROJECT_ROOT / "models" / "helmet"),
        name="run",
        exist_ok=True,
        patience=15,          # early stop if val doesn't improve
        val=True,
    )

    # Copy best weights to the expected inference location
    best = Path(results.save_dir) / "weights" / "best.pt"
    target = PROJECT_ROOT / "models" / "helmet" / "best.pt"
    if best.exists():
        target.write_bytes(best.read_bytes())
        print(f"[OK] Best helmet model copied to {target}")
    else:
        print("[WARN] best.pt not found — check training logs above.")


if __name__ == "__main__":
    main()
