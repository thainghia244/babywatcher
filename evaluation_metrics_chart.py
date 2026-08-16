import csv
import os
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def load_latest_metrics(csv_path: Path) -> dict:
    with csv_path.open('r', encoding='utf-8', newline='') as f:
        rows = list(csv.DictReader(f))

    if not rows:
        raise ValueError(f'No training metrics found in {csv_path}')

    last_row = rows[-1]
    precision = float(last_row['metrics/precision(B)'])
    recall = float(last_row['metrics/recall(B)'])
    map50 = float(last_row['metrics/mAP50(B)']) * 100.0
    map50_95 = float(last_row['metrics/mAP50-95(B)']) * 100.0
    f1 = (2 * precision * recall) / (precision + recall) * 100.0 if (precision + recall) > 0 else 0.0

    return {
        'Recall': round(recall * 100.0, 2),
        'mAP@0.5': round(map50, 2),
        'mAP@0.5:0.95': round(map50_95, 2),
        'F1-score': round(f1, 2),
    }


base_dir = Path(__file__).resolve().parent
results_csv = base_dir / 'runs' / 'detect' / 'models' / 'babyMonitor2' / 'detector' / 'results.csv'
metrics = load_latest_metrics(results_csv)

labels = list(metrics.keys())
values = list(metrics.values())

plt.figure(figsize=(8, 5))
bar_colors = ['#4C78A8', '#F58518', '#54A24B', '#E45756']
plt.bar(labels, values, color=bar_colors, width=0.6)
plt.ylim(0, 100)
plt.ylabel('Giá trị (%)')
plt.title('Các chỉ số đánh giá BabyWatcher từ kết quả huấn luyện thực tế')
plt.grid(axis='y', linestyle='--', alpha=0.3)

for i, v in enumerate(values):
    plt.text(i, v + 1.5, f'{v:.2f}%', ha='center', va='bottom', fontsize=10)

plt.tight_layout()
output_path = base_dir / 'evaluation_results_assessment.png'
plt.savefig(output_path, dpi=300)
plt.close()

summary_path = base_dir / 'evaluation_results_assessment.txt'
with summary_path.open('w', encoding='utf-8') as f:
    f.write('Các chỉ số đánh giá BabyWatcher (dựa trên kết quả huấn luyện thực tế)\n')
    f.write('============================================================\n')
    f.write(f'Nguồn dữ liệu: {results_csv.relative_to(base_dir)}\n')
    f.write('============================================================\n')
    for k, v in metrics.items():
        f.write(f'{k}: {v:.2f}%\n')
    f.write('\nHình ảnh biểu đồ đã được lưu tại: evaluation_results_assessment.png\n')

print('Saved chart:', output_path)
print('Saved summary file:', summary_path)
