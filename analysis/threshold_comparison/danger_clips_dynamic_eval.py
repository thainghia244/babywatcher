"""
Re-run dynamic threshold (single-image mode) on every real captured danger
clip in danger_clips/, and compare against the label encoded in the filename
(the live/video-context decision, made with temporal confirmation + history
while the system was actually running).

This measures how much the video-context confirmation machinery matters:
if single-image dynamic threshold disagrees with the filename label, either
(a) the frame alone doesn't show danger without surrounding context, or
(b) the confirmation logic filtered out a spurious signal, or vice versa.
"""
import sys
import csv
import re
import time
from pathlib import Path

sys.path.insert(0, '.')
import cv2
from src.detector import BabyWatcher

CLIPS_DIR = Path('danger_clips')
OUT_CSV = Path('analysis/threshold_comparison/danger_clips_dynamic_eval.csv')

FILENAME_RE = re.compile(r'^(HAND_TO_MOUTH|OBJECT_TO_MOUTH)_\d{8}_\d{6}\.jpg$')


def _single_frame_proximity_signal(self, distance, threshold):
    """Bypass the 3-frame smoothing window: on an isolated frame there is no
    history to smooth over, so use the current frame's raw distance check
    directly (this is what the smoothed signal reduces to once its history
    window is fully warmed up with matching frames)."""
    return distance <= max(10.0, threshold * 0.85)


def _single_frame_object_to_mouth_signal(self, object_mouth_distance, hand_mouth_distance,
                                          hand_near_mouth, hand_object_distance, threshold):
    """Same idea as above, for the object-to-mouth smoothing window."""
    hand_context = hand_near_mouth or hand_object_distance <= max(20.0, threshold * 0.55)
    if not hand_context:
        return False
    body_scale = max(threshold, 1.0)
    object_threshold = body_scale * self.object_mouth_multiplier * 0.75
    object_hand_threshold = body_scale * 0.55
    object_close = object_mouth_distance <= object_threshold
    object_in_hand = hand_object_distance <= object_hand_threshold
    return object_close and object_in_hand


def make_watcher(config_path='config.yaml'):
    w = BabyWatcher(config_path)
    w.save_danger_clips = False
    w._force_immediate_confirmation = False
    w._single_image_mode = True
    w.dynamic_threshold = True
    w.last_event_log_time = 1e18
    # Bind the history-free variants in place of the real (temporally-smoothed)
    # methods -- see the module docstring update below for why.
    import types
    w._evaluate_proximity_signal = types.MethodType(_single_frame_proximity_signal, w)
    w._evaluate_object_to_mouth_signal = types.MethodType(_single_frame_object_to_mouth_signal, w)
    try:
        w.alert_manager.sound_alert.enabled = False
    except Exception:
        pass
    try:
        w.alert_manager.email_alert.enabled = False
    except Exception:
        pass
    w.logger.log_event = lambda *a, **k: None
    w.logger.log_info = lambda *a, **k: None
    w.logger.log_warning = lambda *a, **k: None
    w.logger.log_error = lambda *a, **k: None
    return w


def main():
    files = sorted(p for p in CLIPS_DIR.iterdir() if FILENAME_RE.match(p.name))
    print(f'Found {len(files)} labeled danger clips')

    watcher = make_watcher()
    rows = []
    t0 = time.time()
    errors = 0
    for i, path in enumerate(files):
        m = FILENAME_RE.match(path.name)
        filename_label = m.group(1)

        frame = cv2.imread(str(path))
        if frame is None:
            errors += 1
            continue

        watcher.proximity_history = []
        watcher.object_mouth_history = []
        watcher.danger_start_time = None
        watcher._danger_state_since = time.time() - 10.0
        watcher.current_source = str(path)
        try:
            _, info = watcher.process_frame(frame)
            status = info.get('status', 'SAFE')
        except Exception as exc:
            errors += 1
            status = 'ERROR'
        rows.append({'image': path.name, 'filename_label': filename_label, 'dynamic_single_image': status})

        if (i + 1) % 50 == 0:
            print(f'  [{i+1}/{len(files)}] elapsed={time.time()-t0:.0f}s')

    with OUT_CSV.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['image', 'filename_label', 'dynamic_single_image'])
        writer.writeheader()
        writer.writerows(rows)

    print(f'Wrote {OUT_CSV} ({len(rows)} rows, {errors} errors) in {time.time()-t0:.1f}s')


if __name__ == '__main__':
    main()
