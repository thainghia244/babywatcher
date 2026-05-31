#!/usr/bin/env python3
"""
Object Detection Test Guide - Test with Real Objects
This guide shows how to properly test object detection
"""

print("""
================================================================================
🎯 OBJECT DETECTION TEST - STEP 2
================================================================================

Your system is ready! Now let's validate object detection with REAL ITEMS.

📋 WHAT TO DO:
1. Prepare test objects (clearly visible items in frame)
2. Run the test script
3. Show objects to camera
4. Monitor detection results

================================================================================
🎨 RECOMMENDED TEST OBJECTS:
================================================================================

✅ BEST OBJECTS (Easy to detect):
   □ Bottle (plastic or glass) - clearly defined edges
   □ Spoon or fork - common feeding items
   □ Cup or glass - typical baby hazards
   □ Toy block or ball - bright colors
   □ Remote control - metallic surface
   □ Credit card / Phone - rectangular shape

⚠️  AVOID (Hard to detect):
   ✗ White objects on white background
   ✗ Transparent plastic bags
   ✗ Very small items
   ✗ Same color as background

================================================================================
📸 TEST PROCEDURE:
================================================================================

STEP 1: Position Object in Camera
   • Hold object ~30cm (1 foot) from camera
   • Ensure good lighting (natural window light is best)
   • Place object clearly in center of frame
   • Object should be ~100-200px in view

STEP 2: Run Detection Test
   • Open NEW terminal (Ctrl+Shift+`)
   • Run: python debug_detection.py --camera 0 --duration 60
   • Show object to camera for 30 seconds
   • Then move object away

STEP 3: Check Results
   After test completes:
   • Look for "Object Detection Rate: X%"
   • If > 30%: ✅ Good detection
   • If < 30%: ⚠️ Need better lighting or object visibility

================================================================================
💡 TIPS FOR BETTER DETECTION:
================================================================================

🔆 LIGHTING:
   ✓ Use natural window light
   ✓ Avoid shadows on object
   ✓ Bright overhead lights help
   ✗ Dark room = hard to detect

📐 OBJECT POSITIONING:
   ✓ Center of frame (not edge)
   ✓ Fully visible (not partially cut off)
   ✓ At least 1/10 of frame size
   ✗ Too close (distorted)
   ✗ Too far (too small)

🎯 CONFIDENCE THRESHOLD:
   • During test, press 'c' to enable confidence adjustment
   • Use +/- keys to modify threshold
   • Lower threshold = more detections (but false positives)
   • Higher threshold = fewer detections (but more accurate)
   • Sweet spot: 0.15-0.25

================================================================================
🚀 QUICK START (Copy & Paste):
================================================================================

# Terminal 1: Monitor system (already running)
# python main.py camera

# Terminal 2: Test object detection
python debug_detection.py --camera 0 --duration 60

# Then show objects to camera during the test!

================================================================================
📊 EXPECTED RESULTS:
================================================================================

During test with visible objects (at confidence 0.25):
   • Pose Detection: 90-98% ✓
   • Object Detection: 40-80% (depends on object type)
   • If 0%: Check lighting or object visibility

After training custom model (Step 3):
   • Object Detection should improve to 70-85%+

================================================================================
❓ TROUBLESHOOTING:
================================================================================

Q: Object Detection still 0% even with objects?
A: • Lower confidence (press 'c' then '-' multiple times)
   • Try different object (brighter color)
   • Ensure object is in center of frame
   • Check lighting (move to bright area)
   • Object might be too small or too large

Q: How much smaller will detection be after training?
A: Typically 20-40% improvement after training on domain-specific data

Q: Do I need to train the custom model?
A: Optional but recommended:
   • Current model: Generic object detection
   • Custom model: Trained on baby-specific objects
   • Training takes: 20-30 minutes on CPU
   • Improvement: 20-40% better accuracy

================================================================================
🎬 NEXT STEPS:
================================================================================

1. ✅ DONE: Deployed main.py camera
2. 🔄 NOW: Test object detection with real items
3. ⏭️  AFTER: Train custom babyMonitor2 model (20 min)
4. ⏭️  FINAL: Configure email alerts

Ready? Open new terminal and run:
   python debug_detection.py --camera 0 --duration 60

================================================================================
""")
