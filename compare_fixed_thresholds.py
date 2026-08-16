from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from collections import Counter
from pathlib import Path

import cv2

sys.path.insert(0, '.')
from src.detector import BabyWatcher


def make_watcher(config_path: str) -> BabyWatcher:
    watcher = BabyWatcher(config_path)
    watcher.save_danger_clips = False
    watcher.save_danger_videos = False
    # _force_immediate_confirmation=True (as used by process_image()) bypasses
    # not just the frame-count gate but also the proximity/object-mouth moving
    # average smoothing entirely -- on a batch of independent still photos
    # (rather than consecutive video frames of one real scene) that smoothing
    # is the only thing standing between "hand happens to be near face in this
    # one photo" and an alert, so bypassing it inflates false positives badly.
    # We instead keep the real smoothing (_force_immediate_confirmation=False)
    # and use reset_and_settle() below to fairly evaluate each image in
    # isolation: reset all per-watcher history, then feed the same frame
    # repeatedly with a simulated clock so the moving-average windows and the
    # sustained_danger_duration wall-clock gate both converge exactly as they
    # would for a real sustained observation, without cross-image state leaking
    # or depending on how fast this machine happens to run the loop.
    watcher._force_immediate_confirmation = False
    watcher._single_image_mode = True
    watcher.last_event_log_time = 1e18
    watcher.danger_start_time = None
    watcher._danger_state_since = None
    try:
        watcher.alert_manager.sound_alert.enabled = False
    except Exception:
        pass
    try:
        watcher.alert_manager.email_alert.enabled = False
    except Exception:
        pass
    watcher.logger.log_event = lambda *args, **kwargs: None
    watcher.logger.log_info = lambda *args, **kwargs: None
    watcher.logger.log_warning = lambda *args, **kwargs: None
    watcher.logger.log_error = lambda *args, **kwargs: None
    return watcher


def _json_default(obj):
    if hasattr(obj, 'item'):
        return obj.item()
    raise TypeError(f'Object of type {obj.__class__.__name__} is not JSON serializable')


def write_json(path: Path, data: dict) -> None:
    with path.open('w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=_json_default)


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, lines: list[str]) -> None:
    with path.open('w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def reset_and_settle(watcher: BabyWatcher, frame, repeats: int = 6, step_seconds: float = 1.0) -> dict:
    """Evaluate a single frame in isolation, as if it were a sustained real
    observation, instead of a single detached call.

    Resets every piece of cross-frame state the detector accumulates
    (proximity/object-mouth moving-average history, confirmation counters,
    danger timers) so nothing leaks in from whatever image was processed
    before this one on the same watcher instance. Then feeds the SAME frame
    `repeats` times (>= proximity_history_window / object_mouth_history_window
    so the moving averages actually converge) while faking time.time() to
    advance by `step_seconds` each call -- this satisfies the real
    sustained_danger_duration wall-clock gate deterministically, without
    depending on how fast this machine happens to loop or resorting to
    `_force_immediate_confirmation` (which would skip the smoothing filters
    entirely and defeat the point of the test).
    """
    watcher.proximity_history = []
    watcher.object_mouth_history = []
    watcher._confirmation_counter = 0
    watcher._confirmed_status = "SAFE"
    watcher.danger_start_time = None
    watcher._danger_state_since = None

    fake_now = [time.time()]

    def fake_time():
        return fake_now[0]

    real_time_func = time.time
    time.time = fake_time  # src/detector.py does `import time; time.time()` -- same module object, so this patches it too
    try:
        info = {}
        for _ in range(repeats):
            fake_now[0] += step_seconds
            # process_frame() draws skeleton/distance overlays directly onto
            # its `frame` argument in place. Passing the same object across
            # repeats would feed the pose/object models an increasingly
            # annotated image on every call after the first, corrupting
            # shoulder_width/distance readings -- always hand it a fresh copy.
            _, info = watcher.process_frame(frame.copy())
        return info
    finally:
        time.time = real_time_func


def load_ground_truth(path: Path) -> dict[str, str]:
    if not path.exists():
        raise FileNotFoundError(f'Ground truth file not found: {path}')

    truth: dict[str, str] = {}
    with path.open('r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            image = row.get('image') or row.get('filename') or row.get('file')
            status = row.get('status')
            if image and status:
                truth[image] = status
    return truth


def compute_confusion_matrix(ground_truth: dict[str, str], predictions: list[dict]) -> dict[str, dict[str, int]]:
    classes = sorted({*ground_truth.values(), *(row['status'] for row in predictions)})
    matrix: dict[str, dict[str, int]] = {gt: {pred: 0 for pred in classes} for gt in classes}
    for row in predictions:
        image = row['image']
        predicted = row['status']
        actual = ground_truth.get(image)
        if actual is None:
            continue
        matrix[actual][predicted] += 1
    return matrix


def compute_classification_metrics(matrix: dict[str, dict[str, int]]) -> dict[str, dict[str, float]]:
    labels = sorted(matrix)
    total = sum(sum(row.values()) for row in matrix.values())
    metrics: dict[str, dict[str, float]] = {}
    for label in labels:
        tp = matrix[label][label]
        fp = sum(matrix[other][label] for other in labels if other != label)
        fn = sum(matrix[label][other] for other in labels if other != label)
        support = tp + fn
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        metrics[label] = {
            'precision': precision,
            'recall': recall,
            'f1': f1,
            'support': float(support),
        }
    accuracy = sum(matrix[label][label] for label in labels) / total if total else 0.0
    return {'accuracy': accuracy, 'total': float(total), 'labels': metrics}


def plot_confusion_matrix(matrix: dict[str, dict[str, int]], path: Path, title: str) -> bool:
    try:
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        return False

    labels = sorted(matrix)
    data = np.array([[matrix[row][col] for col in labels] for row in labels], dtype=int)
    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(data, cmap='Blues', interpolation='nearest')
    ax.set_title(title)
    ax.set_xlabel('Predicted')
    ax.set_ylabel('Actual')
    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha='right')
    ax.set_yticklabels(labels)

    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            color = 'white' if data[i, j] > data.max() / 2 else 'black'
            ax.text(j, i, int(data[i, j]), ha='center', va='center', color=color)

    fig.colorbar(im, ax=ax)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return True


def compute_pairwise_matrix(labels_a: list[str], labels_b: list[str]) -> dict[str, dict[str, int]]:
    classes = sorted(set(labels_a) | set(labels_b))
    matrix: dict[str, dict[str, int]] = {a: {b: 0 for b in classes} for a in classes}
    for a, b in zip(labels_a, labels_b):
        matrix[a][b] += 1
    return matrix


def summarize_pairwise(labels_a: list[str], labels_b: list[str]) -> tuple[int, int, float]:
    total = len(labels_a)
    same = sum(1 for a, b in zip(labels_a, labels_b) if a == b)
    diff = total - same
    same_pct = same / total if total else 0.0
    return same, diff, same_pct


def format_duration(seconds: float) -> str:
    return f'{seconds:.2f}s'


def main() -> None:
    parser = argparse.ArgumentParser(description='Compare fixed threshold values on the BabyWatcher image dataset.')
    parser.add_argument('--config', default='config.yaml', help='Path to config file')
    parser.add_argument('--image-dir', default='image', help='Directory containing image files')
    parser.add_argument('--output-dir', default='.', help='Directory where comparison outputs are written')
    parser.add_argument('--ground-truth', help='Optional CSV file with columns image,status for confusion matrix')
    parser.add_argument('--thresholds', nargs='+', type=int, default=[80, 110, 140], help='Fixed hand/object threshold values to compare')
    args = parser.parse_args()

    image_dir = Path(args.image_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    images = sorted([p for p in image_dir.glob('*') if p.suffix.lower() in {'.jpg', '.jpeg', '.png'}])
    if not images:
        raise SystemExit(f'No images found in {image_dir.resolve()}')

    modes = [('dynamic', None, None)] + [(f'fixed_{value}', value, value) for value in args.thresholds]

    all_rows: list[dict] = []
    summary: dict[str, dict[str, int]] = {}
    image_matrix: dict[str, dict[str, str]] = {img.name: {} for img in images}

    start_time = time.time()
    for mode, hand_thresh, obj_thresh in modes:
        print(f'Running mode: {mode}')
        watcher = make_watcher(args.config)
        watcher.dynamic_threshold = (mode == 'dynamic')
        if mode != 'dynamic':
            watcher.hand_mouth_thresh = hand_thresh
            watcher.hand_obj_thresh = obj_thresh

        counts = Counter()
        errors = 0

        for image_path in images:
            frame = cv2.imread(str(image_path))
            if frame is None:
                errors += 1
                print(f'  ERROR loading image {image_path.name}')
                continue

            watcher.current_source = str(image_path)
            try:
                repeats = max(8, watcher.proximity_history_window * 2, watcher.object_mouth_history_window * 2)
                info = reset_and_settle(watcher, frame, repeats=repeats)
                status = info.get('status', 'SAFE')
                counts[status] += 1
                image_matrix[image_path.name][mode] = status
                all_rows.append({
                    'mode': mode,
                    'image': image_path.name,
                    'status': status,
                    'shoulder_width': info.get('shoulder_width'),
                    'hand_mouth_distance': info.get('h_m_dist'),
                    'hand_mouth_threshold': info.get('h_m_thresh'),
                    'hand_object_distance': info.get('h_o_dist'),
                    'hand_object_threshold': info.get('h_o_thresh'),
                })
            except Exception as exc:
                errors += 1
                print(f'  ERROR processing {image_path.name}: {exc}')

        summary[mode] = {'errors': errors, **counts}
        print(f'  {mode}: {dict(counts)} errors={errors}')

    elapsed = time.time() - start_time
    print(f'Completed {len(images)} images in {format_duration(elapsed)}')

    output_json = output_dir / 'compare_fixed_thresholds.json'
    output_csv = output_dir / 'compare_fixed_thresholds.csv'
    mode_compare_csv = output_dir / 'compare_fixed_thresholds_mode_comparison.csv'

    write_json(output_json, {
        'image_dir': str(image_dir),
        'config': args.config,
        'thresholds': args.thresholds,
        'summary': summary,
        'predictions': all_rows,
        'mode_matrix': image_matrix,
    })
    print(f'Wrote {output_json}')

    fieldnames = [
        'mode', 'image', 'status',
        'shoulder_width',
        'hand_mouth_distance', 'hand_mouth_threshold',
        'hand_object_distance', 'hand_object_threshold',
    ]
    write_csv(output_csv, all_rows, fieldnames)
    print(f'Wrote {output_csv}')

    compare_rows = []
    for image_name, mode_statuses in sorted(image_matrix.items()):
        row = {'image': image_name}
        row.update(mode_statuses)
        row['all_same'] = int(len(set(mode_statuses.values())) == 1)
        compare_rows.append(row)

    fieldnames_compare = ['image'] + [mode for mode, _, _ in modes] + ['all_same']
    write_csv(mode_compare_csv, compare_rows, fieldnames_compare)
    print(f'Wrote {mode_compare_csv}')

    pairwise_report = ['Fixed threshold pairwise summary:']
    mode_labels = [mode for mode, _, _ in modes]
    for i, mode_a in enumerate(mode_labels):
        for mode_b in mode_labels[i + 1:]:
            labels_a = [row[mode_a] for row in compare_rows]
            labels_b = [row[mode_b] for row in compare_rows]
            same, diff, same_pct = summarize_pairwise(labels_a, labels_b)
            pairwise_report.append(f'  {mode_a} vs {mode_b}: same={same}, different={diff}, same_pct={same_pct:.3f}')

    pairwise_report_path = output_dir / 'compare_fixed_thresholds_pairwise_summary.txt'
    write_text(pairwise_report_path, pairwise_report)
    print(f'Wrote {pairwise_report_path}')

    if args.ground_truth:
        ground_truth = load_ground_truth(Path(args.ground_truth))
        print(f'Loaded ground truth for {len(ground_truth)} images from {args.ground_truth}')

        confusion: dict[str, dict[str, dict[str, int]]] = {}
        metrics: dict[str, dict[str, dict[str, float]]] = {}
        for mode, _, _ in modes:
            predictions = [row for row in all_rows if row['mode'] == mode]
            matrix = compute_confusion_matrix(ground_truth, predictions)
            confusion[mode] = matrix
            metrics[mode] = compute_classification_metrics(matrix)

            plot_path = output_dir / f'compare_fixed_thresholds_confusion_matrix_{mode}.png'
            plotted = plot_confusion_matrix(matrix, plot_path, f'Confusion Matrix: {mode}')
            if plotted:
                print(f'Wrote {plot_path}')
            else:
                print(f'Skipped plotting matrix for {mode}: matplotlib not installed')

        confusion_json = output_dir / 'compare_fixed_thresholds_confusion_matrix.json'
        write_json(confusion_json, {'confusion_matrix': confusion})
        print(f'Wrote {confusion_json}')

        metrics_json = output_dir / 'compare_fixed_thresholds_classification_metrics.json'
        write_json(metrics_json, {'classification_metrics': metrics})
        print(f'Wrote {metrics_json}')

        metrics_txt = output_dir / 'compare_fixed_thresholds_classification_report.txt'
        report_lines = ['Classification report:']
        for mode, mode_metrics in metrics.items():
            report_lines.append(f'\nMode: {mode}')
            report_lines.append(f"  Accuracy: {mode_metrics['accuracy']:.4f}")
            report_lines.append(f"  Total: {int(mode_metrics['total'])}")
            report_lines.append('  Label metrics:')
            for label, label_metrics in mode_metrics['labels'].items():
                report_lines.append(
                    f"    {label}: precision={label_metrics['precision']:.4f}, "
                    f"recall={label_metrics['recall']:.4f}, f1={label_metrics['f1']:.4f}, "
                    f"support={int(label_metrics['support'])}"
                )
        write_text(metrics_txt, report_lines)
        print(f'Wrote {metrics_txt}')

    print('Comparison finished.')


if __name__ == '__main__':
    main()
