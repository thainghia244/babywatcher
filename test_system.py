#!/usr/bin/env python3
"""
Comprehensive System Test for BabyWatcher
Tests all components: Config, Logger, Alerts, Detector
"""

import sys
import os
import time
import numpy as np
from pathlib import Path


def print_header(title):
    """Print formatted header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def print_test(name, status, message=""):
    """Print test result"""
    if status:
        print(f"  ✅ {name:<40} PASSED")
    else:
        print(f"  ❌ {name:<40} FAILED")
    if message:
        print(f"     {message}")


def test_imports():
    """Test all imports"""
    print_header("🔧 Testing Imports")
    
    tests_passed = 0
    tests_total = 0
    
    # Test standard library imports
    imports = [
        ("yaml", "PyYAML"),
        ("cv2", "OpenCV"),
        ("numpy", "NumPy"),
        ("ultralytics", "Ultralytics YOLO"),
    ]
    
    for module_name, display_name in imports:
        tests_total += 1
        try:
            __import__(module_name)
            print_test(f"Import {display_name}", True)
            tests_passed += 1
        except ImportError as e:
            print_test(f"Import {display_name}", False, str(e))
    
    # Test custom modules
    try:
        tests_total += 1
        from src.config import Config
        print_test("Import src.config", True)
        tests_passed += 1
    except Exception as e:
        print_test("Import src.config", False, str(e))
    
    try:
        tests_total += 1
        from src.logger import EventLogger
        print_test("Import src.logger", True)
        tests_passed += 1
    except Exception as e:
        print_test("Import src.logger", False, str(e))
    
    try:
        tests_total += 1
        from src.alerts import AlertManager
        print_test("Import src.alerts", True)
        tests_passed += 1
    except Exception as e:
        print_test("Import src.alerts", False, str(e))
    
    try:
        tests_total += 1
        from src.detector import BabyWatcher
        print_test("Import src.detector", True)
        tests_passed += 1
    except Exception as e:
        print_test("Import src.detector", False, str(e))
    
    print(f"\n  Result: {tests_passed}/{tests_total} imports passed")
    return tests_passed == tests_total


def test_configuration():
    """Test configuration loading"""
    print_header("⚙️  Testing Configuration")
    
    try:
        from src.config import Config
        
        # Test config file existence
        if not os.path.exists("config.yaml"):
            print_test("Config file exists", False, "config.yaml not found")
            return False
        
        print_test("Config file exists", True)
        
        # Test config loading
        config = Config("config.yaml")
        print_test("Load config.yaml", True)
        
        # Test getting values
        img_size = config.get("detection.img_size")
        print_test(f"Get detection.img_size={img_size}", img_size == 640)
        
        conf_thresh = config.get("detection.conf_thresh")
        print_test(f"Get detection.conf_thresh={conf_thresh}", conf_thresh == 0.4)
        
        # Test getting section
        detection_config = config.get_dict("detection")
        print_test("Get detection section", len(detection_config) > 0)
        
        return True
    
    except Exception as e:
        print_test("Configuration tests", False, str(e))
        return False


def test_logger():
    """Test event logger"""
    print_header("📊 Testing Event Logger")
    
    try:
        from src.logger import EventLogger
        
        # Create test logger
        logger = EventLogger("test_logs", "test_events.csv")
        print_test("Initialize EventLogger", True, f"Log path: {logger.log_path}")
        
        # Test logging events
        logger.log_event(
            status="HAND_TO_MOUTH",
            duration=2.5,
            hand_mouth_distance=40.0,
            hand_object_distance=999.0,
            source="test_camera:0",
            device="CPU",
            platform="windows",
            notes="Test event"
        )
        print_test("Log HAND_TO_MOUTH event", True)
        
        logger.log_event(
            status="OBJECT_TO_MOUTH",
            duration=5.0,
            hand_mouth_distance=35.0,
            hand_object_distance=55.0,
            frame_saved=True,
            source="test_video.mp4",
            device="CPU",
            platform="windows",
            notes="Test danger event"
        )
        print_test("Log OBJECT_TO_MOUTH event", True)
        
        # Test file existence
        import time
        time.sleep(0.5)
        if os.path.exists(logger.log_path):
            print_test("CSV file created", True, f"File: {logger.log_path}")
        else:
            print_test("CSV file created", False)
        
        # Test statistics
        stats = logger.get_daily_stats()
        print_test("Get daily statistics", True, f"Total events: {stats['total_events']}")
        
        return True
    
    except Exception as e:
        print_test("Logger tests", False, str(e))
        return False


def test_alerts():
    """Test alert system"""
    print_header("🔔 Testing Alert System")
    
    try:
        from src.alerts import SoundAlert, EmailAlert, WebhookAlert, AlertManager
        
        # Test SoundAlert
        sound_alert = SoundAlert(enabled=False)  # Disabled for testing
        print_test("Initialize SoundAlert", True, f"Cooldown: {sound_alert.cooldown}s")
        
        # Test EmailAlert
        email_alert = EmailAlert(enabled=False)
        print_test("Initialize EmailAlert", True, f"Threshold: {email_alert.alert_threshold}s")
        
        # Test WebhookAlert
        webhook_alert = WebhookAlert(enabled=False)
        print_test("Initialize WebhookAlert", True, f"Cooldown: {webhook_alert.webhook_cooldown}s")
        
        # Test AlertManager
        config = {
            'enable_sound': False,
            'enable_email': False,
            'enabled': False
        }
        manager = AlertManager(config)
        print_test("Initialize AlertManager", True, str(manager))
        
        return True
    
    except Exception as e:
        print_test("Alert tests", False, str(e))
        return False


def test_utilities():
    """Test utility functions"""
    print_header("🛠️  Testing Utility Functions")
    
    try:
        from src.utils import distance, box_center, calculate_shoulder_width
        
        # Test distance calculation
        p1 = np.array([0, 0])
        p2 = np.array([3, 4])
        dist = distance(p1, p2)
        print_test(f"Distance calculation", np.isclose(dist, 5.0), f"Distance: {dist:.2f}")
        
        # Test box center
        box = (0, 0, 10, 10)
        center = box_center(box)
        print_test("Box center calculation", np.allclose(center, [5, 5]), f"Center: {center}")
        
        # Test shoulder width
        left_shoulder = np.array([100, 150])
        right_shoulder = np.array([200, 150])
        width = calculate_shoulder_width(left_shoulder, right_shoulder)
        print_test("Shoulder width calculation", width == 100.0, f"Width: {width:.2f}")
        
        return True
    
    except Exception as e:
        print_test("Utility tests", False, str(e))
        return False


def test_detector():
    """Test BabyWatcher detector (without YOLO models)"""
    print_header("🎯 Testing BabyWatcher Detector")
    
    try:
        from src.detector import BabyWatcher
        
        # Test initialization (this might fail if models not downloaded)
        print("  Initializing BabyWatcher...")
        print("  ⏳ Loading YOLO models (this may take a moment)...")
        
        try:
            watcher = BabyWatcher("config.yaml")
            print_test("Initialize BabyWatcher", True)
            
            # Test basic attributes
            print_test("Check img_size attribute", hasattr(watcher, 'img_size'))
            print_test("Check logger attribute", hasattr(watcher, 'logger'))
            print_test("Check alert_manager attribute", hasattr(watcher, 'alert_manager'))
            
            return True
        
        except Exception as e:
            if "yolo26n" in str(e).lower():
                print_test("Initialize BabyWatcher", False, 
                          "YOLO models not downloaded. Run: pip install -U ultralytics")
            else:
                print_test("Initialize BabyWatcher", False, str(e))
            return False
    
    except Exception as e:
        print_test("Detector tests", False, str(e))
        return False


def create_test_image():
    """Create a simple test image"""
    print_header("📷 Creating Test Image")
    
    try:
        import cv2
        
        # Create simple test image
        test_image = np.zeros((640, 640, 3), dtype=np.uint8)
        
        # Draw some shapes
        cv2.circle(test_image, (320, 320), 100, (0, 255, 0), -1)  # Green circle
        cv2.rectangle(test_image, (100, 100), (200, 200), (0, 0, 255), -1)  # Red square
        
        # Save image
        test_image_path = "test_image.jpg"
        cv2.imwrite(test_image_path, test_image)
        
        print_test("Create test image", os.path.exists(test_image_path), 
                  f"File: {test_image_path}")
        
        return test_image_path
    
    except Exception as e:
        print_test("Create test image", False, str(e))
        return None


def run_all_tests():
    """Run all tests"""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*15 + "🧪 BabyWatcher System Test Suite" + " "*20 + "║")
    print("║" + " "*68 + "║")
    print("║" + f" Version: 1.0.0 | Date: {time.strftime('%Y-%m-%d %H:%M:%S')}" + " "*30 + "║")
    print("╚" + "="*68 + "╝")
    
    results = {}
    
    # Run all tests
    results['Imports'] = test_imports()
    results['Configuration'] = test_configuration()
    results['Logger'] = test_logger()
    results['Alerts'] = test_alerts()
    results['Utilities'] = test_utilities()
    results['Detector'] = test_detector()
    
    # Summary
    print_header("📈 Test Summary")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, passed_flag in results.items():
        status_icon = "✅" if passed_flag else "❌"
        print(f"  {status_icon} {test_name:<40} {'PASSED' if passed_flag else 'FAILED'}")
    
    print(f"\n  Total: {passed}/{total} test suites passed")
    
    if passed == total:
        print("\n  🎉 All tests passed! System is ready to use.")
    else:
        print(f"\n  ⚠️  {total - passed} test(s) failed. Please check the output above.")
    
    print("\n" + "="*70)
    print("  Next Steps:")
    print("  1. Run: python main.py <input.mp4 or input.jpg>")
    print("  2. Check logs in: logs/events_log.csv")
    print("  3. View system log in: logs/babywatcher.log")
    print("="*70 + "\n")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
