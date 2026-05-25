"""Comprehensive test for enhanced BabyWatcher detection"""

import cv2
import numpy as np
import os
from src.detector import BabyWatcher
from src.config import Config
import time

def test_enhanced_detection():
    """Test enhanced detection with multiple test cases"""
    
    print("=" * 60)
    print("🚀 BabyWatcher Enhanced Detection Test Suite")
    print("=" * 60)
    
    # Initialize detector
    detector = BabyWatcher("config.yaml")
    
    test_cases = [
        ("images/safe.jpg", "Safe - No danger"),
        ("images/a1.jpg", "Danger - Hand/Object near mouth"),
    ]
    
    all_passed = True
    
    for image_path, description in test_cases:
        if not os.path.exists(image_path):
            print(f"\n⚠️  SKIPPED: {image_path} (file not found)")
            continue
        
        print(f"\n{'='*60}")
        print(f"📸 Testing: {description}")
        print(f"   File: {image_path}")
        print(f"{'='*60}")
        
        try:
            # Load image
            frame = cv2.imread(image_path)
            if frame is None:
                print(f"❌ ERROR: Cannot read image {image_path}")
                all_passed = False
                continue
            
            print(f"   Image size: {frame.shape[1]}x{frame.shape[0]}")
            
            # Process frame
            start_time = time.time()
            output_frame, info = detector.process_frame(frame)
            elapsed = time.time() - start_time
            
            print(f"\n📊 Detection Results:")
            print(f"   Status:          {info.get('status', 'UNKNOWN')}")
            print(f"   H-M Distance:    {info.get('h_m_dist', 0.0):.2f}")
            print(f"   H-M Threshold:   {info.get('h_m_thresh', 0.0):.2f}")
            print(f"   H-O Distance:    {info.get('h_o_dist', 0.0):.2f}")
            print(f"   H-O Threshold:   {info.get('h_o_thresh', 0.0):.2f}")
            print(f"   Num Objects:     {info.get('num_objects', 0)}")
            print(f"   Pose Detected:   {info.get('pose_detected', False)}")
            print(f"   Processing Time: {elapsed*1000:.1f}ms")
            
            # Verify features
            if output_frame is None:
                print(f"\n❌ ERROR: No output frame")
                all_passed = False
            else:
                print(f"\n✅ Output frame generated")
                print(f"   Output size: {output_frame.shape[1]}x{output_frame.shape[0]}")
                
                # Save output
                output_path = f"output_enhanced_{os.path.basename(image_path).split('.')[0]}.jpg"
                cv2.imwrite(output_path, output_frame)
                print(f"   Saved to: {output_path}")
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            all_passed = False
    
    print(f"\n{'='*60}")
    if all_passed:
        print("✅ All tests passed!")
    else:
        print("⚠️  Some tests had issues")
    print("=" * 60)
    
    return all_passed

if __name__ == "__main__":
    test_enhanced_detection()
