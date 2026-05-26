# Hand-to-Object Algorithm Testing & Analysis Guide

## Overview

This guide explains how to test and analyze the Hand-to-Object and Object-to-Mouth algorithms using real camera feeds and image inputs.

## Quick Start

### Option 1: Real-Time Camera Testing (Recommended)

```bash
# Start real-time testing with your camera
python test_hand_object_camera.py

# Test with specific camera (if you have multiple)
python test_hand_object_camera.py --camera 1

# Test for limited duration (e.g., 30 seconds)
python test_hand_object_camera.py --duration 30
```

### Option 2: Detailed Algorithm Analysis

```bash
# Interactive analysis mode
python analyze_hand_object_algorithm.py --interactive

# Analyze specific image
python analyze_hand_object_algorithm.py --image path/to/image.jpg
```

---

## Test Scenarios

### Scenario 1: Hand Near Mouth (HAND_TO_MOUTH)

**Setup:** Position your hand near your mouth within camera view

**Expected Results:**
- ✅ Pose detected: Yes
- ✅ Status: HAND_TO_MOUTH
- ✅ Hand-to-Mouth Distance: < threshold (< 50px typically)
- ✅ Audio alert: Yes (beep sound)

**Metrics to Watch:**
```
Hand-to-Mouth Distance: 20-50px (depends on distance)
Threshold: ~45px (0.9 × shoulder width)
Status: 🚨 HAND_TO_MOUTH
```

### Scenario 2: Hand Holding Object (OBJECT_TO_MOUTH)

**Setup:** Hold an object (toy, spoon, etc.) near your mouth

**Expected Results:**
- ✅ Pose detected: Yes
- ✅ Objects detected: Yes (≥1)
- ✅ Status: OBJECT_TO_MOUTH
- ✅ Hand-to-Object Distance: < threshold (< 25px typically)
- ✅ Audio alert: Critical (double beep)

**Metrics to Watch:**
```
Hand-to-Object Distance: 0-10px (holding) or 10-25px (near)
Status of Object: HOLDING or NEAR
Hand-to-Object Threshold: ~40px (0.8 × shoulder width)
```

### Scenario 3: Safe Position

**Setup:** Hand away from mouth, no objects in hand

**Expected Results:**
- ✅ Pose detected: Yes
- ✅ Status: SAFE
- ✅ Hand-to-Mouth Distance: > threshold
- ✅ Hand-to-Object Distance: > threshold (if objects present)
- ✅ Audio alert: No

**Metrics to Watch:**
```
Hand-to-Mouth Distance: 100+ px
Hand-to-Object Distance: 50+ px
Status: ✅ SAFE
```

### Scenario 4: Multiple Objects

**Setup:** Multiple objects in frame, hand approaching one

**Expected Results:**
- ✅ Objects detected: 2+ 
- ✅ Nearest object tracked
- ✅ Distance calculated to nearest only
- ✅ Alert triggered if approaching nearest object

**Metrics to Watch:**
```
Objects: 3-5
Nearest Object Distance: (variable)
Algorithm: Uses nearest object for decision
```

---

## Real-Time Camera Testing

### Controls While Running

| Key | Function |
|-----|----------|
| `q` | Quit application |
| `p` | Print current metrics |
| `r` | Reset metrics history |
| `s` | Save current frame to file |
| `d` | Toggle debug information display |

### Display Elements

When running with debug enabled, you'll see:

```
Status: HAND_TO_MOUTH
Pose: YES
Objects: 1
H-M Distance: 42.5px
H-O Distance: 15.3px
H-M Threshold: 54.0px
H-O Threshold: 43.2px
Shoulder Width: 120.0px
Frame: 152

[Color coding in display:]
Green: SAFE, Pose detected, threshold lines
Orange: Distance lines, H-M
Red: H-O distances, Objects
```

### Output Files

When you press 's' to save frames:
- File naming: `test_frame_<timestamp>.jpg`
- Includes all visualization
- Shows metrics and distances drawn on frame

---

## Detailed Algorithm Analysis

### What Gets Analyzed

The analysis script breaks down the algorithm into steps:

1. **Shoulder Width Calculation**
   - Measures distance between shoulders
   - Used for dynamic threshold calculation

2. **Dynamic Threshold Calculation**
   - H-M Threshold = shoulder_width × 0.9
   - H-O Threshold = shoulder_width × 0.8
   - Adapts to body size

3. **Hand-to-Mouth Distance (Euclidean)**
   - Calculates distance from wrist to nose
   - Uses minimum of left/right wrist
   - Compares with H-M threshold

4. **Hand-to-Object Distance (Boundary-Based)**
   - Finds nearest object
   - Calculates distance from hand to nearest boundary point
   - Compares with H-O threshold

### Sample Analysis Output

```
Frame 1 Analysis
════════════════════════════════════════════════════════════

✅ Pose Detected - 17 keypoints

📍 Key Positions:
  Nose: (320.5, 240.2)
  Left Wrist: (250.3, 350.1)
  Right Wrist: (390.7, 355.2)
  Left Shoulder: (270.1, 150.3)
  Right Shoulder: (370.9, 148.7)

────────────────────────────────────────────────────────────
STEP 1: Calculate Shoulder Width (for dynamic threshold)
────────────────────────────────────────────────────────────
  Formula: shoulder_width = distance(left_shoulder, right_shoulder)
  Result: 100.8 pixels

────────────────────────────────────────────────────────────
STEP 2: Calculate Dynamic Thresholds
────────────────────────────────────────────────────────────
  Hand-to-Mouth Threshold = 100.8 × 0.9 = 90.7 pixels
  Hand-to-Object Threshold = 100.8 × 0.8 = 80.6 pixels

────────────────────────────────────────────────────────────
STEP 3: Calculate Hand-to-Mouth Distance (Euclidean)
────────────────────────────────────────────────────────────
  Left Wrist to Nose Distance: 125.3 pixels
  Right Wrist to Nose Distance: 95.2 pixels
  Minimum (used for detection): 95.2 pixels
  Decision: 95.2 > 90.7 → ✅ SAFE (Hand-to-Mouth)

────────────────────────────────────────────────────────────
STEP 4: Hand-to-Object Analysis (Boundary-Based Distance)
────────────────────────────────────────────────────────────
  Objects Found: 1
  Selected Hand Position: Right (390.7, 355.2)
  
  Nearest Object (Index 0):
    Bounding Box: [x=350.0, y=200.0, width=80.0, height=100.0]
  
  Boundary Distance Calculation:
    Clamping X: clamp(390.7, 350.0, 430.0) = 430.0
    Clamping Y: clamp(355.2, 200.0, 300.0) = 300.0
    Closest Point on Boundary: (430.0, 300.0)
    Distance: 78.4 pixels
    Decision: 78.4 < 80.6 → 🚨 OBJECT_TO_MOUTH
```

---

## Interpretation Guide

### Hand-to-Mouth Distance

```
0-30px    → 🚨 CRITICAL: Hand very close to mouth
30-50px   → ⚠️  WARNING: Hand approaching mouth
50-100px  → 🟡 CAUTION: Hand getting closer
100+px    → ✅ SAFE: Hand far from mouth
```

### Hand-to-Object Distance

```
0-10px    → 🚨 HOLDING: Clearly holding/grasping object
10-25px   → ⚠️  NEAR: Hand very close to object
25-50px   → 🟡 APPROACHING: Hand moving toward object
50+px     → ✅ SAFE: Hand far from object
```

### Shoulder Width Interpretation

```
60-80px   → Small child (6-9 months)
80-100px  → Toddler (12-18 months)
100-130px → Older toddler (18-24 months)
130+px    → Older child

Purpose: Adapt thresholds to child's size automatically
```

---

## Troubleshooting

### Issue: "Cannot open camera"

**Solution:**
```bash
# Check available cameras
# Try camera index 1, 2, etc.
python test_hand_object_camera.py --camera 1
```

### Issue: "No pose detected"

**Causes:**
- Camera angle too high/low
- Poor lighting
- Person not visible in frame
- Model confidence threshold too high

**Solutions:**
- Adjust camera position
- Improve lighting conditions
- Ensure full body is visible
- Stand at appropriate distance (1-3 meters)

### Issue: Objects not detected

**Causes:**
- Object too small or too large
- Poor object appearance
- Object similar color to background
- Detection confidence too high

**Solutions:**
- Use clear, distinct objects
- Ensure good contrast
- Try different objects
- Reduce detection confidence threshold in config.yaml

### Issue: Inaccurate distance measurements

**Causes:**
- Camera distortion
- Different pose perspectives
- Object position ambiguity

**Solutions:**
- Calibrate camera if possible
- Test from different angles
- Use multiple test scenarios
- Check shoulder width calculation

---

## Advanced Testing

### Batch Processing Multiple Images

```python
from analyze_hand_object_algorithm import AlgorithmAnalyzer
from pathlib import Path

analyzer = AlgorithmAnalyzer()

# Analyze multiple images
image_dir = Path('test_images')
for idx, image_path in enumerate(sorted(image_dir.glob('*.jpg')), 1):
    frame = cv2.imread(str(image_path))
    analyzer.analyze_frame(frame, frame_num=idx)

# Compare results
analyzer.print_comparison(analyzer.analysis_data)

# Export results
analyzer.export_analysis()
```

### Continuous Monitoring

```bash
# Run for 5 minutes and collect metrics
python test_hand_object_camera.py --duration 300

# Then press 'p' every 30 seconds to print metrics
# Press 'q' to exit and see summary
```

### Performance Analysis

Monitor in real-time:
- FPS (frames per second)
- Detection accuracy
- Distance calculation stability
- Response time to danger

---

## Expected Results

### Accuracy Targets

| Scenario | Expected Accuracy |
|----------|-------------------|
| Safe detection | 95%+ |
| Hand-to-mouth detection | 88-91% |
| Object detection | 87-90% |
| Distance accuracy | ±5-10% error |

### Performance Metrics

| Metric | Target |
|--------|--------|
| Detection FPS | 15-25 FPS |
| Latency | < 500ms |
| CPU Usage | 40-70% |
| Memory | 800-1200MB |

---

## Logging and Analysis

### Check Logs

```bash
# View all detection logs
tail -f logs/babywatcher.log

# View only detection changes
tail -f logs/babywatcher.log | grep -E "HAND_TO_MOUTH|OBJECT_TO_MOUTH"

# View event log CSV
cat logs/events_log.csv | tail -20
```

### CSV Event Log Format

```csv
timestamp,status,duration_seconds,hand_mouth_distance,hand_object_distance,frame_saved,notes
2026-05-26 10:30:15.123,HAND_TO_MOUTH,2.5,42.5,85.1,true,Hand near mouth
2026-05-26 10:30:20.456,OBJECT_TO_MOUTH,4.2,15.3,25.7,true,Holding object
```

---

## Common Test Patterns

### Test 1: Progressive Approach

1. Hand far from mouth (30+ seconds) → SAFE
2. Slowly bring hand closer (20 seconds) → transition point
3. Hand very close to mouth (20 seconds) → HAND_TO_MOUTH
4. Move hand away slowly (20 seconds) → transition back to SAFE

**Expected:** Clear transition at threshold boundary

### Test 2: Object Holding

1. Hold object far from mouth (15 seconds) → SAFE
2. Bring object to mouth level (15 seconds) → OBJECT_TO_MOUTH
3. Move object away (15 seconds) → SAFE
4. Repeat with different objects (30 seconds) → consistent detection

**Expected:** Reliable object detection and distance calculation

### Test 3: Multi-Object Scenario

1. Place multiple objects in frame (no hand contact)
2. Approach first object (should calculate to nearest)
3. Switch to different object
4. Hand movement between objects

**Expected:** Always tracks nearest object correctly

---

## Tips for Accurate Testing

✅ **Best Practices:**
- Use good lighting (natural light preferred)
- Wear contrasting clothing if possible
- Maintain stable camera position
- Test multiple scenarios and times
- Save test frames for later review
- Document observations

❌ **Avoid:**
- Poor lighting conditions
- Rapid camera movements
- Objects with similar color to skin
- Testing only one scenario
- Changes in camera height mid-test

---

## Export and Report

### Generate Analysis Report

```bash
# Analyze single image
python analyze_hand_object_algorithm.py --image test_frame.jpg

# This will:
# 1. Show detailed step-by-step analysis
# 2. Print all distance calculations
# 3. Explain algorithm decisions
# 4. Export JSON report
```

### Analysis Output Files

- `analysis_<timestamp>.json` - Full analysis data
- `test_frame_<timestamp>.jpg` - Saved test frames with visualization

---

## Success Criteria Checklist

✅ **Algorithm is working correctly if:**
- [ ] Pose detection works in various lighting
- [ ] Distance calculations are consistent
- [ ] Threshold values adjust with pose size
- [ ] Hand-to-mouth detection triggers correctly
- [ ] Hand-to-object detection works with various objects
- [ ] Multiple objects are handled properly
- [ ] FPS is 15+ on your hardware
- [ ] False positives are rare (< 5%)
- [ ] False negatives are minimal (< 10%)

---

## Next Steps

1. **Run real-time test:** `python test_hand_object_camera.py`
2. **Test different scenarios** (mouth, objects, safe positions)
3. **Analyze detailed results:** `python analyze_hand_object_algorithm.py --interactive`
4. **Review metrics** and compare with expectations
5. **Adjust config** if needed (thresholds, confidence)
6. **Document findings** for your report

---

**Ready to test? Start with:**
```bash
python test_hand_object_camera.py
```

Good luck! 🚀
