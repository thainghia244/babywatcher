import csv
import json
import statistics as stats
from pathlib import Path

base = Path(__file__).parent
rows = list(csv.DictReader(open(base / 'compare_fixed_thresholds.csv', encoding='utf-8')))

by_mode = {}
for r in rows:
    by_mode.setdefault(r['mode'], []).append(r)

# 1. Shoulder width / dynamic threshold distribution (from the dedicated diagnostics rerun)
diag_rows = list(csv.DictReader(open(base / 'dynamic_diagnostics.csv', encoding='utf-8')))
diag_by_image = {r['image']: r for r in diag_rows}
dyn_rows = by_mode['dynamic']
shoulder_widths = [float(r['shoulder_width']) for r in diag_rows if r['shoulder_width'] not in ('', 'None')]
hm_thresh = [float(r['h_m_thresh']) for r in diag_rows if r['h_m_thresh'] not in ('', 'None')]
ho_thresh = [float(r['h_o_thresh']) for r in diag_rows if r['h_o_thresh'] not in ('', 'None')]

def summary(name, values):
    if not values:
        print(f'{name}: no data')
        return
    print(f'{name}: n={len(values)} min={min(values):.1f} p25={stats.quantiles(values, n=4)[0]:.1f} '
          f'median={stats.median(values):.1f} p75={stats.quantiles(values, n=4)[2]:.1f} max={max(values):.1f} '
          f'mean={stats.mean(values):.1f} stdev={stats.pstdev(values):.1f}')

print('=== Dynamic threshold spread across the 121-image set ===')
summary('shoulder_width (px)', shoulder_widths)
summary('dynamic hand_mouth_threshold (px)', hm_thresh)
summary('dynamic hand_object_threshold (px)', ho_thresh)

# 2. For each image, does dynamic agree with each fixed mode? Build image->status per mode
image_status = {}
for r in rows:
    image_status.setdefault(r['image'], {})[r['mode']] = r['status']

fixed_modes = sorted([m for m in by_mode if m != 'dynamic'], key=lambda m: int(m.split('_')[1]))

print('\n=== Agreement of each fixed threshold with dynamic, by dataset half (small vs large shoulder width) ===')
median_sw = stats.median(shoulder_widths)
small_images = {r['image'] for r in diag_rows if r['shoulder_width'] not in ('', 'None') and float(r['shoulder_width']) <= median_sw}
large_images = {r['image'] for r in diag_rows if r['shoulder_width'] not in ('', 'None') and float(r['shoulder_width']) > median_sw}

for mode in fixed_modes:
    small_same = sum(1 for img in small_images if image_status[img].get('dynamic') == image_status[img].get(mode))
    large_same = sum(1 for img in large_images if image_status[img].get('dynamic') == image_status[img].get(mode))
    print(f'{mode:>10}: small-shoulder agree={small_same}/{len(small_images)} ({small_same/len(small_images):.1%})  '
          f'large-shoulder agree={large_same}/{len(large_images)} ({large_same/len(large_images):.1%})')

# 3. Status distribution per mode (for the chart / table)
print('\n=== Status distribution per mode ===')
status_labels = ['SAFE', 'HAND_TO_MOUTH', 'OBJECT_TO_MOUTH']
dist = {}
for mode, mrows in by_mode.items():
    counts = {s: 0 for s in status_labels}
    for r in mrows:
        counts[r['status']] = counts.get(r['status'], 0) + 1
    dist[mode] = counts
    print(mode, counts)

# 4. Agreement-with-dynamic % per fixed threshold (for the line chart)
agreement_by_threshold = []
for mode in fixed_modes:
    same = sum(1 for img, m in image_status.items() if m.get('dynamic') == m.get(mode))
    agreement_by_threshold.append({
        'threshold': int(mode.split('_')[1]),
        'same_pct': round(same / len(image_status) * 100, 1),
    })

# 5. Shoulder-width histogram bins (for the distribution chart)
bin_edges = [0, 50, 100, 150, 200, 250, 300, 400, 520]
hist = [0] * (len(bin_edges) - 1)
for w in shoulder_widths:
    for i in range(len(bin_edges) - 1):
        if bin_edges[i] <= w < bin_edges[i + 1] or (i == len(bin_edges) - 2 and w == bin_edges[-1]):
            hist[i] += 1
            break
hist_bins = [{'range': f'{bin_edges[i]}-{bin_edges[i+1]}', 'count': hist[i]} for i in range(len(hist))]

with open(base / 'analysis_summary.json', 'w', encoding='utf-8') as f:
    json.dump({
        'shoulder_width_stats': {
            'min': min(shoulder_widths), 'max': max(shoulder_widths),
            'median': stats.median(shoulder_widths), 'mean': stats.mean(shoulder_widths),
            'stdev': stats.pstdev(shoulder_widths), 'n': len(shoulder_widths),
            'n_no_pose': len(diag_rows) - len(shoulder_widths),
        },
        'dynamic_hm_thresh_stats': {
            'min': min(hm_thresh), 'max': max(hm_thresh), 'median': stats.median(hm_thresh),
        },
        'status_distribution': dist,
        'mode_order': ['dynamic'] + fixed_modes,
        'median_shoulder_width': median_sw,
        'small_group_size': len(small_images),
        'large_group_size': len(large_images),
        'agreement_by_threshold': agreement_by_threshold,
        'shoulder_width_hist': hist_bins,
        'total_images': len(images) if (images := sorted(set(image_status))) else 0,
    }, f, indent=2, ensure_ascii=False)
print('\nWrote analysis_summary.json')
print(json.dumps(agreement_by_threshold, indent=2))
print(json.dumps(hist_bins, indent=2))
