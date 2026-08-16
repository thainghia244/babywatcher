"""Sweep alpha_hm / alpha_om / alpha_ho one at a time (holding the other two
at baseline) against the 121-image ground truth, using the same
reset_and_settle() methodology as compare_fixed_thresholds.py's "dynamic"
mode -- but only that mode, skipping the fixed_80/110/140 sweeps entirely,
to keep a full grid affordable.

This is the systematic grid-search follow-up mentioned in
BaoCaoDoAnTotNghiep_Full.md section 3.2.4.2 ("hướng phát triển tiếp theo"),
answering: is 0.7 / 0.7 / 0.3 actually a good point, or would a nearby value
do better on Precision/Recall for HAND_TO_MOUTH and OBJECT_TO_MOUTH?

Usage:
    python alpha_grid_search.py
"""
import csv
import json
import sys
import time
from pathlib import Path

import cv2

sys.path.insert(0, '.')
from compare_fixed_thresholds import (
    make_watcher, reset_and_settle, compute_confusion_matrix,
    compute_classification_metrics, write_json, plot_confusion_matrix,
)

BASELINE = {'hand_mouth_multiplier': 0.7, 'object_mouth_multiplier': 0.7, 'object_hand_hold_multiplier': 0.3}

SWEEPS = {
    'hand_mouth_multiplier': [0.5, 0.6, 0.7, 0.8, 0.9],
    'object_mouth_multiplier': [0.5, 0.6, 0.7, 0.8, 0.9],
    'object_hand_hold_multiplier': [0.2, 0.3, 0.4, 0.5, 0.6],
}


def build_combos():
    """Baseline once, then one-at-a-time variations -- not a full cartesian
    grid (5^3=125 runs would take ~14 hours at ~7 min/run; this is ~13 runs)."""
    combos = {'baseline': dict(BASELINE)}
    for key, values in SWEEPS.items():
        for v in values:
            if v == BASELINE[key]:
                continue  # already covered by 'baseline'
            combo = dict(BASELINE)
            combo[key] = v
            label = f"{key}={v}"
            combos[label] = combo
    return combos


def main():
    with open('ground_truth_manual.csv', encoding='utf-8') as f:
        gt = {row['image']: row['status'] for row in csv.DictReader(f)}

    images = sorted([p for p in Path('image').glob('*') if p.suffix.lower() in {'.jpg', '.jpeg', '.png'}])
    frames = {p.name: cv2.imread(str(p)) for p in images}

    combos = build_combos()
    print(f"Sẽ chạy {len(combos)} tổ hợp: {list(combos.keys())}\n")

    results = {}
    out_dir = Path('analysis/alpha_grid_search')
    out_dir.mkdir(parents=True, exist_ok=True)

    for label, combo in combos.items():
        t0 = time.time()
        watcher = make_watcher('config.yaml')
        watcher.dynamic_threshold = True
        watcher.hand_mouth_multiplier = combo['hand_mouth_multiplier']
        watcher.object_mouth_multiplier = combo['object_mouth_multiplier']
        watcher.object_hand_hold_multiplier = combo['object_hand_hold_multiplier']

        repeats = max(8, watcher.proximity_history_window * 2, watcher.object_mouth_history_window * 2)
        predictions = []
        for name, frame in frames.items():
            if frame is None:
                continue
            watcher.current_source = name
            info = reset_and_settle(watcher, frame, repeats=repeats)
            predictions.append({'image': name, 'status': info.get('status', 'SAFE')})

        matrix = compute_confusion_matrix(gt, predictions)
        metrics = compute_classification_metrics(matrix)
        results[label] = {'combo': combo, 'confusion_matrix': matrix, 'metrics': metrics}

        elapsed = time.time() - t0
        acc = metrics['accuracy']
        hm = metrics['labels'].get('HAND_TO_MOUTH', {})
        om = metrics['labels'].get('OBJECT_TO_MOUTH', {})
        print(f"[{elapsed:6.1f}s] {label:35s} acc={acc:.4f}  "
              f"HAND_TO_MOUTH P/R={hm.get('precision', 0):.3f}/{hm.get('recall', 0):.3f}  "
              f"OBJECT_TO_MOUTH P/R={om.get('precision', 0):.3f}/{om.get('recall', 0):.3f}")

        write_json(out_dir / 'results.json', results)  # write after every combo so partial progress isn't lost

    print(f"\nWrote {out_dir / 'results.json'}")

    print("\n=== Bảng tổng hợp ===")
    print(f"{'Combo':35s} {'Acc':>7s} {'HAND P':>7s} {'HAND R':>7s} {'OBJ P':>7s} {'OBJ R':>7s}")
    for label, r in results.items():
        m = r['metrics']
        hm = m['labels'].get('HAND_TO_MOUTH', {})
        om = m['labels'].get('OBJECT_TO_MOUTH', {})
        print(f"{label:35s} {m['accuracy']:7.4f} {hm.get('precision', 0):7.4f} {hm.get('recall', 0):7.4f} "
              f"{om.get('precision', 0):7.4f} {om.get('recall', 0):7.4f}")


if __name__ == '__main__':
    main()
