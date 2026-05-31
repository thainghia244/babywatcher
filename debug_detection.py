#!/usr/bin/env python3
"""
Debug Tool for Hand-to-Object Detection Issues
Diagnoses problems with object detection and alert triggering
"""

import cv2
import argparse
import numpy as np
from pathlib import Path
from src.detector import BabyWatcher
from src.config import Config
import sys

class DetectionDebugger:
    def __init__(self, config_path='config.yaml'):
        self.config = Config(config_path)
        self.detector = BabyWatcher(config_path)
        self.frame_count = 0
        
        # Detection stats
        self.pose_detected_frames = 0
        self.object_detected_frames = 0
        self.hand_mouth_triggered = 0
        self.object_mouth_triggered = 0
        
        # Last values
        self.last_h_m_distance = None
        self.last_h_o_distance = None
        self.last_shoulder_width = None
        self.last_objects = []
        self.last_pose_result = None
        
    def run_debug_camera(self, camera_index=0, duration=None):
        """Run debug mode with detailed output"""
        cap = cv2.VideoCapture(camera_index)
        
        if not cap.isOpened():
            print(f"❌ ERROR: Cannot open camera {camera_index}")
            return
        
        print(f"✅ Camera opened successfully (camera index: {camera_index})")
        print("\n" + "="*100)
        print("🐛 DEBUG MODE - DETECTION DIAGNOSTICS")
        print("="*100)
        print("\nControls:")
        print("  'q' - Quit")
        print("  'p' - Print detailed stats")
        print("  't' - Toggle threshold display")
        print("  'c' - Toggle confidence adjustment (use +/- keys)")
        print("  'd' - Toggle distance display")
        print("  'h' - Toggle histogram of distances")
        print("\n" + "="*100 + "\n")
        
        show_threshold = True
        show_distance = True
        adjust_confidence = False
        confidence = self.config.get_dict("detection").get("conf_thresh", 0.4)
        
        distances_h_m = []
        distances_h_o = []
        
        import time
        start_time = time.time()
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Check duration
            if duration and (time.time() - start_time) > duration:
                break
            
            self.frame_count += 1
            
            # Process frame with current confidence
            self.detector.pose_model.conf = confidence
            if hasattr(self.detector, 'object_model'):
                self.detector.object_model.conf = confidence
            
            # Get detection results
            pose_result = self.detector.pose_model(frame) if self.detector.pose_model else None
            object_result = self.detector.object_model(frame) if hasattr(self.detector, 'object_model') else None
            
            # Parse results
            pose_detected = False
            keypoints = None
            shoulder_width = 0
            
            if pose_result and len(pose_result) > 0:
                boxes = pose_result[0].boxes
                if len(boxes) > 0:
                    pose_detected = True
                    self.pose_detected_frames += 1
                    
                    # Get keypoints
                    if hasattr(pose_result[0], 'keypoints') and pose_result[0].keypoints is not None:
                        kpts = pose_result[0].keypoints.xy[0]  # Get first person's keypoints
                        keypoints = kpts
                        
                        # Calculate shoulder width (distance between left and right shoulders)
                        # Keypoint indices: 5=left_shoulder, 6=right_shoulder
                        if len(kpts) > 6:
                            left_shoulder = kpts[5]
                            right_shoulder = kpts[6]
                            shoulder_width = np.linalg.norm(right_shoulder - left_shoulder)
                            self.last_shoulder_width = shoulder_width
            
            # Object detection
            objects_detected = []
            if object_result and len(object_result) > 0:
                boxes = object_result[0].boxes
                for box in boxes:
                    confidence_score = float(box.conf[0])
                    class_id = int(box.cls[0])
                    class_name = object_result[0].names[class_id]
                    bbox = box.xyxy[0]  # [x1, y1, x2, y2]
                    
                    objects_detected.append({
                        'name': class_name,
                        'confidence': confidence_score,
                        'bbox': bbox,
                        'center': [(bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2]
                    })
                
                if len(objects_detected) > 0:
                    self.object_detected_frames += 1
                    self.last_objects = objects_detected
            
            # Calculate distances and alerts
            h_m_distance = None
            h_o_distance = None
            h_m_threshold = None
            h_o_threshold = None
            alert_status = "SAFE"
            
            if pose_detected and keypoints is not None and shoulder_width > 0:
                # Hand-to-Mouth distance (Euclidean)
                if len(keypoints) > 10:  # At least need nose and wrists
                    nose = keypoints[0]
                    left_wrist = keypoints[9]
                    right_wrist = keypoints[10]
                    
                    dist_left = np.linalg.norm(left_wrist - nose)
                    dist_right = np.linalg.norm(right_wrist - nose)
                    h_m_distance = min(dist_left, dist_right)
                    
                    h_m_threshold = shoulder_width * 0.9
                    self.last_h_m_distance = h_m_distance
                    
                    distances_h_m.append(h_m_distance)
                    if len(distances_h_m) > 100:
                        distances_h_m.pop(0)
                    
                    if h_m_distance < h_m_threshold:
                        alert_status = "HAND_TO_MOUTH"
                        self.hand_mouth_triggered += 1
                
                # Hand-to-Object distance
                if len(objects_detected) > 0:
                    h_o_threshold = shoulder_width * 0.8
                    
                    # Calculate distance from hand to nearest object
                    closest_distance = float('inf')
                    for obj in objects_detected:
                        obj_center = obj['center']
                        
                        if len(keypoints) > 10:
                            left_wrist = keypoints[9]
                            right_wrist = keypoints[10]
                            
                            dist_left = np.linalg.norm(left_wrist - np.array(obj_center))
                            dist_right = np.linalg.norm(right_wrist - np.array(obj_center))
                            
                            closest_distance = min(closest_distance, dist_left, dist_right)
                    
                    if closest_distance < float('inf'):
                        h_o_distance = closest_distance
                        self.last_h_o_distance = h_o_distance
                        
                        distances_h_o.append(h_o_distance)
                        if len(distances_h_o) > 100:
                            distances_h_o.pop(0)
                        
                        if h_o_distance < h_o_threshold and h_m_distance is not None and h_m_distance > h_m_threshold:
                            alert_status = "OBJECT_TO_MOUTH"
                            self.object_mouth_triggered += 1
            
            # Draw on frame
            display_frame = frame.copy()
            h, w = display_frame.shape[:2]
            
            # Draw status
            color = (0, 255, 0) if alert_status == "SAFE" else (0, 165, 255) if alert_status == "HAND_TO_MOUTH" else (0, 0, 255)
            cv2.putText(display_frame, f"STATUS: {alert_status}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
            
            # Draw pose info
            pose_text = f"Pose: {'✓ YES' if pose_detected else '✗ NO'}"
            pose_color = (0, 255, 0) if pose_detected else (0, 0, 255)
            cv2.putText(display_frame, pose_text, (10, 70), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, pose_color, 2)
            
            # Draw object info
            object_text = f"Objects: {len(objects_detected)}"
            object_color = (0, 255, 0) if len(objects_detected) > 0 else (0, 0, 255)
            cv2.putText(display_frame, object_text, (10, 110), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, object_color, 2)
            
            # Draw distances
            if show_distance:
                y_pos = 150
                if shoulder_width > 0:
                    cv2.putText(display_frame, f"Shoulder Width: {shoulder_width:.1f}px", (10, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 1)
                    y_pos += 30
                
                if h_m_distance is not None:
                    cv2.putText(display_frame, f"H-M Distance: {h_m_distance:.1f}px", (10, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 200, 255), 1)
                    y_pos += 30
                
                if h_m_threshold is not None:
                    cv2.putText(display_frame, f"H-M Threshold: {h_m_threshold:.1f}px", (10, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 100, 255), 1)
                    y_pos += 30
                
                if h_o_distance is not None:
                    cv2.putText(display_frame, f"H-O Distance: {h_o_distance:.1f}px", (10, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 200, 255), 1)
                    y_pos += 30
                
                if h_o_threshold is not None:
                    cv2.putText(display_frame, f"H-O Threshold: {h_o_threshold:.1f}px", (10, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 100, 255), 1)
            
            # Confidence display
            conf_text = f"Confidence: {confidence:.2f}"
            conf_color = (100, 200, 100) if adjust_confidence else (150, 150, 150)
            cv2.putText(display_frame, conf_text, (10, h - 40),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, conf_color, 2)
            
            if adjust_confidence:
                cv2.putText(display_frame, "(+/- to adjust, ENTER to apply)", (10, h - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 200, 100), 1)
            
            # Draw frame counter
            cv2.putText(display_frame, f"Frame: {self.frame_count}", (w - 200, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (150, 150, 150), 1)
            
            # Draw objects on frame
            for obj in objects_detected:
                bbox = obj['bbox']
                x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
                cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                label = f"{obj['name']} {obj['confidence']:.2f}"
                cv2.putText(display_frame, label, (x1, y1 - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
            
            # Draw keypoints if pose detected
            if pose_detected and keypoints is not None:
                for i, kpt in enumerate(keypoints):
                    if len(kpt) >= 2:
                        x, y = int(kpt[0]), int(kpt[1])
                        cv2.circle(display_frame, (x, y), 4, (0, 255, 255), -1)
            
            cv2.imshow('🐛 Detection Debug', display_frame)
            
            # Keyboard controls
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'):
                break
            elif key == ord('p'):
                self._print_stats()
            elif key == ord('t'):
                show_threshold = not show_threshold
                print(f"Threshold display: {'ON' if show_threshold else 'OFF'}")
            elif key == ord('d'):
                show_distance = not show_distance
                print(f"Distance display: {'ON' if show_distance else 'OFF'}")
            elif key == ord('c'):
                adjust_confidence = not adjust_confidence
                print(f"Confidence adjustment: {'ON' if adjust_confidence else 'OFF'}")
            elif adjust_confidence and key == ord('+'):
                confidence = min(0.9, confidence + 0.05)
                print(f"Confidence increased to: {confidence:.2f}")
            elif adjust_confidence and key == ord('-'):
                confidence = max(0.1, confidence - 0.05)
                print(f"Confidence decreased to: {confidence:.2f}")
        
        cap.release()
        cv2.destroyAllWindows()
        
        self._print_summary(distances_h_m, distances_h_o)
    
    def _print_stats(self):
        """Print detailed statistics"""
        print("\n" + "="*80)
        print("📊 DETAILED STATISTICS")
        print("="*80)
        print(f"Frame: {self.frame_count}")
        print(f"Pose Detected: {self.pose_detected_frames}/{self.frame_count} ({100*self.pose_detected_frames/max(1,self.frame_count):.1f}%)")
        print(f"Objects Detected: {self.object_detected_frames}/{self.frame_count} ({100*self.object_detected_frames/max(1,self.frame_count):.1f}%)")
        print(f"\nLast Values:")
        if self.last_shoulder_width:
            print(f"  Shoulder Width: {self.last_shoulder_width:.1f}px")
        if self.last_h_m_distance is not None:
            print(f"  H-M Distance: {self.last_h_m_distance:.1f}px")
        if self.last_h_o_distance is not None:
            print(f"  H-O Distance: {self.last_h_o_distance:.1f}px")
        if self.last_objects:
            print(f"  Objects: {len(self.last_objects)}")
            for obj in self.last_objects:
                print(f"    - {obj['name']} ({obj['confidence']:.2f})")
        print(f"\nAlerts Triggered:")
        print(f"  Hand-to-Mouth: {self.hand_mouth_triggered}")
        print(f"  Object-to-Mouth: {self.object_mouth_triggered}")
        print("="*80 + "\n")
    
    def _print_summary(self, distances_h_m, distances_h_o):
        """Print final summary"""
        print("\n" + "="*80)
        print("📈 FINAL SUMMARY")
        print("="*80)
        print(f"\nTotal Frames: {self.frame_count}")
        print(f"Pose Detection Rate: {100*self.pose_detected_frames/max(1,self.frame_count):.1f}%")
        print(f"Object Detection Rate: {100*self.object_detected_frames/max(1,self.frame_count):.1f}%")
        
        if distances_h_m:
            distances_h_m = np.array(distances_h_m)
            print(f"\nHand-to-Mouth Distance:")
            print(f"  Average: {np.mean(distances_h_m):.1f}px")
            print(f"  Min: {np.min(distances_h_m):.1f}px")
            print(f"  Max: {np.max(distances_h_m):.1f}px")
            print(f"  Std Dev: {np.std(distances_h_m):.1f}px")
        
        if distances_h_o:
            distances_h_o = np.array(distances_h_o)
            print(f"\nHand-to-Object Distance:")
            print(f"  Average: {np.mean(distances_h_o):.1f}px")
            print(f"  Min: {np.min(distances_h_o):.1f}px")
            print(f"  Max: {np.max(distances_h_o):.1f}px")
            print(f"  Std Dev: {np.std(distances_h_o):.1f}px")
        
        print(f"\nAlerts Triggered:")
        print(f"  Hand-to-Mouth: {self.hand_mouth_triggered}")
        print(f"  Object-to-Mouth: {self.object_mouth_triggered}")
        
        print("\n" + "="*80)
        print("💡 DIAGNOSTIC RECOMMENDATIONS:")
        print("="*80)
        
        if self.pose_detected_frames < 0.8 * self.frame_count:
            print("⚠️  LOW POSE DETECTION RATE")
            print("   Solutions:")
            print("   - Ensure full body is visible in camera")
            print("   - Check lighting conditions")
            print("   - Stand at optimal distance from camera")
        else:
            print("✅ Pose Detection Rate: GOOD")
        
        if self.object_detected_frames < 0.5 * self.frame_count:
            print("\n⚠️  LOW OBJECT DETECTION RATE")
            print("   Solutions:")
            print("   - Try lowering confidence threshold (press 'c' then '-')")
            print("   - Ensure objects are clearly visible")
            print("   - Try with common objects (cup, bottle, spoon, etc.)")
        else:
            print("\n✅ Object Detection Rate: GOOD")
        
        if self.hand_mouth_triggered == 0 and self.pose_detected_frames > 0.8 * self.frame_count:
            print("\n⚠️  NO HAND-TO-MOUTH ALERTS TRIGGERED")
            print("   Solutions:")
            print("   - Bring hand much closer to mouth")
            print("   - Check shoulder width calculation")
            print("   - Verify hand-to-mouth threshold (current: 0.9 × shoulder_width)")
            print("   - Lower confidence threshold for better pose detection")
        
        print("\n" + "="*80 + "\n")


def main():
    parser = argparse.ArgumentParser(description='Debug Detection Issues')
    parser.add_argument('--camera', type=int, default=0, help='Camera index (default: 0)')
    parser.add_argument('--duration', type=int, default=None, help='Duration in seconds (default: infinite)')
    parser.add_argument('--config', type=str, default='config.yaml', help='Config file path')
    
    args = parser.parse_args()
    
    debugger = DetectionDebugger(args.config)
    debugger.run_debug_camera(args.camera, args.duration)


if __name__ == '__main__':
    main()
