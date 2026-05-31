# 🔧 Fix Guide: Object Detection & Alert Issues

## 📋 Problem Summary (từ Debug Output)

```
Total Frames: 489
Pose Detection Rate: 96.7%         ✅ EXCELLENT
Object Detection Rate: 0.0%        ❌ PROBLEM
Hand-to-Mouth Alerts: 293          ⚠️ Triggering but maybe not correctly
Average H-M Distance: 199.8px      ⚠️ TOO FAR (should be <90px)
```

---

## 🎯 Root Causes Identified

### **Problem 1: Object Detection = 0%**
- **Cause**: Confidence threshold too high (0.4)
- **Effect**: Objects not meeting threshold are skipped
- **Solution**: Reduce confidence threshold to 0.25 (or lower to 0.15)

### **Problem 2: Hand-to-Mouth Threshold Too Strict**
- **Cause**: Multiplier 0.9 is too small, creating threshold of ~90px
- **Effect**: Tay phải gần miệng RẤT SÃT (impossible realistic scenario)
- **Solution**: Increase multiplier from 0.9 → 1.2

### **Problem 3: False Alert Triggering**
- **Cause**: Average distance 199.8px vs threshold 90px mismatch
- **Effect**: Alerts triggering even when hand is not near mouth
- **Solution**: Adjust thresholds (already done above)

---

## ✅ Changes Made

### **config.yaml Updates:**
```yaml
detection:
  conf_thresh: 0.25           # ← Changed from 0.4
  hand_mouth_multiplier: 1.2  # ← Changed from 0.9
  hand_object_multiplier: 1.0 # ← Changed from 0.8
  small_object_conf_thresh: 0.15  # ← Changed from 0.2
```

### **detector.py Updates:**
- Updated initialization to read multipliers from config
- Updated threshold calculation to use config values
- Now hand_mouth_thresh = shoulder_width × 1.2 (more lenient)

---

## 🧪 Testing Procedure

### **Step 1: Test Object Detection**

```bash
# Run object detection tester with adjustable confidence
python test_object_detection.py --camera 0 --duration 60
```

**Controls:**
- `'+'` / `'-'` - Adjust confidence up/down (0.0 - 1.0)
- `'d'` - Set to 0.1 (very low)
- `'m'` - Set to 0.3 (medium)
- `'h'` - Set to 0.6 (high)
- `'p'` - Print stats
- `'q'` - Quit

**What to do:**
1. Start with confidence at 0.25 (current default)
2. If no objects detected, press `'-'` to lower (0.20, 0.15, 0.10)
3. Find the confidence level where objects START to detect
4. That will be the optimal threshold

**Expected output:**
```
Frame 150:
  ✅ DETECTED: 2 objects
    - cup (0.45)
    - bottle (0.38)
```

---

### **Step 2: Test Hand-to-Mouth Detection**

```bash
# Run debug tool to see distance metrics
python debug_detection.py --camera 0 --duration 60
```

**During test:**
1. Place hand on table (SAFE) - should show distance 250+px
2. Bring hand closer to mouth (HAND_TO_MOUTH) - should show distance 80-150px
3. At lips (DANGER) - should show distance 0-50px

**Expected thresholds:**
- Shoulder width: ~100-120px
- H-M threshold: 100 × 1.2 = **120px** ← More lenient!
- H-O threshold: 100 × 1.0 = **100px**

**Controls:**
- `'d'` - Toggle distance display
- `'p'` - Print metrics
- `'q'` - Quit

---

### **Step 3: Full System Test**

```bash
python test_hand_object_camera.py --duration 90
```

**Test Scenarios:**
1. **SAFE**: Hand away from mouth → Status = SAFE
2. **HAND_TO_MOUTH**: Hand gần miệng → Status = HAND_TO_MOUTH → Alert
3. **OBJECT_TO_MOUTH**: Hold object gần miệng → Status = OBJECT_TO_MOUTH → Alert
4. **Mixture**: Switch between scenarios

**Controls:**
- `'p'` - Print metrics every 15s
- `'q'` - Quit

**Expected Alert Timing:**
- Danger must last > 3 seconds before alert (configurable)
- Alert triggers with sound/email/webhook

---

## 📊 Before vs After Comparison

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Object Detection | 0% | Should be 50%+ | +50%+ |
| Confidence Threshold | 0.40 | 0.25 | -0.15 |
| H-M Multiplier | 0.9 | 1.2 | +33% more lenient |
| H-O Multiplier | 0.8 | 1.0 | +25% more lenient |

---

## 🔍 Additional Tuning (If Needed)

### If objects still not detecting:
```bash
# Lower confidence even more in config.yaml
conf_thresh: 0.15  # or even 0.10
```

### If alerts triggering too much:
```bash
# Increase danger_duration_threshold
danger_duration_threshold: 5.0  # from 3.0 (require 5 seconds of danger)
```

### If alerts not triggering enough:
```bash
# Decrease danger_duration_threshold
danger_duration_threshold: 1.0  # from 3.0 (alert after 1 second)
```

### If hand-to-mouth too sensitive:
```bash
# Decrease multiplier (make threshold smaller)
hand_mouth_multiplier: 1.0  # from 1.2
```

---

## 📝 Configuration Template

**Optimal starting point for your camera setup:**

```yaml
detection:
  img_size: 640
  conf_thresh: 0.25           # ← Start here, adjust if needed
  hand_mouth_thresh: 45
  hand_obj_thresh: 60
  dynamic_threshold: true
  
  hand_mouth_multiplier: 1.2   # ← Adjust if too sensitive/insensitive
  hand_object_multiplier: 1.0
  
  small_object_conf_thresh: 0.15  # ← For very small objects
  inferred_object_distance_thresh: 25

alerts:
  danger_duration_threshold: 3.0  # ← Adjust alert delay
```

---

## 🚀 Quick Start After Changes

```bash
# 1. Test object detection (find optimal confidence)
python test_object_detection.py --camera 0 --duration 60

# 2. Update config.yaml if needed (different confidence)

# 3. Test full detection
python debug_detection.py --camera 0 --duration 60

# 4. Full system test
python test_hand_object_camera.py --duration 120

# 5. Real detection
python main.py camera
```

---

## 📋 Success Criteria

✅ Object detection working (>50% detection rate)
✅ Hand-to-mouth alert triggering when hand is actually near mouth
✅ Object-to-mouth alert triggering when holding object near mouth
✅ False positive rate <5%
✅ No alerts when hand is far from mouth

---

## 💡 Troubleshooting

### Objects detected at 0.1 but not at 0.25?
→ Objects too small or unclear → Lower conf_thresh in config

### No objects detected even at 0.1?
→ Objects not in COCO dataset → Use common objects (cup, bottle, spoon)
→ Check if yolo26n.pt file is valid

### Alerts triggering constantly?
→ Decrease hand_mouth_multiplier (make threshold smaller)
→ Increase danger_duration_threshold (require longer danger duration)

### Alerts never triggering?
→ Increase hand_mouth_multiplier (make threshold larger)
→ Decrease danger_duration_threshold (alert faster)
→ Hand not actually near mouth during test

---

## 🎯 Next Steps

1. Run `python test_object_detection.py --camera 0 --duration 60`
2. Report findings:
   - At what confidence level do objects start detecting?
   - How many frames have detections?
3. Adjust config.yaml if needed
4. Re-test with `python debug_detection.py --camera 0 --duration 60`
5. Run full test `python test_hand_object_camera.py --duration 90`

---

**Updated:** May 26, 2026  
**Status:** Configuration Updated & Testing Guide Ready  
**Next Action:** Run test_object_detection.py to find optimal confidence threshold
