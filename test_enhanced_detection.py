"""Test enhanced detection with hand and face models"""

import cv2
import numpy as np
from src.detector import BabyWatcher
from src.config import Config

# Initialize detector
print("🚀 Testing Enhanced Detection System...")
detector = BabyWatcher("config.yaml")

# Test with existing safe.jpg
test_image_path = "images/safe.jpg"

try:
    print(f"\n📸 Processing {test_image_path}...")
    result = detector.process_image(test_image_path, output_path="output_enhanced_test.jpg")
    
    print(f"✅ Image processed successfully!")
    print(f"💾 Output saved to output_enhanced_test.jpg")
        
except Exception as e:
    print(f"❌ Error during testing: {e}")
    import traceback
    traceback.print_exc()

print("\n✨ Test completed!")

