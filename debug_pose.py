"""Debug pose detection"""

import cv2
from src.detector import BabyWatcher

# Initialize
detector = BabyWatcher("config.yaml")

# Test pose detection
image_path = "images/a1.jpg"
frame = cv2.imread(image_path)

print(f"Testing pose detection on {image_path}...")
print(f"Frame shape: {frame.shape}")

# Run pose detection
import torch
pose_results = detector.pose_model.predict(
    frame,
    imgsz=detector.img_size,
    conf=detector.conf_thresh,
    max_det=detector.max_det,
    verbose=False
)[0]

print(f"Pose results: {pose_results}")
print(f"Has keypoints: {pose_results.keypoints is not None}")

if pose_results.keypoints is not None:
    kpts = pose_results.keypoints.xy.cpu().numpy()
    print(f"Number of detected persons: {len(kpts)}")
    if len(kpts) > 0:
        print(f"Keypoints shape: {kpts[0].shape}")
        print(f"First person keypoints:\n{kpts[0]}")
