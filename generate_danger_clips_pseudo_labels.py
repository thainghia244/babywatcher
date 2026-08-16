"""
Generate candidate YOLO bounding-box pseudo-labels for danger_clips/ (608 real
images captured during actual system usage) using the already-trained object
detector, so they can be reviewed/corrected and merged into the training set
as additional real-world data from the actual deployment camera/room.

Known caveat: every danger_clips image so far was captured while testing with
an ADULT stand-in (confirmed earlier), not a real infant -- so any 'baby'
prediction here is guaranteed wrong (it's really an adult). Those are dropped
entirely rather than pseudo-labeled. 'blanket' and 'toy' predictions are kept,
since real objects in the actual room are genuinely useful additional data
regardless of who's in frame -- but still need human review before training,
since pseudo-labels can still be wrong (missed objects, bad boxes, low
confidence, or the model's known confusion with objects like TVs/monitors --
see the 'over-sensitive to irrelevant objects' investigation earlier in this
project).
"""
from pathlib import Path

from ultralytics import YOLO

MODEL_PATH = 'babymonitor2_best.pt'
SRC_DIR = Path('danger_clips')
OUT_DIR = Path('danger_clips_pseudo.v1i.yolov8')
CONF_THRESH = 0.4

# Model's own class scheme (4-class, from the run that didn't apply the
# other-class fix): 0=baby, 1=blanket, 2=other, 3=toy.
DROP_CLASSES = {0, 2}  # baby (unreliable here -- see docstring), other (unusable, see earlier analysis)
REMAP = {1: 0, 3: 1}  # blanket->0, toy->1 in the new 2-class pseudo-label set
NEW_NAMES = ['blanket', 'toy']


def main():
    model = YOLO(MODEL_PATH)
    images_out = OUT_DIR / 'images'
    labels_out = OUT_DIR / 'labels'
    images_out.mkdir(parents=True, exist_ok=True)
    labels_out.mkdir(parents=True, exist_ok=True)

    image_paths = sorted(p for p in SRC_DIR.iterdir() if p.suffix.lower() in {'.jpg', '.jpeg', '.png'})
    print(f'Found {len(image_paths)} images in {SRC_DIR}')

    class_counts = {name: 0 for name in NEW_NAMES}
    confidences = {name: [] for name in NEW_NAMES}
    images_with_boxes = 0
    total_dropped_baby = 0

    for i, img_path in enumerate(image_paths):
        results = model.predict(str(img_path), conf=CONF_THRESH, verbose=False)[0]
        h, w = results.orig_shape

        lines = []
        if results.boxes is not None:
            for box, conf, cls in zip(results.boxes.xyxy.cpu().numpy(),
                                       results.boxes.conf.cpu().numpy(),
                                       results.boxes.cls.cpu().numpy()):
                cls = int(cls)
                if cls == 0:
                    total_dropped_baby += 1
                    continue
                if cls in DROP_CLASSES:
                    continue
                new_cls = REMAP[cls]
                x1, y1, x2, y2 = box
                cx, cy = (x1 + x2) / 2 / w, (y1 + y2) / 2 / h
                bw, bh = (x2 - x1) / w, (y2 - y1) / h
                lines.append(f'{new_cls} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}')
                name = NEW_NAMES[new_cls]
                class_counts[name] += 1
                confidences[name].append(float(conf))

        (labels_out / f'{img_path.stem}.txt').write_text(
            '\n'.join(lines) + ('\n' if lines else ''), encoding='utf-8'
        )
        import shutil
        shutil.copy2(img_path, images_out / img_path.name)
        if lines:
            images_with_boxes += 1

        if (i + 1) % 100 == 0:
            print(f'  [{i+1}/{len(image_paths)}]')

    data_yaml = OUT_DIR / 'data.yaml'
    data_yaml.write_text(
        "train: images\n\n"
        f"nc: {len(NEW_NAMES)}\nnames: {NEW_NAMES}\n",
        encoding='utf-8',
    )

    print(f'\n{images_with_boxes}/{len(image_paths)} images got at least one pseudo-label box')
    print(f'Dropped {total_dropped_baby} "baby" predictions (known-wrong: these are adults, not infants)')
    for name in NEW_NAMES:
        n = class_counts[name]
        avg_conf = sum(confidences[name]) / n if n else 0.0
        print(f'{name}: {n} boxes, avg confidence {avg_conf:.3f}')
    print(f'\nWrote {OUT_DIR}/ -- REVIEW BEFORE using for training (see module docstring).')


if __name__ == '__main__':
    main()
