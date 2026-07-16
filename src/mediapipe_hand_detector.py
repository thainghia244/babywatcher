"""MediaPipe hand detection integration for BabyWatcher"""

import cv2
import numpy as np
from typing import Tuple, Optional, Dict, List

MEDIAPIPE_AVAILABLE = False
mp_hands = None
mp_drawing = None

try:
    import mediapipe
    if hasattr(mediapipe, 'solutions'):
        try:
            from mediapipe import solutions as mp_solutions
            mp_hands = mp_solutions.hands
            mp_drawing = mp_solutions.drawing_utils
            MEDIAPIPE_AVAILABLE = True
        except Exception:
            try:
                import mediapipe.python.solutions.hands as mp_hands_module
                import mediapipe.python.solutions.drawing_utils as mp_drawing_module
                mp_hands = mp_hands_module
                mp_drawing = mp_drawing_module
                MEDIAPIPE_AVAILABLE = True
            except Exception:
                print("⚠️  MediaPipe hand modules not available in this environment")
    else:
        try:
            from mediapipe.python.solutions import hands as mp_hands
            from mediapipe.python.solutions import drawing_utils as mp_drawing
            MEDIAPIPE_AVAILABLE = True
        except ImportError:
            try:
                from mediapipe import hands as mp_hands
                from mediapipe import drawing_utils as mp_drawing
                MEDIAPIPE_AVAILABLE = True
            except ImportError:
                print("⚠️  MediaPipe hand modules not available in this environment")
except ImportError:
    print("⚠️  MediaPipe not installed. Install with: pip install mediapipe")


class MediaPipeHandDetector:
    """Hand detection using MediaPipe Hands"""
    
    def __init__(self, max_hands: int = 2, min_detection_confidence: float = 0.5):
        """
        Initialize MediaPipe Hand Detector
        
        Args:
            max_hands: Maximum number of hands to detect
            min_detection_confidence: Minimum confidence threshold
        """
        if not MEDIAPIPE_AVAILABLE:
            raise RuntimeError("MediaPipe is not installed")
        
        self.mp_hands = mp_hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=True,
            max_num_hands=max_hands,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=0.5
        )
        self.mp_drawing = mp_drawing
    
    def detect(self, frame: np.ndarray) -> Optional[List[Dict]]:
        """
        Detect hands in frame
        
        Args:
            frame: Input frame (BGR)
        
        Returns:
            List of hand detections with keypoints or None if no hands detected
        """
        try:
            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(frame_rgb)
            
            if results.multi_hand_landmarks is None:
                return None
            
            hands_data = []
            for hand_idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                # Extract keypoints (21 points)
                keypoints = np.array([
                    [lm.x * frame.shape[1], lm.y * frame.shape[0]]
                    for lm in hand_landmarks.landmark
                ])
                
                # Determine handedness
                handedness = "Right"
                if results.multi_handedness:
                    handedness = results.multi_handedness[hand_idx].classification[0].label
                
                hands_data.append({
                    'keypoints': keypoints,
                    'handedness': handedness,
                    'landmarks': hand_landmarks
                })
            
            return hands_data
        
        except Exception as e:
            return None
    
    def get_index_finger_tip(self, hand_data: Dict) -> Optional[np.ndarray]:
        """
        Extract index finger tip from hand data
        
        Args:
            hand_data: Hand detection result
        
        Returns:
            Index finger tip coordinates or None
        """
        try:
            # MediaPipe hand keypoint 8 is index finger tip
            keypoints = hand_data['keypoints']
            if keypoints.shape[0] > 8:
                return keypoints[8]
            return None
        except Exception:
            return None
    
    def draw_hand_skeleton(self, frame: np.ndarray, hand_data: Dict) -> None:
        """
        Draw hand skeleton on frame
        
        Args:
            frame: Input frame
            hand_data: Hand detection result
        """
        try:
            keypoints = hand_data['keypoints']
            
            # Draw keypoints
            for kpt in keypoints:
                x, y = int(kpt[0]), int(kpt[1])
                cv2.circle(frame, (x, y), 4, (0, 255, 0), -1)
            
            # Draw connections (hand skeleton)
            connections = [
                (0, 1), (1, 2), (2, 3), (3, 4),  # Thumb
                (0, 5), (5, 6), (6, 7), (7, 8),  # Index
                (0, 9), (9, 10), (10, 11), (11, 12),  # Middle
                (0, 13), (13, 14), (14, 15), (15, 16),  # Ring
                (0, 17), (17, 18), (18, 19), (19, 20),  # Pinky
                (5, 9), (9, 13), (13, 17)  # Palm connections
            ]
            
            for start, end in connections:
                if start < len(keypoints) and end < len(keypoints):
                    pt1 = tuple(keypoints[start].astype(int))
                    pt2 = tuple(keypoints[end].astype(int))
                    cv2.line(frame, pt1, pt2, (255, 0, 0), 2)
        
        except Exception as e:
            pass
