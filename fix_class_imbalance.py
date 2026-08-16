#!/usr/bin/env python3
"""
Fix the babyMonitor2 dataset's class imbalance: the 'other' class has only
5 labeled instances across 1856 images (train=3, valid=1, test=1) -- far too
few for any model to learn, and it drags overall Precision/Recall/F1 down
because the model can never predict it correctly (confirmed by the trained
model's confusion matrix: 0% recall for 'other').

BabyWatcher's danger-detection logic in src/detector.py treats every
non-'baby' detection identically (any detected object near the mouth is a
candidate, regardless of whether it's a blanket/other/toy) -- so dropping
'other' does not remove any functional distinction the system actually uses.

This script creates a new 3-class copy of the dataset (baby, blanket, toy)
at babyMonitor2_3class.v1i.yolov8/, leaving the original untouched:
  - drops every label line for class 2 ('other')
  - remaps class 3 ('toy') -> class 2, so indices stay contiguous 0..2
  - copies images unchanged
"""
import shutil
from pathlib import Path

SRC = Path("babyMonitor2.v1i.yolov8")
DST = Path("babyMonitor2_3class.v1i.yolov8")
SPLITS = ["train", "valid", "test"]

OLD_NAMES = ["baby", "blanket", "other", "toy"]
NEW_NAMES = ["baby", "blanket", "toy"]
# old class id -> new class id ('other' maps to None = dropped)
REMAP = {0: 0, 1: 1, 2: None, 3: 2}


def process_split(split: str) -> tuple[int, int]:
    src_images = SRC / split / "images"
    src_labels = SRC / split / "labels"
    dst_images = DST / split / "images"
    dst_labels = DST / split / "labels"
    dst_images.mkdir(parents=True, exist_ok=True)
    dst_labels.mkdir(parents=True, exist_ok=True)

    dropped = 0
    kept = 0

    for img_path in src_images.iterdir():
        shutil.copy2(img_path, dst_images / img_path.name)

    for label_path in src_labels.glob("*.txt"):
        lines_out = []
        for line in label_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            parts = line.split()
            old_cls = int(parts[0])
            new_cls = REMAP.get(old_cls)
            if new_cls is None:
                dropped += 1
                continue
            kept += 1
            lines_out.append(" ".join([str(new_cls)] + parts[1:]))
        (dst_labels / label_path.name).write_text(
            "\n".join(lines_out) + ("\n" if lines_out else ""), encoding="utf-8"
        )

    return dropped, kept


def main() -> None:
    if DST.exists():
        raise SystemExit(f"{DST} already exists -- remove it first if you want to regenerate.")

    total_dropped = 0
    total_kept = 0
    for split in SPLITS:
        dropped, kept = process_split(split)
        total_dropped += dropped
        total_kept += kept
        print(f"{split}: kept {kept} boxes, dropped {dropped} 'other' boxes")

    data_yaml = DST / "data.yaml"
    data_yaml.write_text(
        "train: ../train/images\n"
        "val: ../valid/images\n"
        "test: ../test/images\n\n"
        f"nc: {len(NEW_NAMES)}\n"
        f"names: {NEW_NAMES}\n",
        encoding="utf-8",
    )

    print(f"\nTotal: kept {total_kept} boxes, dropped {total_dropped} 'other' boxes")
    print(f"Wrote {data_yaml}")
    print(f"New dataset ready at: {DST}/")


if __name__ == "__main__":
    main()
