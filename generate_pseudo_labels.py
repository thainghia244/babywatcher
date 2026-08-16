from pathlib import Path
import sys
import json
import csv
import cv2

sys.path.insert(0, '.')
from src.detector import BabyWatcher


def make_watcher(config_path='config.yaml'):
    w = BabyWatcher(config_path)
    w.save_danger_clips = False
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


if __name__ == '__main__':
    image_dir = Path('image')
    out_json = Path('pseudo_labels.json')
    out_csv = Path('pseudo_labels.csv')

    imgs = sorted([x for x in image_dir.glob('*') if x.suffix.lower() in {'.jpg', '.jpeg', '.png'}])
    if not imgs:
        raise SystemExit(f'No images found in {image_dir.resolve()}')

    modes = [
        ('dynamic', None, None),
        ('fixed_yaml', 45, 60),
        ('fixed_50', 50, 50),
    ]

    results = []
    summary = {}

    for mode, hand_thresh, obj_thresh in modes:
        print(f'Processing mode: {mode}')
        w = make_watcher()
        w.dynamic_threshold = mode == 'dynamic'
        if hand_thresh is not None:
            w.hand_mouth_thresh = hand_thresh
        if obj_thresh is not None:
            w.hand_obj_thresh = obj_thresh
        w._force_immediate_confirmation = True
        w._single_image_mode = True
        w.last_event_log_time = 1e18
        w.danger_start_time = None
        w._danger_state_since = None

        mode_counts = {'SAFE': 0, 'HAND_TO_MOUTH': 0, 'OBJECT_TO_MOUTH': 0}
        errors = 0

        for img_path in imgs:
            frame = cv2.imread(str(img_path))
            if frame is None:
                errors += 1
                print(f'  ERROR reading {img_path.name}')
                continue
            w.current_source = str(img_path)
            try:
                _, info = w.process_frame(frame)
                status = info.get('status', 'SAFE')
                mode_counts[status] = mode_counts.get(status, 0) + 1
                results.append({
                    'mode': mode,
                    'image': img_path.name,
                    'status': status,
                    'hand_mouth_distance': info.get('h_m_dist'),
                    'hand_mouth_threshold': info.get('h_m_thresh'),
                    'hand_object_distance': info.get('h_o_dist'),
                    'hand_object_threshold': info.get('h_o_thresh'),
                })
            except Exception as exc:
                errors += 1
                print(f'  ERROR processing {img_path.name}: {exc}')

        summary[mode] = {'counts': mode_counts, 'errors': errors}
        print(f'  {mode_counts}  errors={errors}')

    out = {'images': len(imgs), 'summary': summary, 'predictions': results}

    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f'Wrote {out_json}')

    with open(out_csv, 'w', encoding='utf-8', newline='') as f:
        fieldnames = [
            'mode', 'image', 'status',
            'hand_mouth_distance', 'hand_mouth_threshold',
            'hand_object_distance', 'hand_object_threshold'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow(row)
    print(f'Wrote {out_csv}')
