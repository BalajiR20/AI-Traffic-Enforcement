# AI-Powered Traffic Violation Detection & Enforcement System

Detects **No Helmet**, **Red Light**, **Wrong Way**, and **Triple Riding** violations
from traffic video/webcam, reads number plates via OCR, generates tamper-evident
evidence, and sends cases to a police review portal (Approve/Reject).

Optional Phase E: **Speed estimation** + **in-dashboard camera calibration tool**.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Vehicle/person detection | YOLOv8n (Ultralytics, pretrained on COCO) |
| Tracking | ByteTrack (built into Ultralytics) |
| Helmet detection | YOLOv8n fine-tuned on AI City Challenge Track 5 |
| Plate detection | YOLOv8n fine-tuned on Indian Licence Plate Dataset |
| OCR | PaddleOCR (pretrained) |
| Red-light / wrong-way / triple-riding | OpenCV + geometry (no model) |
| Backend | FastAPI + SQLAlchemy + SQLite |
| Dashboard | Plain HTML/CSS/JS (no build step) |
| Evidence integrity | SHA-256 hashing |

---

## 1. Prerequisites

- Python 3.10+
- A webcam or a traffic video file (.mp4)
- ~5 GB free disk for models + datasets

## 2. Setup

```bash
cd AI-Traffic-Enforcement

# create environment
conda create -n traffic-ai python=3.10 -y
conda activate traffic-ai

# install dependencies
pip install -r requirements.txt

# download pretrained YOLOv8n (one-time)
python download_pretrained.py
```

## 3. Get the datasets (only needed for training helmet/plate models)

- **Helmet:** AI City Challenge 2024 — Track 5 (helmet violation detection).
  Place images/labels into `datasets/helmet/{train,val,test}/{images,labels}`.
- **License plate:** Indian Licence Plate Dataset in the Wild.
  Place images/labels into `datasets/license_plate/{train,val,test}/{images,labels}`.
- **Your own test videos:** record 5–10 short clips of real traffic and drop
  them into `datasets/my_test_videos/` — used for evaluation, never training.

Label format is standard YOLO `.txt` (class x_center y_center width height, normalized).

## 4. Train the two custom models

```bash
# Helmet detector
cd training/helmet
python train.py --epochs 60

# License plate detector
cd ../license_plate
python train.py --epochs 60
```
Each script copies the best checkpoint to `models/helmet/best.pt` and
`models/license_plate/best.pt` automatically — the pipeline expects them there.

> Until these finish training, `pipeline/main.py` will still run for
> vehicle detection/tracking/red-light/wrong-way/triple-riding — it will just
> fail gracefully on helmet/plate steps (add a try/except around those calls
> during early testing, or run a very short training pass first to get a
> placeholder `best.pt`).

## 5. Calibrate your camera

Edit `configs/camera.yaml`:
- `traffic_light_roi` — pixel box around the traffic light
- `stop_line` — y-coordinate + x-range of the virtual stop line
- `allowed_direction_deg` — the legal direction of travel
- (Phase E) `speed_line_1_y` / `speed_line_2_y` / `speed_reference_distance_m`

Easiest way to find pixel coordinates: open one video frame in any image
viewer/editor and read off the pixel positions with the cursor.

## 6. Run the backend

```bash
# from project root
uvicorn backend.main:app --reload --port 8000
```
API docs: http://127.0.0.1:8000/docs

## 7. Run the dashboard

No build step needed — just open the file, or serve it:
```bash
cd dashboard/traffic-portal
python -m http.server 5500
```
Then open http://127.0.0.1:5500 in your browser.

## 8. Run the detection pipeline

```bash
# from project root, with backend already running
python pipeline/main.py --source datasets/my_test_videos/junction_day.mp4

# or use your laptop webcam
python pipeline/main.py --source 0
```
Press `q` to quit the live preview window. Detected violations appear in the
dashboard within ~10 seconds (auto-refresh).

If the backend isn't running, violation records are still saved locally as
JSON files in `evidence/` so nothing is lost.

---

## Project Structure

```
AI-Traffic-Enforcement/
├── datasets/            # helmet, license_plate, my_test_videos
├── models/               # pretrained + fine-tuned weights
├── training/              # train.py + data.yaml per model
├── inference/            # detector, tracker, helmet, plate, ocr,
│                          # traffic_light, wrong_way, triple_riding,
│                          # speed, violations (rule engine)
├── pipeline/             # main.py (entry point), config.py
├── evidence/              # hashing.py, saved images/JSON
├── backend/               # FastAPI app, models, schemas, routes
├── dashboard/traffic-portal/  # HTML/CSS/JS police review portal
├── configs/               # camera.yaml, traffic_rules.yaml, blacklist.csv
├── requirements.txt
└── download_pretrained.py
```

## Build Order (recommended)

1. `download_pretrained.py` → confirm YOLOv8n detects vehicles on your webcam
2. Add ByteTrack (already wired in `inference/tracker.py`) → confirm stable IDs
3. Train helmet model → integrate
4. Wire red-light + wrong-way rules → calibrate `camera.yaml`
5. Train plate model → integrate + PaddleOCR
6. Triple-riding (already wired, no training needed)
7. Evidence hashing (already wired)
8. Backend + dashboard (already wired) → Approve/Reject flow
9. Rejection-reason feedback loop + analytics tab (already wired)
10. *(Optional, time permitting)* Speed estimation, in-dashboard calibration tool

## Notes on Accuracy

- OCR on Indian plates typically lands around 70–85% out of the box —
  that's expected, not a bug. This is exactly why the Approve/Reject portal
  exists: **AI-assisted, human-verified**, not fully autonomous.
- Violations require 5 consecutive confirming frames (`confirm_frames` in
  `configs/traffic_rules.yaml`) before evidence is generated — this filters
  out one-off false detections and ByteTrack ID switches.
