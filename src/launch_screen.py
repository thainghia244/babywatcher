"""Pre-monitoring launch screen: a button to register hazard objects before
the camera/video feed starts, using the same click-region convention as the
skeleton toggle button in utils.compose_display_frame().
"""

import os
import re

import cv2
import numpy as np

DEFAULT_GALLERY_PATH = "hazard_gallery/gallery.json"
WINDOW_NAME = "BabyWatcher - Man hinh khoi dong"

_BUTTON_RECT = (40, 120, 340, 170)  # x1, y1, x2, y2 -- đăng ký qua camera
_IMAGE_BUTTON_RECT = (40, 180, 340, 230)  # x1, y1, x2, y2 -- đăng ký từ ảnh có sẵn
_MANAGE_BUTTON_RECT = (40, 240, 340, 290)  # x1, y1, x2, y2 -- xem/đổi tên/xoá vật đã đăng ký

# Matches the hazard_gallery_path line by itself, e.g. `  hazard_gallery_path: ""`
# (with an optional trailing comment), leaving indentation/comment untouched.
_GALLERY_PATH_LINE_RE = re.compile(r'^(\s*hazard_gallery_path:\s*)"[^"]*"(.*)$', re.MULTILINE)


def _persist_gallery_path(config_path: str, gallery_path: str) -> None:
    """Rewrite only the detection.hazard_gallery_path value in config.yaml,
    in place as text, so the setting survives future runs without disturbing
    the rest of the file -- a full yaml.safe_load()+yaml.dump() round-trip
    would silently strip every comment in config.yaml, which is hand-written
    and heavily annotated, so that's deliberately avoided here."""
    with open(config_path, 'r', encoding='utf-8') as f:
        text = f.read()

    def _replace(m: re.Match) -> str:
        trailing = m.group(2)
        if trailing.strip().startswith('# e.g.'):
            trailing = '  # cập nhật tự động qua giao diện đăng ký vật nguy hiểm'
        return f'{m.group(1)}"{gallery_path}"{trailing}'

    new_text, n = _GALLERY_PATH_LINE_RE.subn(_replace, text, count=1)
    if n == 0:
        print(f"⚠️  Không tìm thấy dòng 'hazard_gallery_path' trong {config_path} -- cập nhật thủ công.")
        return
    if new_text == text:
        return  # already correct, avoid an unnecessary write

    with open(config_path, 'w', encoding='utf-8') as f:
        f.write(new_text)


def _draw_screen(gallery_count: int):
    canvas = np.full((380, 480, 3), (30, 30, 30), dtype='uint8')

    cv2.putText(canvas, "BabyWatcher", (40, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
    cv2.putText(canvas, f"Da dang ky: {gallery_count} vat the nguy hiem", (40, 80),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

    x1, y1, x2, y2 = _BUTTON_RECT
    cv2.rectangle(canvas, (x1, y1), (x2, y2), (0, 200, 0), 2)
    cv2.rectangle(canvas, (x1 + 2, y1 + 2), (x2 - 2, y2 - 2), (0, 120, 0), -1)
    cv2.putText(canvas, "Dang ky qua camera", (x1 + 16, y1 + 32),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

    ix1, iy1, ix2, iy2 = _IMAGE_BUTTON_RECT
    cv2.rectangle(canvas, (ix1, iy1), (ix2, iy2), (200, 140, 0), 2)
    cv2.rectangle(canvas, (ix1 + 2, iy1 + 2), (ix2 - 2, iy2 - 2), (120, 80, 0), -1)
    cv2.putText(canvas, "Dang ky tu anh co san", (ix1 + 16, iy1 + 32),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

    mx1, my1, mx2, my2 = _MANAGE_BUTTON_RECT
    cv2.rectangle(canvas, (mx1, my1), (mx2, my2), (140, 140, 140), 2)
    cv2.rectangle(canvas, (mx1 + 2, my1 + 2), (mx2 - 2, my2 - 2), (70, 70, 70), -1)
    cv2.putText(canvas, "Xem / doi ten / xoa vat", (mx1 + 16, my1 + 32),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

    cv2.putText(canvas, "Nhan phim bat ky de bat dau giam sat", (40, 340),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
    return canvas


def show_launch_screen(watcher, config_path: str = "config.yaml") -> None:
    """Show the pre-monitoring screen. Blocks until the user presses a key
    (other than clicking the register button) to proceed to monitoring.

    Args:
        watcher: An already-constructed BabyWatcher -- reuses watcher.obj_model
            (avoids loading the object detector a second time) and hot-swaps
            watcher.hazard_gallery once registration finishes.
        config_path: Passed through so a freshly-chosen gallery path (when
            detection.hazard_gallery_path was empty/disabled) gets persisted.
    """
    # Imported lazily to avoid a hard dependency for callers that never touch
    # the hazard gallery (e.g. running in --no-display / headless mode).
    from register_hazard_objects import run_camera_registration, run_image_registration
    from src.hazard_gallery import HazardGallery
    from src.hazard_manager import show_gallery_manager

    clicked = {'camera': False, 'image': False, 'manage': False}

    def on_mouse(event, x, y, flags, param):
        if event != cv2.EVENT_LBUTTONDOWN:
            return
        x1, y1, x2, y2 = _BUTTON_RECT
        if x1 <= x <= x2 and y1 <= y <= y2:
            clicked['camera'] = True
            return
        ix1, iy1, ix2, iy2 = _IMAGE_BUTTON_RECT
        if ix1 <= x <= ix2 and iy1 <= y <= iy2:
            clicked['image'] = True
            return
        mx1, my1, mx2, my2 = _MANAGE_BUTTON_RECT
        if mx1 <= x <= mx2 and my1 <= y <= my2:
            clicked['manage'] = True

    def _pick_image_files():
        """Native "Open File" dialog (tkinter ships with standard Python on
        Windows) so the user can pick one or more existing photos instead of
        capturing new ones from the camera."""
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        paths = filedialog.askopenfilenames(
            title="Chọn ảnh vật nguy hiểm để đăng ký",
            filetypes=[("Ảnh", "*.jpg *.jpeg *.png *.bmp"), ("Tất cả file", "*.*")],
        )
        root.destroy()
        return list(paths)

    cv2.namedWindow(WINDOW_NAME)
    cv2.setMouseCallback(WINDOW_NAME, on_mouse)

    try:
        while True:
            gallery_count = len(watcher.hazard_gallery.entries)
            cv2.imshow(WINDOW_NAME, _draw_screen(gallery_count))
            key = cv2.waitKey(30) & 0xFF

            if clicked['camera'] or clicked['image'] or clicked['manage']:
                is_image_mode = clicked['image']
                is_manage_mode = clicked['manage']
                clicked['camera'] = False
                clicked['image'] = False
                clicked['manage'] = False
                gallery_path = watcher.hazard_gallery.gallery_path or DEFAULT_GALLERY_PATH
                # Reload from disk rather than reusing watcher.hazard_gallery in memory --
                # keeps this in sync if the file was touched another way between clicks.
                gallery = HazardGallery(gallery_path)

                if is_manage_mode:
                    show_gallery_manager(gallery)  # blocks; saves after every rename/delete itself
                elif is_image_mode:
                    image_paths = _pick_image_files()
                    if not image_paths:
                        print("Không chọn ảnh nào -- hủy đăng ký.")
                        continue
                    run_image_registration(watcher.obj_model, gallery, image_paths)
                    gallery.save()
                else:
                    run_camera_registration(watcher.obj_model, gallery, camera_index=0)
                    gallery.save()

                watcher.hazard_gallery = gallery  # hot-swap so THIS session uses the new entries too
                if not os.path.exists(config_path):
                    continue
                _persist_gallery_path(config_path, gallery_path)
                continue

            if key != 255:  # any real keypress (255 = none this tick) -> proceed
                break
    finally:
        cv2.destroyWindow(WINDOW_NAME)
