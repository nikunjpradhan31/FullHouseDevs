import pathlib

from ultralytics import YOLO


model_path = "./cv_models/yolo26n.onnx"

# Load the YOLO26 Nano model, optimized for speed and real-time tasks
model = YOLO(model_path)

# Local path to recorded video
path = pathlib.Path(r"C:\Users\alexd\OneDrive\Pictures\Camera Roll\WIN_20260312_22_04_50_Pro.mp4")

# Run inference on the default webcam (source="0")
# 'stream=True' returns a generator for memory-efficient processing
# 'show=True' displays the video feed with bounding boxes in real-time
results = model.predict(source="0", stream=True, show=True)

# Iterate through the generator to process frames as they arrive
for result in results:
    # Example: Print the number of objects detected in the current frame
    print(result.boxes.xywh)
