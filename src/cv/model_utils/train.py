"""
Performs training with the specified pretrained model and dataset yaml configuration file.
"""
from ultralytics import YOLO

from src.config import \
    DATA_DIR, \
    MODELS_DIR, \
    RUNS_DIR


DATASET_NAME = 'synthetic_dataset'

DATASET_CONFIG_PATH = DATA_DIR / DATASET_NAME / "data.yaml"
MODEL = "yolov8n.pt"


if __name__ == "__main__":
    model = YOLO("yolov8n.pt")

    # Optimized CPU Training Parameters
    model.train(
        data=DATASET_CONFIG_PATH,
        epochs=10,
        device="cpu",      # Explicitly tell it not to look for a GPU
        imgsz=320,         # CRITICAL: Shrinks the training images by 75%, drastically reducing math
        workers=8,         # Utilizes your i7's multiple threads for loading data faster
        cache=True,        # Loads all images into your RAM so the CPU doesn't wait on your hard drive
        batch=8,            # Smaller batches prevent your CPU cache from overflowing
        save_dir=RUNS_DIR / MODEL 
    )