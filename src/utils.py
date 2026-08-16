"""Utility functions for BabyWatcher"""

import numpy as np
import cv2
from typing import Optional, Tuple, List


def select_box_by_mouse(frame: np.ndarray, window_name: str = "Ve khung (ENTER=xong, r=ve lai, c=huy)"
                        ) -> Optional[Tuple[int, int, int, int]]:
    """Custom click-drag rectangle selector -- used instead of cv2.selectROI,
    which was found to return coordinates misaligned with the actual image on
    at least one Windows setup (likely a display DPI-scaling mismatch inside
    its internal window handling). This owns the mouse callback and drawing
    loop directly against `frame`'s own pixel coordinates, so there is no
    intermediate scaling step that could introduce that kind of drift.

    Controls: drag to draw, ENTER/SPACE to confirm, 'r' to redraw, 'c' to cancel.
    Returns (x1, y1, x2, y2) in `frame`'s coordinate space, or None if cancelled.
    """
    state = {'dragging': False, 'start': None, 'end': None}

    def on_mouse(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            state['dragging'] = True
            state['start'] = (x, y)
            state['end'] = (x, y)
        elif event == cv2.EVENT_MOUSEMOVE and state['dragging']:
            state['end'] = (x, y)
        elif event == cv2.EVENT_LBUTTONUP:
            state['dragging'] = False
            state['end'] = (x, y)

    cv2.namedWindow(window_name)
    cv2.setMouseCallback(window_name, on_mouse)

    box = None
    try:
        while True:
            display = frame.copy()
            if state['start'] is not None and state['end'] is not None:
                cv2.rectangle(display, state['start'], state['end'], (0, 255, 0), 2)
            cv2.imshow(window_name, display)
            key = cv2.waitKey(20) & 0xFF

            if key in (13, 32):  # ENTER or SPACE
                if state['start'] is not None and state['end'] is not None:
                    x1, y1 = state['start']
                    x2, y2 = state['end']
                    x1, x2 = sorted((x1, x2))
                    y1, y2 = sorted((y1, y2))
                    if x2 > x1 and y2 > y1:
                        box = (x1, y1, x2, y2)
                break
            if key == ord('c'):
                box = None
                break
            if key == ord('r'):
                state['start'] = state['end'] = None
    finally:
        cv2.destroyWindow(window_name)

    return box


def distance(p1: np.ndarray, p2: np.ndarray) -> float:
    """
    Calculate Euclidean distance between two points
    
    Args:
        p1: Point 1 (x, y)
        p2: Point 2 (x, y)
    
    Returns:
        Distance value
    """
    return np.linalg.norm(np.array(p1) - np.array(p2))


def box_center(box: Tuple[float, float, float, float]) -> np.ndarray:
    """
    Get center point of bounding box
    
    Args:
        box: Bounding box (x1, y1, x2, y2)
    
    Returns:
        Center point as numpy array
    """
    x1, y1, x2, y2 = box
    return np.array([(x1 + x2) / 2, (y1 + y2) / 2])


def draw_skeleton(frame: np.ndarray, keypoints: np.ndarray) -> None:
    """
    Draw human skeleton on frame
    
    Args:
        frame: Input frame
        keypoints: Array of keypoint coordinates
    """
    # COCO pose skeleton connections (17 points)
    skeleton = [
        (0, 1), (0, 2),
        (1, 3), (2, 4),
        (5, 6),
        (5, 7), (7, 9),
        (6, 8), (8, 10),
        (5, 11), (6, 12),
        (11, 12),
        (11, 13), (13, 15),
        (12, 14), (14, 16)
    ]
    
    # Draw keypoints
    for x, y in keypoints:
        cv2.circle(frame, (int(x), int(y)), 4, (0, 255, 0), -1)
    
    # Draw connections
    for i, j in skeleton:
        if i < len(keypoints) and j < len(keypoints):
            x1, y1 = keypoints[i]
            x2, y2 = keypoints[j]
            cv2.line(frame, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 0), 2)


def get_person_keypoints(person_data: np.ndarray) -> dict:
    """
    Extract important keypoints from person pose data
    
    Args:
        person_data: Full keypoint array for person
    
    Returns:
        Dictionary with named keypoints
    
    Keypoint indices (COCO format):
        0: nose, 5: left_shoulder, 6: right_shoulder
        9: left_wrist, 10: right_wrist, 1: left_eye, 2: right_eye
    """
    return {
        'nose': person_data[0],
        'left_eye': person_data[1],
        'right_eye': person_data[2],
        'left_shoulder': person_data[5],
        'right_shoulder': person_data[6],
        'left_elbow': person_data[7],
        'right_elbow': person_data[8],
        'left_wrist': person_data[9],
        'right_wrist': person_data[10],
        'left_hip': person_data[11],
        'right_hip': person_data[12],
    }


def calculate_shoulder_width(left_shoulder: np.ndarray, 
                             right_shoulder: np.ndarray) -> float:
    """
    Calculate width between shoulders
    
    Args:
        left_shoulder: Left shoulder position
        right_shoulder: Right shoulder position
    
    Returns:
        Shoulder width
    """
    return distance(left_shoulder, right_shoulder)


def get_nearest_object(hand_position: np.ndarray,
                       objects: List[np.ndarray]) -> Tuple[float, int]:
    """
    Find nearest object to hand by object center.
    
    Args:
        hand_position: Hand coordinate
        objects: List of object centers
    
    Returns:
        Tuple of (distance, object_index)
    """
    if not objects:
        return (999.0, -1)
    
    distances = [distance(hand_position, obj) for obj in objects]
    min_dist = min(distances)
    min_idx = distances.index(min_dist)
    
    return (min_dist, min_idx)


def get_nearest_object_box(hand_position: np.ndarray,
                           object_boxes: List[Tuple[float, float, float, float]]) -> Tuple[float, int, np.ndarray]:
    """
    Find nearest object to hand using distance to box boundaries.
    
    Args:
        hand_position: Hand coordinate
        object_boxes: List of boxes (x1, y1, x2, y2)
    
    Returns:
        Tuple of (distance, object_index, nearest_point)
    """
    if not object_boxes:
        return (999.0, -1, np.array([0.0, 0.0]))
    
    distances = []
    nearest_points = []
    x, y = hand_position
    
    for box in object_boxes:
        x1, y1, x2, y2 = box
        closest_x = min(max(x, x1), x2)
        closest_y = min(max(y, y1), y2)
        nearest_point = np.array([closest_x, closest_y])
        nearest_points.append(nearest_point)
        distances.append(distance(hand_position, nearest_point))
    
    min_idx = int(np.argmin(distances))
    return (distances[min_idx], min_idx, nearest_points[min_idx])


def draw_distance_line(frame: np.ndarray,
                       p1: np.ndarray,
                       p2: np.ndarray,
                       label: str = "",
                       color: Tuple[int, int, int] = (0, 0, 255),
                       thickness: int = 2) -> None:
    """
    Draw line between two points with distance label
    
    Args:
        frame: Input frame
        p1: Point 1
        p2: Point 2
        label: Text label to display
        color: Line color (BGR)
        thickness: Line thickness
    """
    cv2.line(frame, tuple(p1.astype(int)), tuple(p2.astype(int)), color, thickness)
    
    if label:
        mid_x = int((p1[0] + p2[0]) / 2)
        mid_y = int((p1[1] + p2[1]) / 2)
        cv2.putText(frame, label, (mid_x, mid_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)


def draw_info_panel(frame: np.ndarray,
                    info_dict: dict,
                    panel_width: int = 250,
                    panel_height: int = 135) -> None:
    """
    Draw information panel on top-right corner
    
    Args:
        frame: Input frame
        info_dict: Dictionary with information to display
        panel_width: Width of info panel
        panel_height: Height of info panel
    
    Example:
        info = {
            'h_m_dist': 45.2,
            'h_m_thresh': 50.1,
            'h_o_dist': 999.0,
            'h_o_thresh': 60.0,
            'duration': 2.34,
            'status': 'HAND_TO_MOUTH'
        }
        draw_info_panel(frame, info)
    """
    frame_h, frame_w = frame.shape[:2]
    
    panel_x1 = frame_w - panel_width - 10
    panel_y1 = 85
    panel_x2 = frame_w - 10
    panel_y2 = panel_y1 + panel_height
    
    # Draw panel background
    cv2.rectangle(frame, (panel_x1, panel_y1), (panel_x2, panel_y2), (0, 0, 0), -1)
    
    font_small = 0.5
    font_status = 0.6
    thick = 1
    
    tx = panel_x1 + 10
    ty = panel_y1 + 22
    line_gap = 22
    
    # Draw information
    cv2.putText(frame, f"H-M Dist: {info_dict.get('h_m_dist', 0.0):.1f}",
                (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, font_small, (0, 0, 255), thick)
    cv2.putText(frame, f"H-M Thr : {info_dict.get('h_m_thresh', 0.0):.1f}",
                (tx, ty + line_gap), cv2.FONT_HERSHEY_SIMPLEX, font_small, (0, 0, 255), thick)
    cv2.putText(frame, f"H-O Dist: {info_dict.get('h_o_dist', 0.0):.1f}",
                (tx, ty + line_gap*2), cv2.FONT_HERSHEY_SIMPLEX, font_small, (255, 255, 0), thick)
    cv2.putText(frame, f"H-O Thr : {info_dict.get('h_o_thresh', 0.0):.1f}",
                (tx, ty + line_gap*3), cv2.FONT_HERSHEY_SIMPLEX, font_small, (255, 255, 0), thick)
    cv2.putText(frame, f"Time: {info_dict.get('duration', 0.0):.2f}s",
                (tx, ty + line_gap*4), cv2.FONT_HERSHEY_SIMPLEX, font_small, (255, 255, 255), thick)
    
    status = info_dict.get('status', 'SAFE')
    status_color = info_dict.get('status_color', (0, 255, 0))
    cv2.putText(frame, f"Status: {status}",
                (tx, ty + line_gap*5), cv2.FONT_HERSHEY_SIMPLEX, font_status, status_color, 2)


def draw_warning_banner(frame: np.ndarray, status: str) -> None:
    """
    Draw warning/danger banner at top
    
    Args:
        frame: Input frame
        status: Current status (SAFE, HAND_TO_MOUTH, OBJECT_TO_MOUTH)
    """
    if status == "HAND_TO_MOUTH":
        cv2.putText(frame, "WARNING: HAND TO MOUTH!",
                    (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 3)
    elif status == "OBJECT_TO_MOUTH":
        cv2.putText(frame, "DANGER: OBJECT TO MOUTH!",
                    (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)


def compose_display_frame(frame: np.ndarray,
                          info_dict: dict,
                          status: str,
                          show_info_panel: bool = True,
                          skeleton_enabled: bool = True) -> Tuple[np.ndarray, Tuple[int, int, int, int]]:
    """Compose a display canvas with a top warning banner, a right-side info panel, and a skeleton toggle button."""
    hazard_name = info_dict.get('hazard_name')

    frame_h, frame_w = frame.shape[:2]
    banner_height = 58 if status != "SAFE" else 0
    panel_width = 260 if show_info_panel else 0
    panel_height = (190 if hazard_name else 170) if show_info_panel else 0
    canvas_h = frame_h + banner_height + 20
    canvas_w = frame_w + (panel_width + 20 if show_info_panel else 0)

    canvas = np.full((canvas_h, canvas_w, 3), (20, 20, 20), dtype=np.uint8)

    if status != "SAFE":
        banner_y = 10
        banner_x = 10
        if status == "HAND_TO_MOUTH":
            cv2.rectangle(canvas, (5, 5), (canvas_w - 5, banner_height - 5), (0, 255, 255), 2)
            cv2.putText(canvas, "WARNING: HAND TO MOUTH!", (banner_x, 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        elif status == "OBJECT_TO_MOUTH":
            cv2.rectangle(canvas, (5, 5), (canvas_w - 5, banner_height - 5), (0, 0, 255), 2)
            cv2.putText(canvas, "DANGER: OBJECT TO MOUTH!", (banner_x, 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

    img_y = banner_height + 10
    img_x = 10
    canvas[img_y:img_y + frame_h, img_x:img_x + frame_w] = frame

    button_x1 = 10
    button_y1 = 10
    button_x2 = 125
    button_y2 = 40
    button_rect = (button_x1, button_y1, button_x2, button_y2)
    button_color = (0, 255, 0) if skeleton_enabled else (80, 80, 80)
    cv2.rectangle(canvas, (button_x1, button_y1), (button_x2, button_y2), button_color, 2)
    cv2.rectangle(canvas, (button_x1 + 2, button_y1 + 2), (button_x2 - 2, button_y2 - 2), button_color, -1)
    cv2.putText(canvas, "Skeleton: ON" if skeleton_enabled else "Skeleton: OFF",
                (button_x1 + 8, button_y1 + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

    if show_info_panel:
        panel_x1 = frame_w + 20
        panel_y1 = banner_height + 10
        panel_x2 = canvas_w - 10
        panel_y2 = panel_y1 + panel_height
        cv2.rectangle(canvas, (panel_x1, panel_y1), (panel_x2, panel_y2), (60, 60, 60), 2)
        cv2.rectangle(canvas, (panel_x1 + 4, panel_y1 + 4), (panel_x2 - 4, panel_y2 - 4), (80, 80, 80), -1)

        tx = panel_x1 + 12
        ty = panel_y1 + 20
        line_gap = 20
        cv2.putText(canvas, "Parameters", (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
        cv2.putText(canvas, f"H-M Dist: {info_dict.get('h_m_dist', 0.0):.1f}", (tx, ty + line_gap), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)
        cv2.putText(canvas, f"H-M Thr : {info_dict.get('h_m_thresh', 0.0):.1f}", (tx, ty + line_gap * 2), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)
        cv2.putText(canvas, f"H-O Dist: {info_dict.get('h_o_dist', 0.0):.1f}", (tx, ty + line_gap * 3), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 0), 1)
        cv2.putText(canvas, f"H-O Thr : {info_dict.get('h_o_thresh', 0.0):.1f}", (tx, ty + line_gap * 4), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 0), 1)
        cv2.putText(canvas, f"Time: {info_dict.get('duration', 0.0):.2f}s", (tx, ty + line_gap * 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
        cv2.putText(canvas, f"Status: {status}", (tx, ty + line_gap * 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, get_status_color(status), 1)
        line = 7
        if hazard_name:
            confident = info_dict.get('hazard_confident', True)
            label = f"Hazard: {hazard_name}" if confident else f"Hazard?: {hazard_name}"
            cv2.putText(canvas, label, (tx, ty + line_gap * line), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)
            line += 1
        cv2.putText(canvas, f"Skeleton: {'ON' if skeleton_enabled else 'OFF'}", (tx, ty + line_gap * line), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

    return canvas, button_rect


def get_status_color(status: str) -> Tuple[int, int, int]:
    """
    Get color for status
    
    Args:
        status: Status string
    
    Returns:
        Color tuple (BGR)
    """
    color_map = {
        'SAFE': (0, 255, 0),  # Green
        'HAND_TO_MOUTH': (0, 255, 255),  # Yellow
        'OBJECT_TO_MOUTH': (0, 0, 255),  # Red
    }
    return color_map.get(status, (128, 128, 128))  # Gray as default


def get_hand_keypoints(hand_data: np.ndarray) -> dict:
    """
    Extract hand keypoints from YOLO hand pose data (21 points)
    
    YOLO Hand keypoints (21 points):
        0-4:   Thumb (0: wrist, 1: IP, 2: PIP, 3: MCP, 4: tip)
        5-9:   Index (5: wrist, 6: IP, 7: PIP, 8: MCP, 9: tip)
        10-14: Middle
        15-19: Ring
        20:    Pinky
    
    Args:
        hand_data: Hand keypoint array (21, 2)
    
    Returns:
        Dictionary with named hand keypoints
    """
    if len(hand_data) < 21:
        return {}
    
    return {
        'thumb_tip': hand_data[4],
        'index_mcp': hand_data[8],      # Index Middle Carpal (knuckle)
        'index_pip': hand_data[7],      # Index Proximal Interphalangeal
        'index_tip': hand_data[9],      # Index finger tip - QUAN TRỌNG
        'middle_tip': hand_data[14],
        'ring_tip': hand_data[19],
        'pinky_tip': hand_data[20],
    }


def extract_hand_keypoints(hands_data, frame_shape: Tuple[int, int, int]) -> dict:
    """Extract hand landmarks and index finger tips from YOLO/MediaPipe hand results."""
    result = {
        'left_index_tip': None,
        'right_index_tip': None,
        'left_hand_keypoints': None,
        'right_hand_keypoints': None,
    }

    if hands_data is None:
        return result

    try:
        if isinstance(hands_data, list) and len(hands_data) > 0 and isinstance(hands_data[0], dict):
            for hand_data in hands_data:
                if 'keypoints' in hand_data and 'handedness' in hand_data:
                    keypoints = hand_data['keypoints']
                    handedness = hand_data['handedness']
                    if keypoints.shape[0] > 8:
                        index_tip = keypoints[8]
                        if handedness == 'Right':
                            result['right_index_tip'] = index_tip
                            result['right_hand_keypoints'] = keypoints
                        elif handedness == 'Left':
                            result['left_index_tip'] = index_tip
                            result['left_hand_keypoints'] = keypoints
            return result

        if hasattr(hands_data, 'keypoints'):
            if hands_data.keypoints is not None and hands_data.keypoints.xy is not None:
                keypoints_array = hands_data.keypoints.xy.cpu().numpy()
                if len(keypoints_array) > 0:
                    for keypoints in keypoints_array:
                        hand_center_x = np.mean(keypoints[:, 0]) if keypoints.shape[0] > 0 else 0
                        if hand_center_x < frame_shape[1] / 2:
                            result['left_hand_keypoints'] = keypoints
                            result['left_index_tip'] = keypoints[9] if len(keypoints) > 9 else None
                        else:
                            result['right_hand_keypoints'] = keypoints
                            result['right_index_tip'] = keypoints[9] if len(keypoints) > 9 else None
            return result

        if isinstance(hands_data, list):
            for hand in hands_data:
                try:
                    if hasattr(hand, 'keypoints'):
                        keypoints = hand.keypoints.xy.cpu().numpy()
                        if len(keypoints) > 0:
                            hand_points = keypoints[0]
                            if hasattr(hand, 'handedness') and hand.handedness is not None:
                                if 'Right' in str(hand.handedness):
                                    result['right_hand_keypoints'] = hand_points
                                    result['right_index_tip'] = hand_points[9] if len(hand_points) > 9 else None
                                elif 'Left' in str(hand.handedness):
                                    result['left_hand_keypoints'] = hand_points
                                    result['left_index_tip'] = hand_points[9] if len(hand_points) > 9 else None
                except Exception:
                    continue
    except Exception:
        pass

    return result


def extract_index_fingers(hands_data, frame_shape: Tuple[int, int, int]) -> dict:
    """Backward-compatible wrapper that returns only fingertip positions."""
    hand_keypoints = extract_hand_keypoints(hands_data, frame_shape)
    return {
        'left_index_tip': hand_keypoints.get('left_index_tip'),
        'right_index_tip': hand_keypoints.get('right_index_tip'),
    }
    
    if hands_data is None:
        return result
    
    try:
        # Handle MediaPipe format (list of dicts with 'keypoints' and 'handedness')
        if isinstance(hands_data, list) and len(hands_data) > 0 and isinstance(hands_data[0], dict):
            for hand_data in hands_data:
                if 'keypoints' in hand_data and 'handedness' in hand_data:
                    keypoints = hand_data['keypoints']
                    handedness = hand_data['handedness']
                    
                    # MediaPipe keypoint 8 is index finger tip
                    if keypoints.shape[0] > 8:
                        index_tip = keypoints[8]
                        if handedness == 'Right':
                            result['right_index_tip'] = index_tip
                        elif handedness == 'Left':
                            result['left_index_tip'] = index_tip
            return result
        
        # Handle YOLO format (Results object with keypoints)
        if hasattr(hands_data, 'keypoints'):
            if hands_data.keypoints is not None and hands_data.keypoints.xy is not None:
                keypoints_array = hands_data.keypoints.xy.cpu().numpy()
                
                if len(keypoints_array) > 0:
                    for idx, keypoints in enumerate(keypoints_array):
                        hand_keypoints = get_hand_keypoints(keypoints)
                        
                        # Simple heuristic: if center x is < frame_width/2, it's likely left hand
                        hand_center_x = np.mean(keypoints[:, 0]) if keypoints.shape[0] > 0 else 0
                        if hand_center_x < frame_shape[1] / 2:
                            result['left_index_tip'] = hand_keypoints.get('index_tip')
                        else:
                            result['right_index_tip'] = hand_keypoints.get('index_tip')
            return result
        
        # Handle list of hand objects (YOLO format)
        if isinstance(hands_data, list):
            for hand in hands_data:
                try:
                    if hasattr(hand, 'keypoints'):
                        keypoints = hand.keypoints.xy.cpu().numpy()
                        hand_keypoints = get_hand_keypoints(keypoints)
                        
                        if hasattr(hand, 'handedness') and hand.handedness is not None:
                            if 'Right' in str(hand.handedness):
                                result['right_index_tip'] = hand_keypoints.get('index_tip')
                            elif 'Left' in str(hand.handedness):
                                result['left_index_tip'] = hand_keypoints.get('index_tip')
                except Exception as e:
                    continue
    
    except Exception as e:
        pass  # Return empty result on error
    
    return result


def get_mouth_from_face(face_box: Tuple[float, float, float, float]) -> np.ndarray:
    """
    Extract mouth position from face bounding box
    
    Args:
        face_box: Face bounding box (x1, y1, x2, y2)
    
    Returns:
        Mouth position as (x, y) - center bottom of face box
    """
    x1, y1, x2, y2 = face_box
    mouth_x = (x1 + x2) / 2  # Center horizontally
    mouth_y = y1 + (y2 - y1) * 0.75  # 75% down vertically (mouth area)
    
    return np.array([mouth_x, mouth_y])


def get_face_mouth_keypoint(face_results) -> np.ndarray:
    """
    Extract mouth keypoint from face detection results
    
    Args:
        face_results: Face detection results from YOLO face model
    
    Returns:
        Mouth position as numpy array or None if no face detected
    """
    if not face_results or face_results.boxes is None or len(face_results.boxes) == 0:
        return None
    
    try:
        # Get first (most confident) face box
        face_box = face_results.boxes.xyxy[0].cpu().numpy()
        mouth = get_mouth_from_face(face_box)
        return mouth
    except Exception as e:
        return None


def get_nose_to_mouth_midpoint(nose: np.ndarray, mouth: np.ndarray) -> np.ndarray:
    """Compute a point halfway between the nose and the mouth."""
    if nose is None or mouth is None:
        return None
    return (np.array(nose) + np.array(mouth)) / 2.0


def get_estimated_mouth_point(nose: np.ndarray, shoulder_width: float) -> np.ndarray:
    """Estimate a mouth point from pose data when no face detector is available."""
    if nose is None:
        return None

    base_offset = max(12.0, shoulder_width * 0.28 if shoulder_width else 20.0)
    return np.array([nose[0], nose[1] + base_offset])
