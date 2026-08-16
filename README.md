# BabyWatcher

BabyWatcher is an AI-based infant safety monitoring system. It watches a camera/video/image feed, estimates body pose, detects nearby objects, and raises an alert when it detects a hand or object being brought close to a baby's mouth — the two behaviors most associated with choking risk.

This repository is the implementation behind a university thesis project (`BaoCaoDoAnTotNghiep_Full.md`, in Vietnamese). The thesis document is the authoritative source for design rationale, experiment methodology, and measured results — this README covers how to run and configure the code.

## What it does

- Detects a baby and nearby objects from a live camera, a video file, or a single image
- Estimates 17 COCO body keypoints (pose) to locate the wrists, shoulders, and mouth region
- Computes a **dynamic threshold** (scaled to shoulder width) instead of a fixed pixel distance, so it adapts to the child's size and distance from the camera
- Requires a signal to persist across several frames before confirming a danger state, to suppress single-frame noise
- Classifies each moment into one of three states: `SAFE`, `HAND_TO_MOUTH`, `OBJECT_TO_MOUTH`
- Lets a caregiver pre-register household hazards the object detector was never trained on (via camera capture or an existing photo), matched by visual similarity against what's near the child's hand
- Triggers sound and email alerts, logs every event to CSV, and saves both a snapshot image and a short video clip (with a few seconds of lead-up and trailing footage) for each dangerous event

## Core workflow

1. Read a frame from an image, video file, or camera stream
2. Run pose estimation and object detection on the frame
3. Compute hand↔mouth, hand↔object, and object↔mouth distances against dynamic, body-scaled thresholds
4. Require the signal to persist (multi-frame history + a minimum duration) before confirming a state change
5. If the held object matches a caregiver-registered hazard, reinforce the object-to-mouth signal and fast-track confirmation
6. Trigger alerts (sound/email), write the event to the log, and save an image + short video of the event

## Requirements

- Python 3.10+
- OpenCV, PyTorch, Ultralytics YOLO, NumPy, PyYAML (see `requirements.txt`)
- Windows: `tkinter` (ships with standard Python) is used for the "register from an existing photo" file picker

Install dependencies:

```bash
pip install -r requirements.txt
```

## Quick start

Run on a video file, a single image, or a live camera (`0`, `1`, `camera`, `cam`, `webcam`):

```bash
python main.py path/to/input.mp4
python main.py path/to/photo.jpg
python main.py 0
```

Save the fully annotated output alongside processing:

```bash
python main.py path/to/input.mp4 -o output.mp4
```

Use a different config file, or check logged statistics for a date:

```bash
python main.py path/to/input.mp4 -c config.yaml
python main.py path/to/input.mp4 -s 2026-08-01
```

> **Note on single-image mode:** processing one photo (`main.py photo.jpg`) skips the multi-frame confirmation that the live/video path relies on to suppress false alarms, so it is meaningfully more trigger-happy than continuous monitoring. Treat it as a quick debugging look at one frame, not as a way to measure system accuracy — see `BaoCaoDoAnTotNghiep_Full.md` section 5.1 for the measured gap (≈55–60% vs ≈72.7% accuracy on the same 121-image test set).

## Registering hazard objects

Before starting live monitoring, a caregiver can register objects the trained model doesn't know about (buttons, coins, lighters, medicine, etc.). Launching `main.py` with a display shows a start screen with three options: register via camera, register from an existing photo, and view/rename/delete already-registered objects. The same actions are available from the CLI:

```bash
python register_hazard_objects.py --camera 0
python register_hazard_objects.py --images photo1.jpg photo2.jpg
```

You draw the bounding box by hand (the object detector's own guess, if any, is shown only as a hint) — this is intentional, since the whole point of this feature is objects the detector was never trained to find on its own.

## Configuration

All tunable behavior lives in [config.yaml](config.yaml). Key sections:

| Section | Purpose |
|---|---|
| `detection.hand_mouth_multiplier`, `object_mouth_multiplier`, `object_hand_hold_multiplier` | The α coefficients that scale each distance threshold to shoulder width — see `BaoCaoDoAnTotNghiep_Full.md` section 3.2.4.2 for how these were chosen and their measured precision/recall trade-off |
| `detection.confirmation_frames`, `sustained_danger_duration` | How long/how many frames a signal must persist before it's confirmed |
| `detection.hazard_gallery_path`, `hazard_match_threshold` | Hazard gallery settings — see `src/hazard_gallery.py` |
| `alerts.danger_duration_threshold` | Delay before the audible/email alert fires (separate from, and later than, on-screen status confirmation) |
| `logging.save_danger_clips`, `save_danger_videos` | Evidence storage — a JPG snapshot and/or a short video per event |
| `email.*` | SMTP alert settings — **do not commit a real password here** (see Security below) |
| `hardware.platform` | `"desktop"` for a regular PC/laptop; Jetson Nano support exists in code but has not been run/measured on real Jetson hardware |

## Evaluating accuracy

`compare_fixed_thresholds.py` measures the SAFE/HAND_TO_MOUTH/OBJECT_TO_MOUTH confusion matrix against `ground_truth_manual.csv` (121 hand-labeled images in `image/`):

```bash
python compare_fixed_thresholds.py --image-dir image --ground-truth ground_truth_manual.csv --output-dir analysis/confusion_matrix_current
```

`alpha_grid_search.py` sweeps the α coefficients above one at a time and re-measures the confusion matrix for each value — this is what produced the precision/recall trade-off table in the thesis report. Past results are kept under `analysis/` for reference.

## Project structure

```text
babywatcher/
├── main.py                        # CLI entry point
├── config.yaml                    # All runtime configuration
├── requirements.txt
├── src/
│   ├── detector.py                # Core detection/decision pipeline
│   ├── config.py                  # YAML config loader
│   ├── logger.py                  # CSV event logging
│   ├── alerts.py                  # Sound/email alert manager
│   ├── performance.py             # FPS/perf tracking
│   ├── utils.py                   # Geometry, drawing, mouse-driven box selection
│   ├── hazard_gallery.py          # Few-shot hazard object matching (MobileNetV3 embeddings)
│   ├── hazard_manager.py          # View/rename/delete registered hazard objects (UI)
│   └── launch_screen.py           # Pre-monitoring start screen
├── register_hazard_objects.py     # CLI for registering hazard objects (camera or photo)
├── compare_fixed_thresholds.py    # Confusion matrix evaluation against ground truth
├── alpha_grid_search.py           # α coefficient sweep
├── ground_truth_manual.csv        # Manual labels for the 121-image test set
├── image/                         # The 121-image test set
├── analysis/                      # Evaluation results (confusion matrices, grid search)
├── docs/                          # Supporting technical write-ups
├── tests/                         # Test suite
├── BaoCaoDoAnTotNghiep_Full.md     # Full thesis report (Vietnamese)
└── colab_train_*.ipynb            # Model training notebooks (Google Colab)
```

Not included in this repository (see `.gitignore`): the Roboflow training datasets (re-downloadable via the Colab notebooks), trained model weights (`*.pt`), and anything containing real captured data from actual camera use (`danger_clips/`, `hazard_gallery/`, `logs/`) — these are excluded on purpose since they can contain real photos/video of a real child.

## Known limitations

See `BaoCaoDoAnTotNghiep_Full.md` section 6.3 for a full, evidence-backed list. In short: accuracy is currently only measured on static images (not a real labeled video), multiple children in one frame share a single threshold rather than being tracked independently, keypoint confidence isn't checked (so heavy occlusion can silently skew the dynamic threshold), and Jetson Nano deployment code exists but has never been run on real Jetson hardware.

## Security

`config.yaml` ships with `email.sender_password` left **blank** on purpose. Fill in your own Gmail App Password locally after cloning — never commit a real value. If you're working from a clone of this repo, check `git log` for the file before assuming history is clean.
