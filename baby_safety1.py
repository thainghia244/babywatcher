from ultralytics import YOLO
import cv2
import numpy as np
import time
import os

# =========================
# LOAD MODELS
# =========================
pose_model = YOLO("yolo26n-pose.pt")
obj_model  = YOLO("yolo26n.pt")

# =========================
# PARAMETERS
# =========================
IMG_SIZE = 640
CONF_THRESH = 0.4

danger_start_time = None


# =========================
# FUNCTIONS
# =========================
def distance(p1, p2):
    return np.linalg.norm(np.array(p1) - np.array(p2))


def box_center(box):
    x1, y1, x2, y2 = box
    return np.array([(x1 + x2) / 2, (y1 + y2) / 2])


def draw_skeleton(frame, keypoints):
    skeleton = [
        (0,1), (0,2),
        (1,3), (2,4),
        (5,6),
        (5,7), (7,9),
        (6,8), (8,10),
        (5,11), (6,12),
        (11,12),
        (11,13), (13,15),
        (12,14), (14,16)
    ]

    for x, y in keypoints:
        cv2.circle(frame, (int(x), int(y)), 4, (0, 255, 0), -1)

    for i, j in skeleton:
        x1, y1 = keypoints[i]
        x2, y2 = keypoints[j]
        cv2.line(frame, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 0), 2)


def process_frame(frame):
    global danger_start_time

    frame = cv2.resize(frame, (IMG_SIZE, IMG_SIZE))

    pose_results = pose_model.predict(frame, imgsz=640, conf=0.4, verbose=False)[0]
    obj_results  = obj_model.predict(frame, imgsz=640, conf=0.4, verbose=False)[0]

    wrists = []
    hand_near_mouth = False
    hand_holding_obj = False
    detected_objects = []

    hand_obj_thresh = 60
    hand_mouth_thresh = 45

    d_hand_mouth = 999.0
    d_hand_obj = 999.0

    # =========================
    # POSE
    # =========================
    if pose_results.keypoints is not None:
        kpts = pose_results.keypoints.xy.cpu().numpy()
        person_boxes = pose_results.boxes.xyxy.cpu().numpy()

        for person, pbox in zip(kpts, person_boxes):
            nose = person[0]
            left_shoulder = person[5]
            right_shoulder = person[6]
            left_wrist = person[9]
            right_wrist = person[10]

            wrists = [left_wrist, right_wrist]

            draw_skeleton(frame, person)

            px1, py1, px2, py2 = pbox.astype(int)
            cv2.rectangle(frame, (px1, py1), (px2, py2), (0, 255, 255), 2)

            cv2.rectangle(frame, (px1, py1 - 30), (px1 + 70, py1), (0, 0, 0), -1)
            cv2.putText(frame, "baby", (px1 + 5, py1 - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

            # Dynamic thresholds
            shoulder_width = distance(left_shoulder, right_shoulder)
            hand_mouth_thresh = shoulder_width * 0.9
            hand_obj_thresh   = shoulder_width * 0.8

            for wrist in wrists:
                d = distance(wrist, nose)

                if d < d_hand_mouth:
                    d_hand_mouth = d

                cv2.line(frame, tuple(wrist.astype(int)), tuple(nose.astype(int)), (0, 0, 255), 2)
                cv2.putText(frame, f"H-M: {d:.1f}",
                            (int((wrist[0] + nose[0]) / 2),
                             int((wrist[1] + nose[1]) / 2)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

                if d < hand_mouth_thresh:
                    hand_near_mouth = True

    # =========================
    # OBJECT
    # =========================
    if obj_results.boxes is not None:
        boxes = obj_results.boxes.xyxy.cpu().numpy()
        confs = obj_results.boxes.conf.cpu().numpy()
        classes = obj_results.boxes.cls.cpu().numpy()

        for box, conf, cls in zip(boxes, confs, classes):
            if conf < CONF_THRESH:
                continue
            if int(cls) == 0:
                continue

            x1, y1, x2, y2 = box
            center = box_center((x1, y1, x2, y2))
            detected_objects.append(center)

            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)

    # =========================
    # HAND HOLD OBJECT
    # =========================
    for wrist in wrists:
        nearest_obj = None
        nearest_dist = 999.0

        for obj_center in detected_objects:
            d = distance(wrist, obj_center)

            if d < nearest_dist:
                nearest_dist = d
                nearest_obj = obj_center

        if nearest_obj is not None:
            d_hand_obj = min(d_hand_obj, nearest_dist)

            cv2.line(frame, tuple(wrist.astype(int)), tuple(nearest_obj.astype(int)), (255, 255, 0), 2)
            cv2.putText(frame, f"H-O: {nearest_dist:.1f}",
                        (int((wrist[0] + nearest_obj[0]) / 2),
                         int((wrist[1] + nearest_obj[1]) / 2)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)

            if nearest_dist < hand_obj_thresh:
                hand_holding_obj = True

    # =========================
    # TIME LOGIC
    # =========================
    current_time = time.time()

    if not hand_near_mouth:
        danger_start_time = None
        danger_duration = 0.0
        status = "SAFE"
        color = (0, 255, 0)

    elif hand_near_mouth and not hand_holding_obj:
        if danger_start_time is None:
            danger_start_time = current_time
        danger_duration = current_time - danger_start_time
        status = "HAND TO MOUTH"
        color = (0, 255, 255)

    else:
        if danger_start_time is None:
            danger_start_time = current_time
        danger_duration = current_time - danger_start_time
        status = "OBJECT TO MOUTH"
        color = (0, 0, 255)

    # =========================
    # INFO PANEL (Top-Right)
    # =========================
    panel_w = 250
    panel_h = 135

    panel_x1 = IMG_SIZE - panel_w - 10
    panel_y1 = 85
    panel_x2 = IMG_SIZE - 10
    panel_y2 = panel_y1 + panel_h

    cv2.rectangle(frame, (panel_x1, panel_y1), (panel_x2, panel_y2), (0, 0, 0), -1)

    font_small = 0.5
    font_status = 0.6
    thick = 1

    tx = panel_x1 + 10
    ty = panel_y1 + 22
    line_gap = 22

    cv2.putText(frame, f"H-M Dist: {d_hand_mouth:.1f}", (tx, ty),
                cv2.FONT_HERSHEY_SIMPLEX, font_small, (0, 0, 255), thick)
    cv2.putText(frame, f"H-M Thr : {hand_mouth_thresh:.1f}", (tx, ty + line_gap),
                cv2.FONT_HERSHEY_SIMPLEX, font_small, (0, 0, 255), thick)
    cv2.putText(frame, f"H-O Dist: {d_hand_obj:.1f}", (tx, ty + line_gap*2),
                cv2.FONT_HERSHEY_SIMPLEX, font_small, (255, 255, 0), thick)
    cv2.putText(frame, f"H-O Thr : {hand_obj_thresh:.1f}", (tx, ty + line_gap*3),
                cv2.FONT_HERSHEY_SIMPLEX, font_small, (255, 255, 0), thick)
    cv2.putText(frame, f"Time: {danger_duration:.2f}s", (tx, ty + line_gap*4),
                cv2.FONT_HERSHEY_SIMPLEX, font_small, (255, 255, 255), thick)
    cv2.putText(frame, f"Status: {status}", (tx, ty + line_gap*5),
                cv2.FONT_HERSHEY_SIMPLEX, font_status, color, 2)

    # =========================
    # WARNING BANNER
    # =========================
    if status == "HAND TO MOUTH":
        cv2.putText(frame, "WARNING: HAND TO MOUTH!",
                    (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 3)

    elif status == "OBJECT TO MOUTH":
        cv2.putText(frame, "DANGER: OBJECT TO MOUTH!",
                    (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

    return frame


# =========================
# INPUT PATH
# =========================
input_path = "train1.jpg"
ext = os.path.splitext(input_path)[1].lower()

if ext in [".jpg", ".jpeg", ".png", ".bmp"]:
    frame = cv2.imread(input_path)
    output = process_frame(frame)

    cv2.imshow("YOLO26 BabyWatcher", output)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

else:
    cap = cv2.VideoCapture(input_path)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        output = process_frame(frame)
        cv2.imshow("YOLO26 BabyWatcher", output)

        if cv2.waitKey(1) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()
