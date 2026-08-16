#!/usr/bin/env python3
"""
Re-split the babyMonitor2_3class dataset from Roboflow's original 70/20/10
train/valid/test assignment into 80/10/10, for a modest-sized dataset (1594
images total) where maximizing training data matters more than keeping a
large validation set -- see chat discussion for the full rationale.

Pools every image+label pair from the existing train/valid/test folders,
shuffles with a fixed seed (reproducible), and re-splits 80/10/10.
"""
import random
import shutil
from pathlib import Path

SRC = Path("babyMonitor2_3class.v1i.yolov8")
DST = Path("babyMonitor2_3class_split80.v1i.yolov8")
SPLITS_IN = ["train", "valid", "test"]
RATIOS = {"train": 0.8, "valid": 0.1, "test": 0.1}
SEED = 42

NAMES = ["baby", "blanket", "toy"]


def main() -> None:
    if DST.exists():
        raise SystemExit(f"{DST} already exists -- remove it first if you want to regenerate.")

    pairs = []
    for split in SPLITS_IN:
        images_dir = SRC / split / "images"
        labels_dir = SRC / split / "labels"
        for img_path in images_dir.iterdir():
            label_path = labels_dir / (img_path.stem + ".txt")
            pairs.append((img_path, label_path))

    print(f"Pooled {len(pairs)} image/label pairs from {SRC}/{{train,valid,test}}")

    rng = random.Random(SEED)
    rng.shuffle(pairs)

    n = len(pairs)
    n_train = round(n * RATIOS["train"])
    n_valid = round(n * RATIOS["valid"])
    # test gets the remainder, so the three counts always sum to n exactly
    n_test = n - n_train - n_valid

    split_assignment = (
        [("train", p) for p in pairs[:n_train]]
        + [("valid", p) for p in pairs[n_train:n_train + n_valid]]
        + [("test", p) for p in pairs[n_train + n_valid:]]
    )

    counts = {"train": 0, "valid": 0, "test": 0}
    for split, (img_path, label_path) in split_assignment:
        images_out = DST / split / "images"
        labels_out = DST / split / "labels"
        images_out.mkdir(parents=True, exist_ok=True)
        labels_out.mkdir(parents=True, exist_ok=True)

        shutil.copy2(img_path, images_out / img_path.name)
        if label_path.exists():
            shutil.copy2(label_path, labels_out / label_path.name)
        else:
            (labels_out / label_path.name).write_text("", encoding="utf-8")
        counts[split] += 1

    for split in ["train", "valid", "test"]:
        pct = counts[split] / n * 100
        print(f"{split}: {counts[split]} images ({pct:.1f}%)")

    data_yaml = DST / "data.yaml"
    data_yaml.write_text(
        "train: ../train/images\n"
        "val: ../valid/images\n"
        "test: ../test/images\n\n"
        f"nc: {len(NAMES)}\n"
        f"names: {NAMES}\n",
        encoding="utf-8",
    )
    print(f"\nWrote {data_yaml}")
    print(f"New dataset ready at: {DST}/ (seed={SEED}, reproducible)")


if __name__ == "__main__":
    main()
