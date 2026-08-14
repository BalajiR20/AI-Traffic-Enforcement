"""
Evidence generation: saves the violation frame/crop to disk,
computes a SHA-256 hash of the saved file (tamper-evidence),
and builds the JSON record sent to the backend.
"""
import hashlib
import json
import uuid
from datetime import datetime
from pathlib import Path

import cv2

EVIDENCE_DIR = Path(__file__).resolve().parents[1] / "evidence" / "images"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)


def _sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def generate_evidence(frame, violation_type: str, plate_number: str,
                       confidence: float, camera_id: str, location: str) -> dict:
    """
    Saves the evidence image and returns the full violation record dict,
    ready to POST to the backend /violations endpoint.
    """
    case_id = f"TV-{uuid.uuid4().hex[:8].upper()}"
    timestamp = datetime.now().isoformat(timespec="seconds")

    filename = f"{case_id}.jpg"
    filepath = EVIDENCE_DIR / filename
    cv2.imwrite(str(filepath), frame)

    evidence_hash = _sha256_of_file(filepath)

    record = {
        "case_id": case_id,
        "vehicle_number": plate_number or "UNREADABLE",
        "violation_type": violation_type,
        "timestamp": timestamp,
        "location": location,
        "camera_id": camera_id,
        "confidence": round(confidence, 4),
        "evidence_image_path": str(filepath),
        "evidence_hash": evidence_hash,
        "status": "pending",
    }
    return record


def save_record_json(record: dict):
    """Optional local backup of the record, independent of the backend DB."""
    out = EVIDENCE_DIR.parent / f"{record['case_id']}.json"
    with open(out, "w") as f:
        json.dump(record, f, indent=2)
