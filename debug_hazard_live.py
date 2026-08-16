#!/usr/bin/env python3
"""
Live diagnostic for the hazard-gallery matching feature. Reads
info['hazard_debug'] straight from BabyWatcher.process_frame() -- the ACTUAL
best similarity computed by the real matching code on the ACTUAL box it
checked this frame (held object or wrist ROI), even when it's below the
match threshold -- so a near-miss is visible instead of only pass/fail.

Usage:
    python debug_hazard_live.py [camera_index]
"""
import sys

import cv2
import numpy as np

sys.path.insert(0, '.')
from src.detector import BabyWatcher
from src.hazard_gallery import extract_embedding
from src.utils import select_box_by_mouse


def check_manual_box(watcher: BabyWatcher, frame) -> None:
    """Freeze the current frame and let the user drag a box by hand (same
    utils.select_box_by_mouse as register_hazard_objects.py), then print
    similarity against every gallery entry for that exact crop -- removes any
    uncertainty about which region the automatic wrist-ROI/held-object logic
    picked, useful when you want to test "does THIS exact crop match" directly."""
    box = select_box_by_mouse(frame, "Ve khung de kiem tra (ENTER=xong, r=ve lai, c=huy)")
    if box is None:
        print("  (huy chon)")
        return
    x1, y1, x2, y2 = box
    print(f"  Khung da ve: ({x1},{y1})-({x2},{y2}), kich thuoc {x2-x1}x{y2-y1}px")
    crop = frame[y1:y2, x1:x2]
    print(f"  Crop thuc te: shape={crop.shape}")
    try:
        emb = extract_embedding(crop)
    except Exception as e:
        print(f"  Loi khi trich embedding: {e}")
        return

    from src.hazard_gallery import cosine_similarity
    print(f"  Similarity cua vung ban vua ve, voi tung vat trong gallery:")
    results = []
    for entry in watcher.hazard_gallery.entries:
        sim = cosine_similarity(emb, np.array(entry['embedding'], dtype=np.float32))
        results.append((entry['name'], sim))
    for name, sim in sorted(results, key=lambda r: -r[1]):
        if sim >= watcher.hazard_match_threshold:
            mark = "CHAC CHAN"
        elif sim >= watcher.hazard_possible_match_threshold:
            mark = "CO THE   "
        else:
            mark = "         "
        print(f"    {mark}  {name:20s} similarity={sim:.3f}")


def main():
    camera_index = int(sys.argv[1]) if len(sys.argv) > 1 else 0

    w = BabyWatcher('config.yaml')
    print(f"\nHazard gallery: enabled={w.hazard_gallery.enabled}, entries={len(w.hazard_gallery.entries)}")
    for e in w.hazard_gallery.entries:
        print(f"  - {e['name']} (severity={e['severity']})")
    print(f"Match threshold: {w.hazard_match_threshold}\n")

    if not w.hazard_gallery.enabled or not w.hazard_gallery.entries:
        print("❌ Gallery rỗng hoặc bị tắt -- không có gì để so khớp. Dừng lại.")
        return

    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print(f"❌ Không mở được camera {camera_index}")
        return

    print("Đang chạy. Đưa vật đã đăng ký lại gần miệng.")
    print("Nhấn 's' để dừng khung hình và TỰ VẼ khung quanh vật (kiểm tra chính xác vùng bạn chọn).")
    print("Nhấn 'q' để thoát.\n")
    consecutive_failures = 0
    frame_i = 0
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                consecutive_failures += 1
                if consecutive_failures >= 30:
                    print("❌ Camera không trả frame.")
                    break
                continue
            consecutive_failures = 0
            frame_i += 1

            out_frame, info = w.process_frame(frame)

            hand_near_mouth = info.get('hand_near_mouth')
            hazard_name = info.get('hazard_name')
            hazard_confident = info.get('hazard_confident')
            debug = info.get('hazard_debug')  # (name, similarity, box) or None

            if frame_i % 5 == 0:
                matched_label = hazard_name if hazard_name is None else f"{hazard_name} ({'chac chan' if hazard_confident else 'co the'})"
                bits = [f"hand_near_mouth={hand_near_mouth}", f"matched={matched_label}"]
                if debug is not None:
                    dname, dsim, _dbox = debug
                    bits.append(f"best_sim={dsim:.3f} vs '{dname}' (chac_chan>={w.hazard_match_threshold}, co_the>={w.hazard_possible_match_threshold})")
                else:
                    bits.append("(chua co box nao duoc kiem tra frame nay)")
                print("  ".join(bits))

            cv2.imshow("Hazard debug - q de thoat", out_frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            if key == ord('s'):
                print("\n[Da dung -- ve khung quanh vat trong cua so moi]")
                check_manual_box(w, frame)
                print()
    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
