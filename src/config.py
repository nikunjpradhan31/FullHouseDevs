from pathlib import Path

SRC_DIR = Path(__file__).parent.resolve()

ROOT_DIR = SRC_DIR.parent

MODELS_DIR = ROOT_DIR / "models"
DATA_DIR = ROOT_DIR / "data"
RUNS_DIR = ROOT_DIR / "runs"

YOLO_WEIGHTS_PATH = MODELS_DIR / "yolo_v8_cards.pt"
