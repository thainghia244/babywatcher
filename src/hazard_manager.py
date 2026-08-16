"""Gallery manager UI: view, rename and delete registered hazard objects.

Sits next to the two registration entry points (camera / existing image) in
src/launch_screen.py -- registering an object is one-way otherwise (no way to
fix a typo'd name or remove a bad registration short of hand-editing
gallery.json), which is the gap this fills.

Entries registered before src/hazard_gallery.py grew a `thumbnail` field
(e.g. the original "bật lửa"/"hột quẹt"/"pen" test entries) have no saved
image -- these render as a name-only placeholder tile instead of a photo,
they are not broken, just predate this feature.
"""

import os

import cv2
import numpy as np

from src.hazard_gallery import HazardGallery

WINDOW_NAME = "BabyWatcher - Quan ly vat nguy hiem"

_CANVAS_W = 820
_CANVAS_H = 620
_CELL_W = 190
_CELL_H = 190
_THUMB_SIZE = 140
_COLS = 4
_GRID_TOP = 70
_HELP_Y = _CANVAS_H - 20


def _load_thumbnail(entry: dict):
    path = entry.get('thumbnail')
    if not path or not os.path.exists(path):
        return None
    img = cv2.imread(path)
    if img is None:
        return None
    h, w = img.shape[:2]
    scale = _THUMB_SIZE / max(h, w)
    resized = cv2.resize(img, (max(1, int(w * scale)), max(1, int(h * scale))))
    canvas = np.full((_THUMB_SIZE, _THUMB_SIZE, 3), 40, dtype='uint8')
    rh, rw = resized.shape[:2]
    y0 = (_THUMB_SIZE - rh) // 2
    x0 = (_THUMB_SIZE - rw) // 2
    canvas[y0:y0 + rh, x0:x0 + rw] = resized
    return canvas


def _draw(entries, selected_id, page, rows_per_page):
    canvas = np.full((_CANVAS_H, _CANVAS_W, 3), (30, 30, 30), dtype='uint8')
    cv2.putText(canvas, f"Vat nguy hiem da dang ky: {len(entries)}", (20, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

    per_page = _COLS * rows_per_page
    start = page * per_page
    page_entries = entries[start:start + per_page]

    cell_positions = {}
    for i, entry in enumerate(page_entries):
        col = i % _COLS
        row = i // _COLS
        cx = 20 + col * _CELL_W
        cy = _GRID_TOP + row * _CELL_H
        cell_positions[entry['id']] = (cx, cy, cx + _CELL_W - 12, cy + _CELL_H - 12)

        is_selected = entry['id'] == selected_id
        border_color = (0, 200, 255) if is_selected else (90, 90, 90)
        thickness = 3 if is_selected else 1
        cv2.rectangle(canvas, (cx, cy), (cx + _CELL_W - 12, cy + _CELL_H - 12), border_color, thickness)

        thumb = _load_thumbnail(entry)
        tx, ty = cx + 10, cy + 8
        if thumb is not None:
            canvas[ty:ty + _THUMB_SIZE, tx:tx + _THUMB_SIZE] = thumb
        else:
            cv2.rectangle(canvas, (tx, ty), (tx + _THUMB_SIZE, ty + _THUMB_SIZE), (55, 55, 55), -1)
            cv2.putText(canvas, "(khong co", (tx + 14, ty + _THUMB_SIZE // 2 - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, (140, 140, 140), 1)
            cv2.putText(canvas, "anh)", (tx + 40, ty + _THUMB_SIZE // 2 + 14),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, (140, 140, 140), 1)

        name = entry.get('name', '?')
        label = name if len(name) <= 20 else name[:18] + '..'
        sev = entry.get('severity', 'high')
        sev_color = (0, 0, 255) if sev == 'critical' else (0, 165, 255)
        cv2.putText(canvas, label, (cx + 10, cy + _THUMB_SIZE + 26),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 1)
        cv2.putText(canvas, sev, (cx + 10, cy + _THUMB_SIZE + 44),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, sev_color, 1)

    total_pages = max(1, (len(entries) + per_page - 1) // per_page)
    if total_pages > 1:
        cv2.putText(canvas, f"Trang {page + 1}/{total_pages} (n = trang sau, p = trang truoc)",
                    (20, _HELP_Y - 22), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (170, 170, 170), 1)

    cv2.putText(canvas, "Click de chon | r = doi ten | d = xoa | q/ESC = dong",
                (20, _HELP_Y), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (170, 170, 170), 1)
    return canvas, cell_positions


def show_gallery_manager(gallery: HazardGallery) -> None:
    """Blocks until the user closes the window ('q'/ESC). Saves the gallery
    to disk immediately after every rename/delete, not just on close, so a
    crash or force-quit mid-session doesn't lose earlier edits."""
    if not gallery.entries:
        print("📦 Gallery đang rỗng -- chưa có vật nào để quản lý.")
        return

    rows_per_page = max(1, (_CANVAS_H - _GRID_TOP - 60) // _CELL_H)
    state = {'selected': None, 'page': 0}

    def on_mouse(event, x, y, flags, param):
        if event != cv2.EVENT_LBUTTONDOWN:
            return
        for entry_id, (x1, y1, x2, y2) in state['cells'].items():
            if x1 <= x <= x2 and y1 <= y <= y2:
                state['selected'] = entry_id
                return

    cv2.namedWindow(WINDOW_NAME)
    cv2.setMouseCallback(WINDOW_NAME, on_mouse)

    try:
        while True:
            canvas, cells = _draw(gallery.entries, state['selected'], state['page'], rows_per_page)
            state['cells'] = cells
            cv2.imshow(WINDOW_NAME, canvas)
            key = cv2.waitKey(30) & 0xFF

            if key in (ord('q'), 27):  # q or ESC
                break

            elif key == ord('r') and state['selected']:
                entry = next((e for e in gallery.entries if e['id'] == state['selected']), None)
                if entry:
                    new_name = input(f"Tên mới cho '{entry['name']}' (Enter để bỏ qua): ").strip()
                    if new_name:
                        gallery.rename(entry['id'], new_name)
                        gallery.save()
                        print(f"✅ Đã đổi tên thành '{new_name}'")

            elif key == ord('d') and state['selected']:
                entry = next((e for e in gallery.entries if e['id'] == state['selected']), None)
                if entry:
                    confirm = input(f"Xoá '{entry['name']}'? (y/N): ").strip().lower()
                    if confirm == 'y':
                        gallery.delete(entry['id'])
                        gallery.save()
                        state['selected'] = None
                        print(f"🗑️  Đã xoá '{entry['name']}'")
                        if not gallery.entries:
                            break

            elif key == ord('p'):  # previous page
                state['page'] = max(0, state['page'] - 1)
            elif key == ord('n'):  # next page
                per_page = _COLS * rows_per_page
                max_page = max(0, (len(gallery.entries) - 1) // per_page)
                state['page'] = min(max_page, state['page'] + 1)
    finally:
        cv2.destroyWindow(WINDOW_NAME)
