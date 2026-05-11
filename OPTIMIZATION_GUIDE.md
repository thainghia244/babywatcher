# 🚀 BabyWatcher Optimizations Guide

## Overview
BabyWatcher has been optimized for **better performance, accuracy, and maintainability**. This document outlines all optimizations implemented.

---

## 🎯 Performance Optimizations

### 1. **Device Auto-Detection**
- Automatically detects GPU (CUDA) or uses CPU
- Configuration: `models.device: "auto"`
- Switch devices without code changes in `config.yaml`

```yaml
models:
  device: "auto"        # Auto-detect GPU/CPU
  half_precision: false # Enable FP16 for faster GPU inference
```

### 2. **Frame Skipping**
- Process every Nth frame to increase throughput
- Useful for real-time processing on slower hardware
- Configuration: `performance.skip_frames: N`

```yaml
performance:
  skip_frames: 0        # 0 = process all, 1 = skip every other frame
```

### 3. **FPS Monitoring**
- Real-time FPS tracking with moving average
- Monitors CPU and memory usage
- Configuration: `performance.track_fps: true`

```yaml
performance:
  track_fps: true       # Enable runtime FPS monitoring
```

### 4. **Model Optimization**
- Max detection limit to reduce processing
- Optional FP16 precision for GPU (requires GPU)
- Configuration: `models.max_det: 300`

```yaml
models:
  max_det: 300          # Limit objects per frame for speed
  half_precision: false # FP16 faster but less accurate on CPU
```

---

## 📊 Monitoring & Statistics

### PerformanceMonitor
Tracks:
- FPS (frames per second)
- Frame processing time
- CPU usage percentage
- Memory usage (MB)

### DetectionStats
Tracks:
- Total frames processed
- Pose detection rate
- Average objects per frame
- Danger detection rate

### Usage
```python
from src.detector import BabyWatcher

watcher = BabyWatcher("config.yaml")
# ... process frames ...
watcher.print_stats()  # Print statistics
```

---

## 🔧 Configuration Profiles

### Fast Mode (for CPU/slow hardware)
```yaml
detection:
  img_size: 480              # Smaller = faster
  conf_thresh: 0.5           # Higher = fewer detections

performance:
  skip_frames: 1             # Skip every other frame
  track_fps: true
```

### Balanced Mode (recommended)
```yaml
detection:
  img_size: 640              # Standard
  conf_thresh: 0.4           # Balanced

performance:
  skip_frames: 0             # Process all frames
  track_fps: true
```

### Accurate Mode (GPU recommended)
```yaml
detection:
  img_size: 1280             # Highest resolution
  conf_thresh: 0.3           # Catch more objects

models:
  device: "0"                # Use GPU
  half_precision: true       # Can use FP16

performance:
  skip_frames: 0
```

---

## 📈 Performance Metrics Explained

| Metric | Range | Target | Notes |
|--------|-------|--------|-------|
| FPS | 1-60+ | 10+ | Higher is better |
| Frame Time | 16-100ms | <100ms | Lower is better |
| Memory | 100-2000MB | <1000MB | Depends on image size |
| CPU % | 0-100 | <80% | Comfortable margin |

---

## 💡 Optimization Tips

### For CPU-only systems:
1. Reduce `img_size` to 480-640
2. Enable `skip_frames: 1` or `2`
3. Increase confidence threshold to 0.5

### For GPU systems:
1. Set `device: "0"` explicitly
2. Enable `half_precision: true` for 2x speedup
3. Increase `max_det` if needed (more objects)

### For Real-time processing:
1. Monitor FPS with `track_fps: true`
2. Use frame skipping if FPS < 1
3. Reduce image size if processing is bottleneck

---

## 📝 Code Changes Summary

### New Files
- `src/performance.py` - Performance monitoring & statistics

### Modified Files
- `config.yaml` - Added performance & model optimization settings
- `src/detector.py`:
  - Device auto-detection
  - Frame skipping support
  - Performance monitoring integration
  - Statistics tracking
  - New `print_stats()` method

---

## 🧪 Testing Optimizations

```bash
# Test with optimizations enabled
python main.py image.jpg

# Print statistics after processing
python -c "from src.detector import BabyWatcher; w = BabyWatcher(); w.print_stats()"
```

---

## 🎓 Best Practices

1. ✅ Start with **Balanced mode**
2. ✅ Monitor FPS regularly with `track_fps: true`
3. ✅ Adjust `skip_frames` based on FPS needs
4. ✅ Use GPU if available (`device: "auto"`)
5. ✅ Run `print_stats()` after processing batches
6. ✅ Set `half_precision: true` only on GPU

---

## 📚 Resources

- YOLO Optimization: https://docs.ultralytics.com/guides/optimizing-inference-speed/
- CUDA Setup: https://pytorch.org/get-started/locally/
- Profiling: Enable `enable_profiling: true` in config

---

**Last Updated:** May 11, 2026  
**Version:** 1.1 (Optimized)
