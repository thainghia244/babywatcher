#!/usr/bin/env python3
"""Quick test to verify config loading"""

from src.config import Config
from src.detector import BabyWatcher

# Test 1: Load config directly
print("=" * 60)
print("TEST 1: Direct config loading")
print("=" * 60)
c = Config('config.yaml')
conf_thresh = c.get('detection.conf_thresh', 0.4)
print(f"Config 'detection.conf_thresh': {conf_thresh}")

# Test 2: Load BabyWatcher and check its settings
print("\n" + "=" * 60)
print("TEST 2: BabyWatcher detector settings")
print("=" * 60)
try:
    detector = BabyWatcher('config.yaml')
    print(f"Detector 'conf_thresh': {detector.conf_thresh}")
    print(f"Detector 'small_object_conf_thresh': {detector.small_object_conf_thresh}")
    print(f"Detector 'hand_mouth_multiplier': {detector.hand_mouth_multiplier}")
    print(f"Detector 'hand_object_multiplier': {detector.hand_object_multiplier}")
except Exception as e:
    print(f"Error loading detector: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("✅ Configuration test complete")
print("=" * 60)
