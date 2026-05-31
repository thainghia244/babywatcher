#!/usr/bin/env python3
"""
Object Detection Tester with Adjustable Confidence
Reads defaults from config.yaml and allows CLI overrides
"""

import cv2
import argparse
from ultralytics import YOLO
import numpy as np
import time
from src.config import Config


class ObjectDetectionTester:
    def __init__(self, config_path='config.yaml'):
        print("Loading YOLO object detection model...")
        self.config = Config(config_path)
        self.default_conf = float(self.config.get('detection.conf_thresh', 0.25))
        self.default_small_conf = float(self.config.get('detection.small_object_conf_thresh', 0.15))
        model_path = self.config.get('models.object_model_path', 'yolo26n.pt')
        self.model = YOLO(model_path)
        self.model.conf = self.default_conf

    def run_test_camera(self, camera_index=0, duration=None):
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            print(f"❌ Cannot open camera {camera_index}")
            return

        print(f"✅ Camera opened (index: {camera_index})")
        print("\n" + "=" * 80)
        print("🎯 OBJECT DETECTION TESTER")
        print("=" * 80)
        print("\nControls:")
        print("  '+' / '-'  : Increase/Decrease confidence (0.0 - 1.0)")
        print("  '[' / ']'  : Decrease/Increase small-object threshold (for candidates)")
        print("  'r'        : Reset to default (from config)")
        print("  'p'        : Print detailed stats")
        print("  'q'        : Quit")
        print("\n" + "=" * 80 + "\n")

        frame_count = 0
        detections_per_conf = {}
        current_conf = float(self.model.conf)
        current_small_conf = float(self.default_small_conf)

        start_time = time.time()

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if duration and (time.time() - start_time) > duration:
                break

            frame_count += 1

            # Run detection
            self.model.conf = current_conf
            results = self.model(frame)

            # Draw results
            display = frame.copy()
            h, w = display.shape[:2]

            # Get detections
            num_detections = 0
            if len(results) > 0 and hasattr(results[0], 'boxes') and len(results[0].boxes) > 0:
                boxes = results[0].boxes
                num_detections = len(boxes)

                # Track detections for this confidence level
                detections_per_conf.setdefault(round(current_conf, 3), 0)
                detections_per_conf[round(current_conf, 3)] += 1

                for box in boxes:
                    try:
                        x1, y1, x2, y2 = box.xyxy[0]
                    except Exception:
                        # Older ultralytics API shape
                        x1, y1, x2, y2 = box.xyxy

                    conf_val = float(box.conf[0]) if hasattr(box, 'conf') else 0.0
                    cls_id = int(box.cls[0]) if hasattr(box, 'cls') else int(box.cls)
                    class_name = results[0].names[cls_id]

                    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

                    color = (0, 255, 0)
                    cv2.rectangle(display, (x1, y1), (x2, y2), color, 2)
                    label = f"{class_name} {conf_val:.2f}"
                    label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
                    cv2.rectangle(display, (x1, y1 - label_size[1] - 5), (x1 + label_size[0], y1), color, -1)
                    cv2.putText(display, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)

            # Status text
            status_text = f"✅ DETECTED: {num_detections} objects" if num_detections > 0 else "❌ NO OBJECTS DETECTED"
            status_color = (0, 255, 0) if num_detections > 0 else (0, 0, 255)
            cv2.putText(display, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, status_color, 2)
            cv2.putText(display, f"Confidence: {current_conf:.2f}", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 200, 100), 2)
            cv2.putText(display, f"Small-conf: {current_small_conf:.2f}", (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (150, 150, 150), 1)
            cv2.putText(display, f"Frame: {frame_count}", (w - 200, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (150, 150, 150), 1)
            cv2.putText(display, "Use +/- to adjust confidence", (10, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 200, 100), 1)

            cv2.imshow('Object Detection Test', display)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('+') or key == ord('='):
                current_conf = min(1.0, current_conf + 0.05)
                print(f"Confidence increased to: {current_conf:.2f}")
            elif key == ord('-') or key == ord('_'):
                current_conf = max(0.01, current_conf - 0.05)
                print(f"Confidence decreased to: {current_conf:.2f}")
            elif key == ord('['):
                current_small_conf = max(0.01, current_small_conf - 0.01)
                print(f"Small-object threshold decreased to: {current_small_conf:.2f}")
            elif key == ord(']'):
                current_small_conf = min(0.5, current_small_conf + 0.01)
                print(f"Small-object threshold increased to: {current_small_conf:.2f}")
            elif key == ord('r'):
                current_conf = float(self.default_conf)
                current_small_conf = float(self.default_small_conf)
                print(f"Confidence & small-conf reset to config defaults: {current_conf}, {current_small_conf}")
            elif key == ord('p'):
                self._print_stats(frame_count, detections_per_conf)

        cap.release()
        cv2.destroyAllWindows()
        self._print_final_summary(frame_count, detections_per_conf)

    def _print_stats(self, frame_count, detections_per_conf):
        print("\n" + "=" * 80)
        print("📊 CURRENT STATISTICS")
        print("=" * 80)
        print(f"Frames processed: {frame_count}")
        print(f"\nDetection rates by confidence:")
        for conf in sorted(detections_per_conf.keys()):
            count = detections_per_conf[conf]
            rate = 100 * count / max(1, frame_count)
            print(f"  Confidence {conf:.3f}: {count}/{frame_count} ({rate:.1f}%)")
        print("=" * 80 + "\n")

    def _print_final_summary(self, frame_count, detections_per_conf):
        print("\n" + "=" * 80)
        print("📈 FINAL SUMMARY")
        print("=" * 80)
        print(f"Total frames: {frame_count}\n")

        if detections_per_conf:
            print("Detection results by confidence threshold:")
            print("-" * 80)

            best_conf = None
            best_rate = 0

            for conf in sorted(detections_per_conf.keys()):
                count = detections_per_conf[conf]
                rate = 100 * count / max(1, frame_count)
                print(f"  Confidence {conf:.3f}: {count:3d}/{frame_count} frames ({rate:5.1f}%)")
                if rate > best_rate and rate > 50:
                    best_rate = rate
                    best_conf = conf

            print("\n" + "=" * 80)
            print("💡 RECOMMENDATIONS:")
            print("=" * 80)

            if best_conf is None:
                print("⚠️  OBJECT DETECTION NOT WORKING")
                print("\nPossible causes:")
                print("  1. No objects in camera view")
                print("  2. Objects too small or unclear")
                print("  3. Objects not in COCO dataset (person, cup, bottle, etc.)")
                print("  4. Model file corrupted")
                print("\nSolutions:")
                print("  - Try with common objects: cup, bottle, spoon, banana, apple")
                print("  - Ensure objects are clearly visible")
                print("  - Check if yolo26n.pt file is valid")
            else:
                print(f"✅ Best confidence threshold: {best_conf:.3f} ({best_rate:.1f}% detection)")
        else:
            print("No detections recorded.")


def parse_args():
    parser = argparse.ArgumentParser(description='Object detection tester with configurable confidence')
    parser.add_argument('--camera', type=int, default=0, help='Camera index')
    parser.add_argument('--duration', type=int, default=60, help='Test duration in seconds')
    parser.add_argument('--conf', type=float, help='Start confidence threshold (overrides config)')
    parser.add_argument('--small-conf', type=float, help='Small-object confidence threshold (for candidate boxes)')
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    tester = ObjectDetectionTester()
    # Override defaults if provided
    if args.conf is not None:
        tester.model.conf = float(args.conf)
        print(f"Starting confidence overridden to: {tester.model.conf}")
    if args.small_conf is not None:
        tester.default_small_conf = float(args.small_conf)
        print(f"Small-object threshold overridden to: {tester.default_small_conf}")

    tester.run_test_camera(camera_index=args.camera, duration=args.duration)
