# BabyWatcher

BabyWatcher is an AI-based baby safety monitoring system that analyzes video frames to detect potentially dangerous behaviors such as hand-to-mouth and object-to-mouth actions.

## What it does

- Detects a baby and surrounding objects from image, video, or camera input
- Estimates pose keypoints and analyzes hand, mouth, and object proximity
- Uses dynamic thresholds and temporal confirmation to reduce false alarms
- Logs dangerous events and can trigger sound, email, or webhook alerts

## Core workflow

1. Read a frame from an image, video, or camera stream
2. Run pose estimation and object detection
3. Analyze geometric relationships between hand, mouth, and nearby objects
4. Apply confirmation/history logic to confirm a dangerous event
5. Emit alerts and save event logs or clips

## Requirements

- Python 3.10+
- OpenCV
- PyTorch
- Ultralytics YOLO
- NumPy
- PyYAML

Install dependencies:

```bash
pip install -r requirements.txt
```

## Quick start

Run the detector on an image or video:

```bash
python main.py path/to/input.mp4
```

Use a custom configuration:

```bash
python main.py path/to/input.mp4 -c config.yaml
```

Show statistics for a given date:

```bash
python main.py path/to/input.mp4 -s 2026-08-01
```

## Configuration

The main settings are stored in [config.yaml](config.yaml). Key options include:

- detection.dynamic_threshold
- detection.confirmation_frames
- detection.proximity_history_window
- alerts.enable_sound
- logging.save_danger_clips

## Project structure

```text
babywatcher/
├── main.py
├── config.yaml
├── requirements.txt
├── src/
│   ├── detector.py
│   ├── config.py
│   ├── logger.py
│   ├── alerts.py
│   ├── performance.py
│   └── utils.py
└── README.md
```

## Notes

- MediaPipe-based hand detection has been removed from the default workflow.
- The system currently relies on pose + object detection and geometric analysis.

