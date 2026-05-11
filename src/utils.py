"""Utility functions for BabyWatcher"""

import numpy as np
import cv2
from typing import Tuple, List


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
    Find nearest object to hand
    
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
