"""
Loads configs/camera.yaml and configs/traffic_rules.yaml into plain dicts.
"""
from pathlib import Path
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIGS_DIR = PROJECT_ROOT / "configs"


def load_camera_config(path: str = None) -> dict:
    path = Path(path) if path else CONFIGS_DIR / "camera.yaml"
    with open(path) as f:
        return yaml.safe_load(f)


def load_rules_config(path: str = None) -> dict:
    path = Path(path) if path else CONFIGS_DIR / "traffic_rules.yaml"
    with open(path) as f:
        return yaml.safe_load(f)


def load_blacklist(path: str = None) -> set:
    path = Path(path) if path else CONFIGS_DIR / "blacklist.csv"
    plates = set()
    if not Path(path).exists():
        return plates
    with open(path) as f:
        next(f, None)  # skip header
        for line in f:
            plate = line.strip().split(",")[0]
            if plate:
                plates.add(plate.upper())
    return plates
