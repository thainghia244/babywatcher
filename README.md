````markdown
# 👶 BabyWatcher - AI Baby Safety Detection System

Advanced AI-powered system to detect and alert when a baby performs dangerous actions like hand-to-mouth or object-to-mouth behaviors.

## 🎯 Features

- **Real-time Detection**: Uses YOLO pose estimation and object detection
- **Hand-to-Mouth Detection**: Alerts when baby brings hand close to mouth
- **Object-to-Mouth Detection**: Detects when baby holds or brings objects to mouth
- **Smart Alerts**: 
  - 🔊 Sound alerts with increasing urgency
  - 📧 Email notifications
  - 🔗 Webhook integration
- **Event Logging**: CSV logs of all dangerous events
- **Daily Statistics**: Track safety metrics per day
- **Dynamic Configuration**: YAML-based configuration management
- **Performance Monitoring**: FPS counter and performance metrics
- **Multi-format Support**: Works with images, videos, and live streams

## 📋 Requirements

- Python 3.8+
- YOLO models (yolo26n-pose.pt, yolo26n.pt)
- OpenCV
- NumPy
- PyYAML

## 🚀 Installation

### 1. Clone Repository
```bash
git clone https://github.com/thainghia244/babywatcher.git
cd babywatcher
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Download YOLO Models
```bash
# Models will be auto-downloaded on first run, or manually download:
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n-pose.pt
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt
```

## ⚙️ Configuration

Edit `config.yaml` to customize:

```yaml
detection:
  img_size: 640                    # Image size for detection
  conf_thresh: 0.4                # Confidence threshold
  hand_mouth_thresh: 45           # Hand-to-mouth distance threshold
  hand_obj_thresh: 60             # Hand-to-object distance threshold
  dynamic_threshold: true         # Use dynamic thresholds based on person size

alerts:
  enable_sound: true              # Enable sound alerts
  enable_email: false             # Enable email notifications
  enable_logs: true               # Enable event logging
  danger_duration_threshold: 3.0  # Alert after 3 seconds of danger

logging:
  log_dir: "logs"                 # Directory for logs
  log_file: "events_log.csv"      # CSV file for events
  save_danger_clips: true         # Save video clips of dangerous events
```

## 💻 Usage

### Process Image
```bash
python main.py image.jpg
```

### Process Video
```bash
python main.py video.mp4
```

### Save Output
```bash
python main.py video.mp4 -o output.mp4
```

### View Daily Statistics
```bash
python main.py dummy.mp4 -s 2026-05-11
```

### Custom Configuration
```bash
python main.py video.mp4 -c custom_config.yaml
```

## 🎬 Example: Python Script

```python
from src.detector import BabyWatcher

# Initialize
watcher = BabyWatcher(config_path="config.yaml")

# Process video
watcher.process_video("input.mp4", "output.mp4")

# Get statistics
stats = watcher.get_stats("2026-05-11")
print(f"Total events: {stats['total_events']}")
print(f"Danger time: {stats['total_danger_time']:.2f}s")
```

## 📊 Output Files

### Event Log (logs/events_log.csv)
```csv
timestamp,status,duration_seconds,hand_mouth_distance,hand_object_distance,frame_saved,notes
2026-05-11 10:30:45,HAND_TO_MOUTH,2.34,45.2,999.0,0,
2026-05-11 10:31:12,OBJECT_TO_MOUTH,5.67,38.1,55.3,1,High risk
```

### System Log (logs/babywatcher.log)
```
2026-05-11 10:30:45 - BabyWatcher - WARNING - Event: HAND_TO_MOUTH | Duration: 2.34s
```

## 🔔 Alert Types

### Sound Alerts
- ⚠️ Single beep (800Hz) for "Hand to Mouth"
- 🚨 Double beep (1000Hz) for "Object to Mouth"

### Email Alerts (Optional)
Configure in `config.yaml`:
```yaml
email:
  enabled: true
  smtp_server: "smtp.gmail.com"
  sender_email: "your_email@gmail.com"
  sender_password: "your_app_password"
  recipient_email: "parent@example.com"
```

### Webhook Alerts (Optional)
```yaml
webhook:
  enabled: true
  url: "https://your-webhook-url.com/alert"
```

## 📈 Thresholds Explanation

### Dynamic Thresholds
- **Hand-Mouth Distance**: `shoulder_width × 0.9`
- **Hand-Object Distance**: `shoulder_width × 0.8`

This adapts to the baby's size automatically!

### Danger Duration
- Alerts trigger when dangerous behavior persists > configured threshold
- Default: 3 seconds

## 🔍 Status Meanings

| Status | Color | Meaning |
|--------|-------|---------|
| SAFE | 🟢 Green | No danger detected |
| HAND_TO_MOUTH | 🟡 Yellow | Hand near mouth (warning) |
| OBJECT_TO_MOUTH | 🔴 Red | Object near mouth (critical) |

## 🐛 Troubleshooting

### Models not downloading
```bash
# Manual download
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n-pose.pt -O yolo26n-pose.pt
```

### CUDA/GPU issues
Set in `config.yaml`:
```yaml
models:
  device: "cpu"  # Use CPU instead of GPU
```

### Low FPS
- Reduce `img_size` in config.yaml (e.g., 480)
- Lower `conf_thresh` to skip difficult frames
- Use CPU version without GPU overhead

## 📁 Project Structure

```
babywatcher/
├── src/
│   ├── __init__.py
│   ├── detector.py          # Main detection engine
│   ├── config.py            # Configuration management
│   ├── logger.py            # Event logging
│   ├── alerts.py            # Alert system
│   └── utils.py             # Utility functions
├── config.yaml              # Configuration file
├── requirements.txt         # Dependencies
├── setup.py                 # Package setup
├── main.py                  # Entry point
└── README.md               # This file
```

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📝 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- Built with [Ultralytics YOLO](https://github.com/ultralytics/ultralytics)
- Pose detection powered by YOLOv8-Pose
- Object detection powered by YOLOv8

## 📧 Support

For issues and questions:
- 📝 Open an issue on GitHub
- 💬 Check existing discussions
- 📧 Contact: your.email@example.com

---

**Stay safe! 👶💙**
````
