#!/usr/bin/env python3
"""
Detailed Analysis: Hand-to-Object Algorithm Performance
Analyzes distance calculations and detection accuracy
"""

import sys
import cv2
import numpy as np
from pathlib import Path
import json
from datetime import datetime

from src.config import Config
from src.detector import BabyWatcher
from src.utils import distance, get_nearest_object_box, calculate_shoulder_width


class AlgorithmAnalyzer:
    """Detailed analysis of Hand-to-Object and Object-to-Mouth algorithms"""
    
    def __init__(self, config_path="config.yaml"):
        """Initialize analyzer"""
        self.config = Config(config_path)
        self.watcher = BabyWatcher(config_path=config_path)
        self.analysis_data = []
        
        print("\n" + "="*80)
        print("🔬 HAND-TO-OBJECT ALGORITHM DETAILED ANALYSIS")
        print("="*80 + "\n")
    
    def analyze_frame(self, frame, frame_num=1, show_visualization=True):
        """
        Analyze single frame in detail
        
        Args:
            frame: Input frame
            frame_num: Frame number for tracking
            show_visualization: Show debug visualization
        
        Returns:
            analysis_dict with detailed metrics
        """
        print(f"\n{'='*80}")
        print(f"📸 Frame {frame_num} Analysis")
        print(f"{'='*80}")
        
        # Process frame
        processed_frame, info = self.watcher.process_frame(frame)
        
        # Extract data
        results = info.get('results', {})
        pose_data = results.get('pose_data', [])
        object_data = results.get('object_data', [])
        
        analysis = {
            'frame': frame_num,
            'timestamp': datetime.now().isoformat(),
            'status': info.get('status', 'UNKNOWN'),
            'pose_detected': bool(pose_data),
            'num_objects': len(object_data),
            'keypoints': None,
            'objects': None,
            'distances': {},
            'thresholds': {},
            'algorithm_steps': [],
        }
        
        # Analysis
        if not pose_data:
            print("⚠️  No pose detected in frame")
            return analysis
        
        keypoints = pose_data[0] if isinstance(pose_data[0], list) else pose_data
        
        if len(keypoints) < 17:
            print(f"⚠️  Invalid keypoints format: {len(keypoints)} keypoints")
            return analysis
        
        print(f"\n✅ Pose Detected - {len(keypoints)} keypoints\n")
        
        # Extract key points
        nose = np.array(keypoints[0])
        left_wrist = np.array(keypoints[9])
        right_wrist = np.array(keypoints[10])
        left_shoulder = np.array(keypoints[5])
        right_shoulder = np.array(keypoints[6])
        
        print("📍 Key Positions:")
        print(f"  Nose: ({nose[0]:.1f}, {nose[1]:.1f})")
        print(f"  Left Wrist: ({left_wrist[0]:.1f}, {left_wrist[1]:.1f})")
        print(f"  Right Wrist: ({right_wrist[0]:.1f}, {right_wrist[1]:.1f})")
        print(f"  Left Shoulder: ({left_shoulder[0]:.1f}, {left_shoulder[1]:.1f})")
        print(f"  Right Shoulder: ({right_shoulder[0]:.1f}, {right_shoulder[1]:.1f})")
        
        # Step 1: Calculate shoulder width
        print(f"\n{'─'*80}")
        print("STEP 1: Calculate Shoulder Width (for dynamic threshold)")
        print(f"{'─'*80}")
        
        shoulder_width = calculate_shoulder_width(left_shoulder, right_shoulder)
        print(f"  Formula: shoulder_width = distance(left_shoulder, right_shoulder)")
        print(f"  Calculation: √[({left_shoulder[0]:.1f} - {right_shoulder[0]:.1f})² + ({left_shoulder[1]:.1f} - {right_shoulder[1]:.1f})²]")
        print(f"  Result: {shoulder_width:.1f} pixels")
        
        analysis['keypoints'] = {
            'nose': tuple(nose),
            'left_wrist': tuple(left_wrist),
            'right_wrist': tuple(right_wrist),
            'left_shoulder': tuple(left_shoulder),
            'right_shoulder': tuple(right_shoulder),
            'shoulder_width': shoulder_width,
        }
        
        analysis['algorithm_steps'].append({
            'step': 1,
            'name': 'Calculate Shoulder Width',
            'value': shoulder_width,
            'unit': 'pixels',
        })
        
        # Step 2: Calculate dynamic thresholds
        print(f"\n{'─'*80}")
        print("STEP 2: Calculate Dynamic Thresholds")
        print(f"{'─'*80}")
        
        threshold_hm = shoulder_width * 0.9
        threshold_ho = shoulder_width * 0.8
        
        print(f"  Hand-to-Mouth Threshold = shoulder_width × 0.9")
        print(f"                          = {shoulder_width:.1f} × 0.9")
        print(f"                          = {threshold_hm:.1f} pixels")
        print(f"\n  Hand-to-Object Threshold = shoulder_width × 0.8")
        print(f"                           = {shoulder_width:.1f} × 0.8")
        print(f"                           = {threshold_ho:.1f} pixels")
        
        analysis['thresholds']['hand_mouth'] = threshold_hm
        analysis['thresholds']['hand_object'] = threshold_ho
        
        analysis['algorithm_steps'].append({
            'step': 2,
            'name': 'Calculate Dynamic Thresholds',
            'hand_mouth_threshold': threshold_hm,
            'hand_object_threshold': threshold_ho,
        })
        
        # Step 3: Calculate Hand-to-Mouth distance
        print(f"\n{'─'*80}")
        print("STEP 3: Calculate Hand-to-Mouth Distance (Euclidean)")
        print(f"{'─'*80}")
        
        hm_left = distance(left_wrist, nose)
        hm_right = distance(right_wrist, nose)
        hm_min = min(hm_left, hm_right)
        
        print(f"  Left Wrist to Nose Distance:")
        print(f"    √[({left_wrist[0]:.1f} - {nose[0]:.1f})² + ({left_wrist[1]:.1f} - {nose[1]:.1f})²]")
        print(f"    = {hm_left:.1f} pixels")
        
        print(f"\n  Right Wrist to Nose Distance:")
        print(f"    √[({right_wrist[0]:.1f} - {nose[0]:.1f})² + ({right_wrist[1]:.1f} - {nose[1]:.1f})²]")
        print(f"    = {hm_right:.1f} pixels")
        
        print(f"\n  Minimum (used for detection): {hm_min:.1f} pixels")
        
        analysis['distances']['hand_mouth'] = hm_min
        analysis['distances']['hand_mouth_left'] = hm_left
        analysis['distances']['hand_mouth_right'] = hm_right
        
        # Determine Hand-to-Mouth status
        print(f"\n  Decision Logic:")
        print(f"    if {hm_min:.1f} < {threshold_hm:.1f}:")
        hm_danger = hm_min < threshold_hm
        print(f"      → {'🚨 HAND_TO_MOUTH' if hm_danger else '✅ SAFE (Hand-to-Mouth)'}")
        
        analysis['algorithm_steps'].append({
            'step': 3,
            'name': 'Hand-to-Mouth Distance',
            'left_distance': hm_left,
            'right_distance': hm_right,
            'minimum_distance': hm_min,
            'threshold': threshold_hm,
            'is_danger': hm_danger,
        })
        
        # Step 4: Process objects and Hand-to-Object distance
        print(f"\n{'─'*80}")
        print("STEP 4: Hand-to-Object Analysis (Boundary-Based Distance)")
        print(f"{'─'*80}")
        
        if not object_data or len(object_data) == 0:
            print("  ⚠️  No objects detected in frame")
            analysis['objects'] = []
        else:
            print(f"  Objects Found: {len(object_data)}\n")
            
            objects_boxes = [obj[:4] for obj in object_data]
            hand_pos = left_wrist if hm_left < hm_right else right_wrist
            
            ho_distance, nearest_idx, nearest_box = get_nearest_object_box(hand_pos, objects_boxes)
            
            print(f"  Selected Hand Position: ({'Left' if hm_left < hm_right else 'Right'}) ({hand_pos[0]:.1f}, {hand_pos[1]:.1f})")
            
            # Analyze nearest object
            if nearest_box is not None:
                x1, y1, x2, y2 = nearest_box
                
                print(f"\n  Nearest Object (Index {nearest_idx}):")
                print(f"    Bounding Box: [x={x1:.1f}, y={y1:.1f}, width={x2-x1:.1f}, height={y2-y1:.1f}]")
                
                # Calculate closest point on boundary
                closest_x = max(x1, min(hand_pos[0], x2))
                closest_y = max(y1, min(hand_pos[1], y2))
                
                print(f"\n  Boundary Distance Calculation:")
                print(f"    Hand Position: ({hand_pos[0]:.1f}, {hand_pos[1]:.1f})")
                print(f"    Box Range: X=[{x1:.1f}, {x2:.1f}], Y=[{y1:.1f}, {y2:.1f}]")
                print(f"\n    Clamping X: clamp({hand_pos[0]:.1f}, {x1:.1f}, {x2:.1f}) = {closest_x:.1f}")
                print(f"    Clamping Y: clamp({hand_pos[1]:.1f}, {y1:.1f}, {y2:.1f}) = {closest_y:.1f}")
                
                print(f"\n    Closest Point on Boundary: ({closest_x:.1f}, {closest_y:.1f})")
                print(f"    Distance: √[({hand_pos[0]:.1f} - {closest_x:.1f})² + ({hand_pos[1]:.1f} - {closest_y:.1f})²]")
                print(f"            = {ho_distance:.1f} pixels")
                
                # Determine status
                print(f"\n    Decision Logic:")
                print(f"      if {ho_distance:.1f} < {threshold_ho:.1f}:")
                ho_danger = ho_distance < threshold_ho
                print(f"        → {'🚨 OBJECT_TO_MOUTH' if ho_danger else '✅ SAFE (Hand-to-Object)'}")
                
                analysis['distances']['hand_object'] = ho_distance
                analysis['distances']['hand_object_status'] = 'HOLDING' if ho_distance < 10 else 'NEAR' if ho_danger else 'FAR'
                analysis['objects'] = [
                    {
                        'index': nearest_idx,
                        'box': nearest_box,
                        'distance': ho_distance,
                        'threshold': threshold_ho,
                        'is_danger': ho_danger,
                        'closest_point': (closest_x, closest_y),
                    }
                ]
            
            analysis['algorithm_steps'].append({
                'step': 4,
                'name': 'Hand-to-Object Distance',
                'hand_position': tuple(hand_pos),
                'objects_count': len(objects_boxes),
                'nearest_object_distance': ho_distance,
                'threshold': threshold_ho,
                'is_danger': ho_danger if nearest_box is not None else False,
            })
        
        # Final detection status
        print(f"\n{'─'*80}")
        print("FINAL DETECTION RESULT")
        print(f"{'─'*80}")
        print(f"  Status: {info.get('status', 'UNKNOWN')}")
        print(f"  Hand-to-Mouth: {'🚨 DANGER' if hm_danger else '✅ SAFE'}")
        if analysis['objects']:
            ho_status = analysis['objects'][0]['is_danger'] if analysis['objects'] else False
            print(f"  Hand-to-Object: {'🚨 DANGER' if ho_status else '✅ SAFE'}")
        
        self.analysis_data.append(analysis)
        return analysis
    
    def print_comparison(self, analyses):
        """Compare multiple frame analyses"""
        print(f"\n{'='*80}")
        print("📊 COMPARISON OF MULTIPLE FRAMES")
        print(f"{'='*80}\n")
        
        print(f"{'Frame':<8} {'Status':<20} {'H-M Dist':<12} {'H-M Thresh':<12} {'H-O Dist':<12} {'H-O Thresh':<12}")
        print(f"{'-'*80}")
        
        for analysis in analyses:
            frame = analysis['frame']
            status = analysis['status']
            hm_dist = analysis['distances'].get('hand_mouth', 'N/A')
            hm_thresh = analysis['thresholds'].get('hand_mouth', 'N/A')
            ho_dist = analysis['distances'].get('hand_object', 'N/A')
            ho_thresh = analysis['thresholds'].get('hand_object', 'N/A')
            
            hm_dist_str = f"{hm_dist:.1f}px" if isinstance(hm_dist, (int, float)) else str(hm_dist)
            hm_thresh_str = f"{hm_thresh:.1f}px" if isinstance(hm_thresh, (int, float)) else str(hm_thresh)
            ho_dist_str = f"{ho_dist:.1f}px" if isinstance(ho_dist, (int, float)) else str(ho_dist)
            ho_thresh_str = f"{ho_thresh:.1f}px" if isinstance(ho_thresh, (int, float)) else str(ho_thresh)
            
            print(f"{frame:<8} {status:<20} {hm_dist_str:<12} {hm_thresh_str:<12} {ho_dist_str:<12} {ho_thresh_str:<12}")
    
    def export_analysis(self, filename=None):
        """Export analysis data to JSON"""
        if filename is None:
            filename = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Convert numpy types for JSON serialization
        def convert_types(obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, (np.float64, np.float32)):
                return float(obj)
            elif isinstance(obj, (np.int64, np.int32)):
                return int(obj)
            elif isinstance(obj, dict):
                return {k: convert_types(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [convert_types(item) for item in obj]
            return obj
        
        data = convert_types(self.analysis_data)
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"\n💾 Analysis exported to: {filename}")
        return filename


def interactive_analysis():
    """Interactive mode for frame analysis"""
    print("\n" + "="*80)
    print("🎬 INTERACTIVE FRAME ANALYSIS MODE")
    print("="*80 + "\n")
    
    analyzer = AlgorithmAnalyzer()
    
    print("Commands:")
    print("  'c' - Capture from camera")
    print("  'i' - Input image file")
    print("  'q' - Quit")
    print()
    
    frame_num = 0
    
    try:
        while True:
            cmd = input("\nEnter command (c/i/q): ").strip().lower()
            
            if cmd == 'q':
                break
            elif cmd == 'c':
                # Capture from camera
                print("\n📹 Opening camera...")
                cap = cv2.VideoCapture(0)
                
                if not cap.isOpened():
                    print("❌ Cannot open camera")
                    continue
                
                print("Press SPACE to capture, 'q' to exit camera")
                
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    
                    cv2.imshow('Press SPACE to capture, q to exit', frame)
                    key = cv2.waitKey(1) & 0xFF
                    
                    if key == ord(' '):
                        frame_num += 1
                        analyzer.analyze_frame(frame, frame_num=frame_num)
                    elif key == ord('q'):
                        break
                
                cap.release()
                cv2.destroyAllWindows()
            
            elif cmd == 'i':
                # Input image
                image_path = input("Enter image file path: ").strip()
                if Path(image_path).exists():
                    frame = cv2.imread(image_path)
                    if frame is not None:
                        frame_num += 1
                        analyzer.analyze_frame(frame, frame_num=frame_num)
                    else:
                        print("❌ Cannot read image")
                else:
                    print("❌ File not found")
    
    except KeyboardInterrupt:
        pass
    
    if analyzer.analysis_data:
        analyzer.print_comparison(analyzer.analysis_data)
        analyzer.export_analysis()


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Detailed Analysis of Hand-to-Object Algorithm"
    )
    parser.add_argument(
        '--image',
        help='Analyze single image file'
    )
    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Interactive analysis mode'
    )
    
    args = parser.parse_args()
    
    if args.interactive:
        interactive_analysis()
    elif args.image:
        analyzer = AlgorithmAnalyzer()
        frame = cv2.imread(args.image)
        if frame is not None:
            analyzer.analyze_frame(frame)
        else:
            print(f"❌ Cannot read image: {args.image}")
    else:
        interactive_analysis()


if __name__ == "__main__":
    main()
