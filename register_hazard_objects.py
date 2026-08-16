#!/usr/bin/env python3
"""
Register caregiver-photographed dangerous objects (buttons, coins, small toy
parts, etc.) into the hazard gallery used by src/hazard_gallery.py.

The object being registered is, by definition, something the object detector
was never trained on (that's the whole point of registering it -- it's an
arbitrary household hazard, not one of the trained baby/blanket/toy classes),
so the detector CANNOT be trusted to locate it automatically. The user draws
the box by hand (utils.select_box_by_mouse: drag a rectangle, ENTER/SPACE to
confirm, 'r' to redraw, 'c' to cancel) -- the object detector's own detection
is shown only as a visual hint underneath, never used to crop automatically.

The embedding itself comes from src/hazard_gallery.py's extract_embedding()
(ImageNet-pretrained MobileNetV3), not from the object detector -- the
detector's own embed() was tried first and rejected: unrelated images
averaged ~0.93 cosine similarity in testing, i.e. it doesn't separate
different objects well enough to match against (it's trained for a narrow
3-class task, not open-set similarity).

Usage:
    python register_hazard_objects.py --images photos/button.jpg photos/coin.jpg
    python register_hazard_objects.py --camera 0
"""
import argparse
import os
import sys
import uuid

import cv2
from ultralytics import YOLO

sys.path.insert(0, '.')
from src.config import Config
from src.hazard_gallery import HazardGallery, extract_embedding
from src.utils import select_box_by_mouse


def get_object_box(obj_model: YOLO, frame, conf_thresh: float = 0.15):
    """Return the highest-confidence non-background box (x1, y1, x2, y2), or
    None if nothing was detected. Display-only hint -- never used to crop,
    since the object being registered is by definition not one of the
    detector's trained classes and it usually won't find it at all."""
    results = obj_model.predict(frame, conf=conf_thresh, verbose=False)[0]
    if results.boxes is None or len(results.boxes) == 0:
        return None

    boxes = results.boxes.xyxy.cpu().numpy()
    confs = results.boxes.conf.cpu().numpy()
    best_idx = confs.argmax()
    x1, y1, x2, y2 = boxes[best_idx].astype(int)
    if x2 <= x1 or y2 <= y1:
        return None
    return int(x1), int(y1), int(x2), int(y2)


def select_box_manually(frame, hint_box=None, window_name: str = "Ve khung quanh vat the (ENTER=xong, r=ve lai, c=huy)"):
    """Let the caregiver drag a box by hand around the object. Returns
    (x1, y1, x2, y2), or None if the selection was cancelled/empty.

    hint_box (from get_object_box) is drawn first as a visual reference so
    the user has a starting point, but the user's own drag is always what
    gets used -- it is never auto-accepted."""
    display = frame.copy()
    if hint_box is not None:
        hx1, hy1, hx2, hy2 = hint_box
        cv2.rectangle(display, (hx1, hy1), (hx2, hy2), (0, 165, 255), 1)
        cv2.putText(display, "Goi y tu dong (khong dung de crop)", (hx1, max(20, hy1 - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 165, 255), 1)

    box = select_box_by_mouse(display, window_name)
    if box is not None:
        x1, y1, x2, y2 = box
        print(f"  Khung da ve: ({x1},{y1})-({x2},{y2}), kich thuoc {x2-x1}x{y2-y1}px")
    return box


def crop_from_box(frame, box):
    if box is None:
        return frame
    x1, y1, x2, y2 = box
    crop = frame[max(0, y1):y2, max(0, x1):x2]
    return crop if crop.size > 0 else frame


THUMBNAIL_DIR = os.path.join("hazard_gallery", "thumbnails")


def _save_thumbnail(crop) -> str:
    """Save the registered crop to disk so the gallery manager UI
    (src/hazard_manager.py) has something to actually show -- gallery.json
    itself only ever stored the embedding vector, never the image."""
    os.makedirs(THUMBNAIL_DIR, exist_ok=True)
    filename = f"{uuid.uuid4().hex[:12]}.jpg"
    path = os.path.join(THUMBNAIL_DIR, filename)
    cv2.imwrite(path, crop)
    return path


def _flush_stdin() -> None:
    """Drain any keystrokes buffered in the console before prompting.

    The ENTER pressed to confirm the box in the OpenCV window (see
    utils.select_box_by_mouse) is sometimes ALSO picked up by the terminal's
    own stdin buffer on Windows (the console keeps listening even while the
    OpenCV window nominally has focus) -- without this, the very next
    input() call below can silently receive that leftover Enter as an empty
    line, making it look like pressing Enter "doesn't let you type" the
    name: the prompt appears and immediately accepts blank input before the
    user types anything."""
    try:
        import msvcrt
        while msvcrt.kbhit():
            msvcrt.getch()
    except ImportError:
        pass  # not on Windows -- no equivalent buffering issue via cv2's Win32 window


def register_one(gallery: HazardGallery, frame, source_label: str, box) -> None:
    """Register the crop at `box` (must be a hand-drawn box from
    select_box_manually -- see module docstring for why)."""
    crop = crop_from_box(frame, box)
    embedding = extract_embedding(crop)

    _flush_stdin()
    name = input(f"  Tên vật thể (ví dụ 'cúc áo', 'đồng xu') cho {source_label}: ").strip()
    if not name:
        print("  Bỏ qua (không nhập tên).")
        return
    severity = input("  Mức độ (high/critical, Enter = high): ").strip().lower() or "high"
    if severity not in ("high", "critical"):
        print(f"  '{severity}' không hợp lệ, dùng 'high'.")
        severity = "high"

    thumbnail_path = _save_thumbnail(crop)
    gallery.add(name=name, embedding=embedding, severity=severity, source_image=source_label,
                thumbnail_path=thumbnail_path)
    print(f"  ✅ Đã đăng ký '{name}' (severity={severity})")


def run_camera_registration(obj_model: YOLO, gallery: HazardGallery, camera_index: int = 0) -> int:
    """Open a camera window; SPACE captures+registers a shot, 'q' closes it.

    Reused by both the CLI (`--camera`) and the pre-launch "Đăng ký vật nguy
    hiểm" button in src/launch_screen.py, so the two entry points behave
    identically instead of duplicating this loop.

    Returns the number of shots captured (not necessarily all registered --
    the user can leave the name prompt blank to skip a shot).
    """
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print(f"❌ Không mở được camera {camera_index}")
        return 0

    print("\n📷 Camera đang chạy. Nhấn SPACE để chụp, 'q' để thoát.")
    shot_count = 0
    consecutive_failures = 0
    # Windows/MSMF cameras commonly fail the first few grabFrame() calls right
    # after opening (warm-up delay) -- treat a handful of failed reads as
    # transient and retry, instead of exiting on the very first one.
    max_consecutive_failures = 30
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                consecutive_failures += 1
                if consecutive_failures >= max_consecutive_failures:
                    print(f"❌ Camera {camera_index} không trả về frame sau {max_consecutive_failures} lần thử.")
                    break
                continue
            consecutive_failures = 0
            cv2.imshow("Register Hazard Object - SPACE to capture, q to quit", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            if key == ord(' '):
                shot_count += 1
                label = f"camera_shot_{shot_count}"
                print(f"\n📸 Đã chụp ({label}) -- vẽ khung quanh vật thể trong cửa sổ mới.")
                hint_box = get_object_box(obj_model, frame)
                box = select_box_manually(frame, hint_box)
                if box is None:
                    print("  Bỏ qua (không vẽ khung / đã hủy).")
                    continue
                register_one(gallery, frame, label, box)
    finally:
        cap.release()
        cv2.destroyWindow("Register Hazard Object - SPACE to capture, q to quit")
    return shot_count


def run_image_registration(obj_model: YOLO, gallery: HazardGallery, image_paths) -> int:
    """Register hazard objects from a list of existing image file paths,
    instead of capturing new shots from a live camera.

    Reused by both the CLI (`--images`) and the "Đăng ký từ ảnh có sẵn" button
    in src/launch_screen.py, so both entry points behave identically.

    Returns the number of images successfully read (not necessarily all
    registered -- the user can cancel the box or leave the name blank).
    """
    registered = 0
    for img_path in image_paths:
        frame = cv2.imread(img_path)
        if frame is None:
            print(f"❌ Không đọc được ảnh: {img_path}")
            continue
        print(f"\n📸 {img_path} -- vẽ khung quanh vật thể trong cửa sổ hiện ra.")
        hint_box = get_object_box(obj_model, frame)
        box = select_box_manually(frame, hint_box)
        if box is None:
            print("  Bỏ qua (không vẽ khung / đã hủy).")
            continue
        register_one(gallery, frame, os.path.basename(img_path), box)
        registered += 1
    return registered


def main():
    parser = argparse.ArgumentParser(description="Register hazard objects into the BabyWatcher hazard gallery")
    parser.add_argument("--images", nargs="+", help="Đường dẫn ảnh vật nguy hiểm đã chụp sẵn")
    parser.add_argument("--camera", type=int, help="Chỉ số camera để chụp trực tiếp (ví dụ 0)")
    parser.add_argument("--config", default="config.yaml", help="Đường dẫn config.yaml")
    args = parser.parse_args()

    if not args.images and args.camera is None:
        parser.error("Cần --images hoặc --camera")

    config = Config(args.config)
    gallery_path = config.get("detection.hazard_gallery_path", "hazard_gallery/gallery.json")
    obj_model_path = config.get("models.object_model_path", "yolov8n.pt")

    print(f"🔄 Đang tải object model: {obj_model_path}")
    obj_model = YOLO(obj_model_path)
    gallery = HazardGallery(gallery_path)
    print(f"📦 Gallery hiện có {len(gallery.entries)} vật thể đã đăng ký ({gallery_path})")

    if args.images:
        run_image_registration(obj_model, gallery, args.images)

    if args.camera is not None:
        run_camera_registration(obj_model, gallery, args.camera)

    gallery.save()
    print(f"\n✅ Đã lưu {len(gallery.entries)} vật thể vào {gallery_path}")
    print("Cập nhật config.yaml: detection.hazard_gallery_path đúng đường dẫn trên để bật tính năng.")


if __name__ == "__main__":
    main()
