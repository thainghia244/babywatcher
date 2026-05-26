#!/usr/bin/env python3
"""
Real-time Testing: Hand-to-Object and Object-to-Mouth Algorithms
Tests algorithms using actual camera feed
"""

import sys
import cv2
import numpy as np
from pathlib import Path
import time
from collections import deque

from src.config import Config
from src.detector import BabyWatcher
from src.utils import (
    distance, 
    get_nearest_object_box, 
    calculate_shoulder_width,
    draw_skeleton,
    draw_distance_line
)


class HandObjectTester:
    """Real-time tester for Hand-to-Object and Object-to-Mouth algorithms"""
    
    def __init__(self, config_path="config.yaml"):
        """Initialize tester"""
        self.config = Config(config_path)
        self.watcher = BabyWatcher(config_path=config_path)
        
        # Metrics tracking
        self.frame_count = 0
        self.metrics_history = deque(maxlen=100)  # Last 100 frames
        
        # Detection history for stability
        self.detection_stable_frames = 0
        self.last_status = "SAFE"
        
        print("\n" + "="*70)
        print("🎬 REAL-TIME HAND-OBJECT TESTING WITH CAMERA")
        print("="*70 + "\n")
        
    def run_camera_test(self, camera_index=0, duration=None):
        """
        Run real-time test from camera
        
        Args:
            camera_index: Camera index (0 for default)
            duration: Test duration in seconds (None = infinite)
        """
        print(f"🎥 Opening camera {camera_index}...")
        cap = cv2.VideoCapture(camera_index)
        
        if not cap.isOpened():
            print(f"❌ Cannot open camera {camera_index}")
            return
        
        # Set camera properties
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cap.set(cv2.CAP_PROP_FPS, 30)
        
        print("✅ Camera opened successfully")
        print("\nControls:")
        print("  'q' - Quit")
        print("  'r' - Reset metrics")
        print("  'p' - Print current metrics")
        print("  's' - Save current frame")
        print("  'd' - Toggle debug info")
        print()
        
        show_debug = True
        start_time = time.time()
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    print("❌ Failed to read frame")
                    break
                
                # Check duration
                if duration and (time.time() - start_time) > duration:
                    print(f"\n⏱️  Duration {duration}s reached")
                    break
                
                # Process frame
                processed_frame, metrics = self.process_frame(frame, show_debug)
                
                # Display
                cv2.imshow('Hand-Object Detection Test', processed_frame)
                
                # Handle keyboard
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("\n👋 Exiting...")
                    break
                elif key == ord('r'):
                    self.metrics_history.clear()
                    print("\n🔄 Metrics reset")
                elif key == ord('p'):
                    self.print_metrics()
                elif key == ord('s'):
                    filename = f"test_frame_{int(time.time())}.jpg"
                    cv2.imwrite(filename, processed_frame)
                    print(f"\n💾 Frame saved: {filename}")
                elif key == ord('d'):
                    show_debug = not show_debug
                    print(f"\n{'🐛 Debug ON' if show_debug else '🔇 Debug OFF'}")
                
        except KeyboardInterrupt:
            print("\n\n⏹️  Test interrupted by user")
        finally:
            cap.release()
            cv2.destroyAllWindows()
            print("✅ Camera closed")
            self.print_summary()
    
    def process_frame(self, frame, show_debug=True):
        """
        Process single frame and extract metrics
        
        Args:
            frame: Input frame from camera
            show_debug: Show debugging information
        
        Returns:
            (display_frame, metrics_dict)
        """
        self.frame_count += 1
        
        # Process with detector
        processed_frame, info = self.watcher.process_frame(frame)
        
        # Extract detection data
        results = info.get('results', {})
        pose_data = results.get('pose_data', [])
        object_data = results.get('object_data', [])
        
        # Extract keypoints and objects
        keypoints_list = []
        objects_boxes = []
        
        if pose_data:
            keypoints_list = pose_data
        
        if object_data:
            objects_boxes = [obj[:4] for obj in object_data]  # Get bbox
        
        # Calculate metrics
        metrics = {
            'frame': self.frame_count,
            'status': info.get('status', 'UNKNOWN'),
            'pose_detected': bool(keypoints_list),
            'num_objects': len(objects_boxes),
            'hand_mouth_distance': None,
            'hand_object_distance': None,
            'shoulder_width': None,
            'threshold_hand_mouth': None,
            'threshold_hand_object': None,
            'hand_position': None,
            'mouth_position': None,
            'nearest_object': None,
        }
        
        # If pose detected, calculate distances
        if keypoints_list and len(keypoints_list) > 0:
            keypoints = keypoints_list[0] if isinstance(keypoints_list[0], list) else keypoints_list
            
            if len(keypoints) >= 17:  # COCO format
                # Extract keypoints
                nose = keypoints[0]
                left_wrist = keypoints[9]
                right_wrist = keypoints[10]
                left_shoulder = keypoints[5]
                right_shoulder = keypoints[6]
                
                # Calculate shoulder width (for dynamic threshold)
                shoulder_w = calculate_shoulder_width(left_shoulder, right_shoulder)
                metrics['shoulder_width'] = shoulder_w
                
                # Calculate thresholds
                threshold_hm = shoulder_w * 0.9 if shoulder_w > 0 else 50
                threshold_ho = shoulder_w * 0.8 if shoulder_w > 0 else 40
                
                metrics['threshold_hand_mouth'] = threshold_hm
                metrics['threshold_hand_object'] = threshold_ho
                
                # Calculate hand-to-mouth distance
                hand_mouth_left = distance(left_wrist, nose)
                hand_mouth_right = distance(right_wrist, nose)
                hand_mouth_min = min(hand_mouth_left, hand_mouth_right)
                
                metrics['hand_mouth_distance'] = hand_mouth_min
                metrics['hand_position'] = left_wrist if hand_mouth_left < hand_mouth_right else right_wrist
                metrics['mouth_position'] = nose
                
                # Calculate hand-to-object distance
                if objects_boxes:
                    hand_pos = metrics['hand_position']
                    nearest_dist, nearest_idx, nearest_box = get_nearest_object_box(hand_pos, objects_boxes)
                    
                    metrics['hand_object_distance'] = nearest_dist
                    metrics['nearest_object'] = {
                        'distance': nearest_dist,
                        'index': nearest_idx,
                        'box': nearest_box,
                        'status': 'HOLDING' if nearest_dist < 10 else 'NEAR' if nearest_dist < threshold_ho else 'FAR'
                    }
                
                # Draw visualization
                processed_frame = self._draw_debug_info(
                    processed_frame, 
                    metrics, 
                    keypoints, 
                    objects_boxes,
                    show_debug
                )
        
        # Store metrics
        self.metrics_history.append(metrics)
        
        return processed_frame, metrics
    
    def _draw_debug_info(self, frame, metrics, keypoints, objects_boxes, show_debug):
        """Draw debugging information on frame"""
        frame_h, frame_w = frame.shape[:2]
        
        # Draw skeleton
        if keypoints:
            frame = draw_skeleton(frame, keypoints)
        
        # Draw object boxes
        for box in objects_boxes:
            x1, y1, x2, y2 = [int(v) for v in box]
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        
        # Draw hand-to-mouth distance line
        if metrics['hand_position'] and metrics['mouth_position']:
            frame = draw_distance_line(
                frame,
                metrics['hand_position'],
                metrics['mouth_position'],
                f"H-M: {metrics['hand_mouth_distance']:.1f}px",
                (0, 165, 255)  # Orange
            )
        
        # Draw hand-to-object distance line
        if metrics['nearest_object'] and metrics['hand_position']:
            obj = metrics['nearest_object']
            box = obj['box']
            center = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
            
            frame = draw_distance_line(
                frame,
                metrics['hand_position'],
                center,
                f"H-O: {obj['distance']:.1f}px ({obj['status']})",
                (0, 0, 255)  # Red
            )
        
        # Draw status and metrics on frame
        y_offset = 30
        
        # Status
        status_color = (0, 255, 0) if metrics['status'] == 'SAFE' else (0, 165, 255) if metrics['status'] == 'HAND_TO_MOUTH' else (0, 0, 255)
        cv2.putText(frame, f"Status: {metrics['status']}", (10, y_offset), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
        y_offset += 35
        
        if show_debug:
            # Pose detected
            pose_color = (0, 255, 0) if metrics['pose_detected'] else (0, 0, 255)
            cv2.putText(frame, f"Pose: {'YES' if metrics['pose_detected'] else 'NO'}", 
                       (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, pose_color, 1)
            y_offset += 25
            
            # Objects
            cv2.putText(frame, f"Objects: {metrics['num_objects']}", 
                       (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
            y_offset += 25
            
            # Distances
            if metrics['hand_mouth_distance'] is not None:
                cv2.putText(frame, f"H-M Distance: {metrics['hand_mouth_distance']:.1f}px", 
                           (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 1)
                y_offset += 25
            
            if metrics['hand_object_distance'] is not None:
                cv2.putText(frame, f"H-O Distance: {metrics['hand_object_distance']:.1f}px", 
                           (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 1)
                y_offset += 25
            
            # Thresholds
            if metrics['threshold_hand_mouth'] is not None:
                cv2.putText(frame, f"H-M Threshold: {metrics['threshold_hand_mouth']:.1f}px", 
                           (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 0), 1)
                y_offset += 25
            
            if metrics['threshold_hand_object'] is not None:
                cv2.putText(frame, f"H-O Threshold: {metrics['threshold_hand_object']:.1f}px", 
                           (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 0), 1)
                y_offset += 25
            
            # Shoulder width
            if metrics['shoulder_width'] is not None:
                cv2.putText(frame, f"Shoulder Width: {metrics['shoulder_width']:.1f}px", 
                           (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 1)
                y_offset += 25
            
            # Frame counter
            cv2.putText(frame, f"Frame: {metrics['frame']}", 
                       (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        
        # Help text
        cv2.putText(frame, "Press 'p' for metrics | 'd' debug | 's' save | 'q' quit", 
                   (10, frame_h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        return frame
    
    def print_metrics(self):
        """Print current metrics"""
        if not self.metrics_history:
            print("\n⚠️  No metrics recorded yet")
            return
        
        recent = list(self.metrics_history)[-10:]  # Last 10 frames
        
        print("\n" + "="*70)
        print("📊 RECENT METRICS (Last 10 Frames)")
        print("="*70)
        
        for m in recent:
            print(f"\nFrame {m['frame']}:")
            print(f"  Status: {m['status']}")
            print(f"  Pose Detected: {m['pose_detected']}")
            print(f"  Objects: {m['num_objects']}")
            
            if m['hand_mouth_distance'] is not None:
                print(f"  H-M Distance: {m['hand_mouth_distance']:.1f}px (threshold: {m['threshold_hand_mouth']:.1f}px)")
            
            if m['hand_object_distance'] is not None:
                print(f"  H-O Distance: {m['hand_object_distance']:.1f}px (threshold: {m['threshold_hand_object']:.1f}px)")
            
            if m['nearest_object']:
                obj = m['nearest_object']
                print(f"  Nearest Object: {obj['distance']:.1f}px - {obj['status']}")
        
        print("\n" + "="*70)
    
    def print_summary(self):
        """Print test summary"""
        if not self.metrics_history:
            print("\n⚠️  No data to summarize")
            return
        
        metrics_list = list(self.metrics_history)
        
        # Count statuses
        status_counts = {}
        pose_detections = 0
        total_objects = 0
        
        for m in metrics_list:
            status = m['status']
            status_counts[status] = status_counts.get(status, 0) + 1
            
            if m['pose_detected']:
                pose_detections += 1
            
            total_objects += m['num_objects']
        
        # Calculate averages
        valid_hm = [m['hand_mouth_distance'] for m in metrics_list if m['hand_mouth_distance'] is not None]
        valid_ho = [m['hand_object_distance'] for m in metrics_list if m['hand_object_distance'] is not None]
        
        print("\n" + "="*70)
        print("📈 TEST SUMMARY")
        print("="*70)
        print(f"\nTotal Frames: {len(metrics_list)}")
        print(f"\nStatus Distribution:")
        for status, count in status_counts.items():
            pct = (count / len(metrics_list)) * 100
            print(f"  {status}: {count} frames ({pct:.1f}%)")
        
        print(f"\nDetection Statistics:")
        print(f"  Pose Detected: {pose_detections}/{len(metrics_list)} ({(pose_detections/len(metrics_list))*100:.1f}%)")
        print(f"  Total Objects: {total_objects}")
        print(f"  Avg Objects/Frame: {total_objects/len(metrics_list):.1f}")
        
        if valid_hm:
            print(f"\nHand-to-Mouth Metrics:")
            print(f"  Avg Distance: {np.mean(valid_hm):.1f}px")
            print(f"  Min Distance: {min(valid_hm):.1f}px")
            print(f"  Max Distance: {max(valid_hm):.1f}px")
            print(f"  Std Dev: {np.std(valid_hm):.1f}px")
        
        if valid_ho:
            print(f"\nHand-to-Object Metrics:")
            print(f"  Avg Distance: {np.mean(valid_ho):.1f}px")
            print(f"  Min Distance: {min(valid_ho):.1f}px")
            print(f"  Max Distance: {max(valid_ho):.1f}px")
            print(f"  Std Dev: {np.std(valid_ho):.1f}px")
        
        print("\n" + "="*70)


def main():
    """Main test function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Real-time Hand-to-Object and Object-to-Mouth Algorithm Tester"
    )
    parser.add_argument(
        '--camera',
        type=int,
        default=0,
        help='Camera index (default: 0)'
    )
    parser.add_argument(
        '--duration',
        type=int,
        default=None,
        help='Test duration in seconds (default: infinite)'
    )
    parser.add_argument(
        '--config',
        default='config.yaml',
        help='Config file path'
    )
    
    args = parser.parse_args()
    
    try:
        tester = HandObjectTester(config_path=args.config)
        tester.run_camera_test(camera_index=args.camera, duration=args.duration)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
