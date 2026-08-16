#!/usr/bin/env python3
"""
Merge the existing 3-class babyMonitor2 dataset (baby/blanket/toy, already
re-split 80/10/10) with three supplementary public datasets downloaded from
Roboflow Universe into train/:

- "Baby Monitoring 4" (1 class: Baby)                -> all boxes become baby
- "Baby-Detection" (3 classes: prone/sideways/suspine, i.e. sleep positions
  of a baby) -> all boxes become baby (position doesn't matter for our use)
- "kid-toys" (33 classes: small animal/food/vehicle toy figures)
  -> all boxes become toy

Pools every image+label pair across ALL sources (ignoring their original
train/valid/test assignment, same approach as resplit_dataset.py), shuffles
with a fixed seed, and re-splits 80/10/10 so the whole merged set follows one
consistent, reproducible split.
"""
import random
import shutil
from pathlib import Path

SEED = 42
RATIOS = {"train": 0.8, "valid": 0.1, "test": 0.1}
NEW_NAMES = ["baby", "blanket", "toy"]
DST = Path("babyMonitor2_merged.v1i.yolov8")

# Each source: (dataset dir, splits to pool from, remap function old_cls -> new_cls, filename prefix)
BASE = Path("babyMonitor2_3class_split80.v1i.yolov8")
SUP_DIR = Path("train")
BABY_MONITORING_4 = SUP_DIR / "Baby Monitoring 4.v1i.yolov8"
BABY_DETECTION = SUP_DIR / "Baby-Detection.v1i.yolov8"
KID_TOYS = SUP_DIR / "kid-toys.v1i.yolov8"


def identity_remap(old_cls):
    return old_cls  # base dataset is already baby=0, blanket=1, toy=2


def all_to_baby(old_cls):
    return 0


def all_to_toy(old_cls):
    return 2


SOURCES = [
    (BASE, identity_remap, "base"),
    (BABY_MONITORING_4, all_to_baby, "bm4"),
    (BABY_DETECTION, all_to_baby, "bd"),
    (KID_TOYS, all_to_toy, "kt"),
]


def polygon_to_bbox(coords):
    """coords: flat [x1, y1, x2, y2, ...] normalized polygon points -> (cx, cy, w, h)."""
    xs = coords[0::2]
    ys = coords[1::2]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    return (x_min + x_max) / 2, (y_min + y_max) / 2, x_max - x_min, y_max - y_min


def collect_pairs(dataset_dir, remap_fn, prefix):
    pairs = []
    dropped = 0
    n_polygon_lines = 0
    for split in ["train", "valid", "test"]:
        images_dir = dataset_dir / split / "images"
        labels_dir = dataset_dir / split / "labels"
        if not images_dir.exists():
            continue
        for img_path in images_dir.iterdir():
            if img_path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
                continue
            label_path = labels_dir / (img_path.stem + ".txt")
            lines_out = []
            if label_path.exists():
                for line in label_path.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    parts = line.split()
                    old_cls = int(parts[0])
                    new_cls = remap_fn(old_cls)
                    if new_cls is None:
                        dropped += 1
                        continue
                    values = [float(v) for v in parts[1:]]
                    if len(values) == 4:
                        cx, cy, bw, bh = values
                    else:
                        # Segmentation-format label (polygon points) -- convert
                        # to an axis-aligned bounding box, since this project
                        # trains a detection (not segmentation) head.
                        n_polygon_lines += 1
                        cx, cy, bw, bh = polygon_to_bbox(values)
                    lines_out.append(f"{new_cls} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")
            new_name = f"{prefix}_{img_path.name}"
            pairs.append((img_path, new_name, lines_out))
    if n_polygon_lines:
        print(f"  ({dataset_dir.name}: converted {n_polygon_lines} polygon labels to bounding boxes)")
    return pairs, dropped


def main():
    if DST.exists():
        raise SystemExit(f"{DST} already exists -- remove it first if you want to regenerate.")

    all_pairs = []
    print("=== Collecting from each source ===")
    for dataset_dir, remap_fn, prefix in SOURCES:
        if not dataset_dir.exists():
            print(f"SKIP (not found): {dataset_dir}")
            continue
        pairs, dropped = collect_pairs(dataset_dir, remap_fn, prefix)
        n_boxes = sum(len(p[2]) for p in pairs)
        print(f"{dataset_dir.name}: {len(pairs)} images, {n_boxes} boxes kept, {dropped} boxes dropped")
        all_pairs.extend(pairs)

    print(f"\nTotal pooled: {len(all_pairs)} images")

    rng = random.Random(SEED)
    rng.shuffle(all_pairs)

    n = len(all_pairs)
    n_train = round(n * RATIOS["train"])
    n_valid = round(n * RATIOS["valid"])

    split_assignment = (
        [("train", p) for p in all_pairs[:n_train]]
        + [("valid", p) for p in all_pairs[n_train:n_train + n_valid]]
        + [("test", p) for p in all_pairs[n_train + n_valid:]]
    )

    counts = {"train": 0, "valid": 0, "test": 0}
    class_counts = {"train": [0, 0, 0], "valid": [0, 0, 0], "test": [0, 0, 0]}
    for split, (img_path, new_name, lines_out) in split_assignment:
        images_out = DST / split / "images"
        labels_out = DST / split / "labels"
        images_out.mkdir(parents=True, exist_ok=True)
        labels_out.mkdir(parents=True, exist_ok=True)

        shutil.copy2(img_path, images_out / new_name)
        label_name = Path(new_name).stem + ".txt"
        (labels_out / label_name).write_text(
            "\n".join(lines_out) + ("\n" if lines_out else ""), encoding="utf-8"
        )
        counts[split] += 1
        for line in lines_out:
            class_counts[split][int(line.split()[0])] += 1

    print("\n=== Final split ===")
    for split in ["train", "valid", "test"]:
        pct = counts[split] / n * 100
        cc = class_counts[split]
        print(f"{split}: {counts[split]} images ({pct:.1f}%) -- baby={cc[0]} blanket={cc[1]} toy={cc[2]}")

    data_yaml = DST / "data.yaml"
    data_yaml.write_text(
        "train: ../train/images\n"
        "val: ../valid/images\n"
        "test: ../test/images\n\n"
        f"nc: {len(NEW_NAMES)}\n"
        f"names: {NEW_NAMES}\n",
        encoding="utf-8",
    )
    print(f"\nWrote {data_yaml}")
    print(f"Merged dataset ready at: {DST}/ (seed={SEED}, reproducible)")


if __name__ == "__main__":
    main()
