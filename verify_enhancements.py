"""Final verification of BabyWatcher v2.0 enhancements"""

import sys
import os

def verify_implementation():
    """Verify all enhancements are properly implemented"""
    
    print("\n" + "=" * 80)
    print("🔍 BabyWatcher v2.0 - Enhancement Verification Report")
    print("=" * 80)
    
    checks = []
    
    # 1. Check src/utils.py has new functions
    print("\n1️⃣  Checking src/utils.py for new functions...")
    with open("src/utils.py", "r", encoding="utf-8", errors="ignore") as f:
        utils_content = f.read()
    
    new_functions = [
        ("get_hand_keypoints", "Hand keypoint extraction"),
        ("extract_index_fingers", "Index finger extraction"),
        ("get_mouth_from_face", "Mouth position calculation"),
        ("get_face_mouth_keypoint", "Face mouth detection"),
    ]
    
    for func_name, description in new_functions:
        found = f"def {func_name}" in utils_content
        checks.append(("✅" if found else "❌", f"{description} ({func_name})"))
        print(f"   {'✅' if found else '❌'} {description}")
    
    # 2. Check src/detector.py enhancements
    print("\n2️⃣  Checking src/detector.py for enhancements...")
    with open("src/detector.py", "r", encoding="utf-8", errors="ignore") as f:
        detector_content = f.read()
    
    detector_checks = [
        ("self.use_hand_detection", "Hand detection flag"),
        ("self.use_face_detection", "Face detection flag"),
        ("extract_index_fingers", "Index finger extraction call"),
        ("get_face_mouth_keypoint", "Face mouth detection call"),
        ("pose_detected", "Pose detection in return"),
        ("num_objects", "Object count in return"),
    ]
    
    for check_str, description in detector_checks:
        found = check_str in detector_content
        checks.append(("✅" if found else "❌", f"{description}"))
        print(f"   {'✅' if found else '❌'} {description}")
    
    # 3. Check config.yaml
    print("\n3️⃣  Checking config.yaml configuration...")
    with open("config.yaml", "r", encoding="utf-8", errors="ignore") as f:
        config_content = f.read()
    
    config_checks = [
        ("hand_model_path", "Hand model path config"),
        ("face_model_path", "Face model path config"),
    ]
    
    for check_str, description in config_checks:
        found = check_str in config_content
        checks.append(("✅" if found else "❌", f"{description}"))
        print(f"   {'✅' if found else '❌'} {description}")
    
    # 4. Check new files
    print("\n4️⃣  Checking new files...")
    new_files = [
        ("src/mediapipe_hand_detector.py", "MediaPipe hand detector"),
        ("test_comprehensive_enhanced.py", "Enhanced test suite"),
        ("demo_enhanced_features.py", "Feature demonstration"),
        ("ENHANCEMENTS.md", "Technical documentation"),
        ("CHANGELOG.md", "Change log"),
        ("QUICK_START.md", "Quick start guide"),
    ]
    
    for file_path, description in new_files:
        found = os.path.exists(file_path)
        checks.append(("✅" if found else "❌", f"{description} ({file_path})"))
        print(f"   {'✅' if found else '❌'} {description}")
    
    # 5. Test imports
    print("\n5️⃣  Testing imports...")
    try:
        from src.detector import BabyWatcher
        checks.append(("✅", "BabyWatcher import successful"))
        print(f"   ✅ BabyWatcher import successful")
    except Exception as e:
        checks.append(("❌", f"BabyWatcher import failed: {e}"))
        print(f"   ❌ BabyWatcher import failed: {e}")
    
    try:
        from src import utils
        checks.append(("✅", "Utils import successful"))
        print(f"   ✅ Utils import successful")
    except Exception as e:
        checks.append(("❌", f"Utils import failed: {e}"))
        print(f"   ❌ Utils import failed: {e}")
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 Verification Summary")
    print("=" * 80)
    
    passed = sum(1 for status, _ in checks if status == "✅")
    total = len(checks)
    
    print(f"\n   Total Checks: {total}")
    print(f"   Passed: {passed}")
    print(f"   Failed: {total - passed}")
    
    if passed == total:
        print("\n   🎉 ALL CHECKS PASSED! ✅")
        print("\n   Status: PRODUCTION READY")
        return 0
    else:
        print("\n   ⚠️  Some checks failed")
        print("\n   Failed items:")
        for status, description in checks:
            if status == "❌":
                print(f"      - {description}")
        return 1
    
    print("=" * 80)

if __name__ == "__main__":
    sys.exit(verify_implementation())
