"""BabyWatcher - Main detection engine"""

import cv2
import numpy as np
import time
import os
import platform
import subprocess
from typing import Tuple, Optional, Dict, List, Union
from ultralytics import YOLO
import torch

from .config import Config
from .logger import EventLogger
from .alerts import AlertManager
from .performance import PerformanceMonitor, DetectionStats
from . import utils


class BabyWatcher:
    """Main BabyWatcher detection system"""

    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize BabyWatcher

        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        self.config = Config(config_path)

        # Detect platform
        self.platform = self._detect_platform()
        print(f"🖥️  Platform detected: {self.platform}")

        # Jetson-specific setup
        if self.platform == "jetson":
            self._setup_jetson()

        # Extract configuration values
        self.img_size = self.config.get("detection.img_size", 640)
        self.conf_thresh = self.config.get("detection.conf_thresh", 0.25)  # Reduced from 0.4
        self.hand_mouth_thresh = self.config.get("detection.hand_mouth_thresh", 45)
        self.hand_obj_thresh = self.config.get("detection.hand_obj_thresh", 60)
        self.dynamic_threshold = self.config.get("detection.dynamic_threshold", True)
        
        # Dynamic threshold multipliers
        self.hand_mouth_multiplier = self.config.get("detection.hand_mouth_multiplier", 0.6)
        self.hand_object_multiplier = self.config.get("detection.hand_object_multiplier", 0.6)
        self.object_mouth_multiplier = self.config.get("detection.object_mouth_multiplier", 0.6)
        self.object_region_multiplier = self.config.get("detection.object_region_multiplier", 1.2)
        
        # Enhanced object detection for small/occluded objects
        self.small_object_conf_thresh = self.config.get("detection.small_object_conf_thresh", 0.12)
        self.hand_closing_thresh = self.config.get("detection.hand_conf_thresh", 0.35)  # Hand confidence threshold
        self.inferred_object_distance_thresh = self.config.get("detection.inferred_object_distance_thresh", 22)  # If hand-mouth < 25px, infer object
        self.hand_near_object_conf_thresh = self.config.get("detection.hand_near_object_conf_thresh", 0.1)
        self.hand_near_object_roi_scale = self.config.get("detection.hand_near_object_roi_scale", 1.6)
        self.object_near_mouth_min_distance = self.config.get("detection.object_near_mouth_min_distance", 18)
        self.object_size_limit_multiplier = self.config.get("detection.object_size_limit_multiplier", 0.35)

        # Load models
        pose_model_path = self.config.get("models.pose_model_path", "yolo26n-pose.pt")
        obj_model_path = self.config.get("models.object_model_path", "yolo26n.pt")
        hand_model_path = self.config.get("models.hand_model_path", "")
        face_model_path = self.config.get("models.face_model_path", "yolov8n-face.pt")
        device_config = self.config.get("models.device", "auto")
        half_precision = self.config.get("models.half_precision", False)
        max_det = self.config.get("models.max_det", 300)
        enable_tensorrt = self.config.get("hardware.enable_tensorrt", True)

        # Auto-detect device with platform consideration
        device, device_name = self._setup_device(device_config)
        print(f"🖥️  Using {device_name}")

        # Load models with optimizations
        self.pose_model, self.obj_model, self.hand_model, self.face_model = self._load_models(
            pose_model_path, obj_model_path, hand_model_path, face_model_path,
            device, half_precision, max_det, enable_tensorrt
        )
        
        # Model availability flags
        self.use_hand_detection = False
        self.use_face_detection = self.config.get("detection.enable_face_detection", False)
        self.hand_detector = None
        print("ℹ️  MediaPipe hand detection disabled; using pose + object logic only")

        print("✅ Models loaded successfully")
        
        # Performance settings
        self.skip_frames = self.config.get("performance.skip_frames", 0)
        self.track_fps = self.config.get("performance.track_fps", True)
        self.max_det = max_det
        self.frames_skipped = 0
        
        # Performance monitoring
        self.perf_monitor = PerformanceMonitor() if self.track_fps else None
        self.detection_stats = DetectionStats()
        
        # Initialize logger
        log_dir = self.config.get("logging.log_dir", "logs")
        log_file = self.config.get("logging.log_file", "events_log.csv")
        self.logger = EventLogger(log_dir, log_file)
        
        # Initialize danger clips
        self.save_danger_clips = self.config.get("logging.save_danger_clips", True)
        self.danger_clips_dir = self.config.get("logging.clips_dir", "danger_clips")
        if self.save_danger_clips and not os.path.exists(self.danger_clips_dir):
            os.makedirs(self.danger_clips_dir)
            self.logger.log_info(f"Created danger clips directory: {self.danger_clips_dir}")
        
        # Initialize alert manager
        alerts_config = self.config.get_dict("alerts")
        email_config = self.config.get_dict("email")
        webhook_config = self.config.get_dict("webhook")
        self.alert_manager = AlertManager(alerts_config, email_config, webhook_config)
        
        # State variables
        self.danger_start_time = None
        self.frame_count = 0
        self.start_time = time.time()
        self.last_event_log_time = 0
        self.event_log_cooldown = 1.0  # Log events max once per second
        self.last_danger_clip_time = 0
        self.danger_clip_cooldown = 2.0  # Save danger clips max once per 2 seconds
        self.confirmation_frames = self.config.get("detection.confirmation_frames", 3)
        self._confirmation_counter = 0
        self._confirmed_status = "SAFE"
        self.proximity_history_window = self.config.get("detection.proximity_history_window", 3)
        self.proximity_history = []
        self.object_mouth_history_window = self.config.get("detection.object_mouth_history_window", 3)
        self.object_mouth_history = []
        self.sustained_danger_duration = self.config.get("detection.sustained_danger_duration", 0.6)
        self._danger_state_since = None
        
        # Display settings
        self.show_skeleton = self.config.get("display.show_skeleton", True)
        self.show_keypoints = self.config.get("display.show_keypoints", True)
        self.show_info_panel = self.config.get("display.show_info_panel", True)
        self.show_fps = self.config.get("display.show_fps", True)
        self._last_click_button = None
        
        self.logger.log_info("✅ BabyWatcher initialized successfully")
    
    def process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, Dict]:
        """
        Process single frame
        
        Args:
            frame: Input frame from video/image
        
        Returns:
            Tuple of (output_frame, info_dict)
        """
        frame_start = self.perf_monitor.start_frame() if self.perf_monitor else None
        self.frame_count += 1
        
        # Frame skipping for performance
        if self.skip_frames > 0 and self.frames_skipped < self.skip_frames:
            self.frames_skipped += 1
            # Return frame without processing
            return frame, {'skipped': True}
        
        self.frames_skipped = 0
        
        # Run YOLO predictions with optimized settings
        # Note: Let YOLO use its default input size for better object detection
        pose_results = self.pose_model.predict(
            frame, 
            conf=self.conf_thresh,
            max_det=self.max_det,
            verbose=False
        )[0]
        
        obj_results = self.obj_model.predict(
            frame, 
            conf=self.conf_thresh,
            max_det=self.max_det,
            verbose=False
        )[0]
        
        # Hand and face detection inputs.
        hand_results = None
        face_results = None
        hand_boxes = []
        hand_confs = []
        person_hand_state = []
        
        # Initialize variables
        wrists = []
        hand_near_mouth = False
        hand_holding_obj = False
        detected_objects = []
        detected_boxes = []
        object_candidate_boxes = []
        hand_boxes = []
        hand_confs = []
        
        d_hand_mouth = 999.0
        d_hand_obj = 999.0
        hand_mouth_thresh = self.hand_mouth_thresh
        hand_obj_thresh = self.hand_obj_thresh
        object_scan_threshold = max(20.0, self.hand_obj_thresh * 0.7)
        
        if self.use_hand_detection and self.hand_detector is not None:
            try:
                hand_results = self.hand_detector.detect(frame)
            except Exception:
                hand_results = None

        # ====== POSE DETECTION ======
        if pose_results.keypoints is not None:
            kpts = pose_results.keypoints.xy.cpu().numpy()
            person_boxes = pose_results.boxes.xyxy.cpu().numpy()
            
            for person, pbox in zip(kpts, person_boxes):
                # Extract keypoints
                keypoints = utils.get_person_keypoints(person)
                nose = keypoints['nose']
                left_shoulder = keypoints['left_shoulder']
                right_shoulder = keypoints['right_shoulder']
                left_wrist = keypoints['left_wrist']
                right_wrist = keypoints['right_wrist']
                
                wrists = [left_wrist, right_wrist]
                
                # Use the palm-center as the hand proxy. This is more representative of the hand
                # position than the raw wrist and is less sensitive to pose noise than a forearm point.
                index_fingers = None
                hand_landmarks = None
                mouth = None
                effective_wrists = self._get_palm_center_proxies(keypoints, wrists)
                shoulder_width = utils.calculate_shoulder_width(left_shoulder, right_shoulder)
                mouth_point = None
                if mouth is not None:
                    mouth_point = mouth
                if mouth_point is None:
                    mouth_point = utils.get_estimated_mouth_point(nose, shoulder_width)
                if mouth_point is None:
                    mouth_point = nose
                effective_mouth = utils.get_nose_to_mouth_midpoint(nose, mouth_point)
                if effective_mouth is None:
                    effective_mouth = nose
                
                # Draw skeleton
                if self.show_skeleton:
                    utils.draw_skeleton(frame, person)
                
                # Draw the nose-to-mouth reference line so it is visible on-screen.
                nose_pt = np.round(nose).astype(int)
                mouth_pt = np.round(mouth_point).astype(int)
                mid_pt = np.round(effective_mouth).astype(int)
                cv2.line(frame, tuple(nose_pt), tuple(mouth_pt), (255, 255, 0), 2)
                cv2.circle(frame, tuple(nose_pt), 5, (255, 0, 0), -1)
                cv2.circle(frame, tuple(mouth_pt), 5, (0, 255, 255), -1)
                cv2.circle(frame, tuple(mid_pt), 5, (255, 0, 255), -1)
                
                # Draw any hand landmarks if available from the hand detector.
                if self.use_hand_detection and hand_results is not None:
                    try:
                        for hand_data in hand_results:
                            self.hand_detector.draw_hand_skeleton(frame, hand_data)
                    except Exception:
                        pass

                if mouth is not None:
                    cv2.circle(frame, tuple(mouth.astype(int)), 6, (255, 0, 255), -1)  # Magenta
                    cv2.putText(frame, "Mouth", tuple((mouth + 10).astype(int)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 255), 1)
                
                # Draw person bounding box
                px1, py1, px2, py2 = pbox.astype(int)
                cv2.rectangle(frame, (px1, py1), (px2, py2), (0, 255, 255), 2)
                
                # Draw label
                cv2.rectangle(frame, (px1, py1 - 30), (px1 + 70, py1), (0, 0, 0), -1)
                cv2.putText(frame, "baby", (px1 + 5, py1 - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                
                # Dynamic thresholds based on shoulder width
                if self.dynamic_threshold:
                    shoulder_width = utils.calculate_shoulder_width(
                        left_shoulder, right_shoulder
                    )
                    hand_mouth_thresh = shoulder_width * self.hand_mouth_multiplier  # Use config multiplier
                    hand_obj_thresh = shoulder_width * self.hand_object_multiplier  # Use config multiplier
                    object_scan_threshold = self._get_object_proximity_threshold(shoulder_width)
                else:
                    hand_mouth_thresh = self.hand_mouth_thresh
                    hand_obj_thresh = self.hand_obj_thresh
                
                # Check hand-to-mouth distance using the more stable hand proxy.
                person_min_hand_distance = float('inf')
                for wrist, proxy_point in zip(wrists, effective_wrists):
                    d = utils.distance(proxy_point, effective_mouth)
                    person_min_hand_distance = min(person_min_hand_distance, d)
                    
                    # Draw the main distance line to the mouth using the palm-center proxy.
                    utils.draw_distance_line(
                        frame, proxy_point, effective_mouth,
                        label=f"H-M: {d:.1f}",
                        color=(0, 0, 255)
                    )

                    # Draw a visual link from the real wrist to the palm-center proxy.
                    try:
                        wrist_pt = np.round(wrist).astype(int)
                        proxy_pt = np.round(proxy_point).astype(int)
                        cv2.line(frame, tuple(wrist_pt), tuple(proxy_pt), (255, 255, 0), 1)
                        cv2.circle(frame, tuple(wrist_pt), 4, (0, 255, 255), -1)
                        cv2.circle(frame, tuple(proxy_pt), 4, (255, 255, 0), -1)
                    except Exception:
                        pass

                if person_min_hand_distance < float('inf'):
                    d_hand_mouth = min(d_hand_mouth, person_min_hand_distance)

                # Only mark as near-mouth when the minimum hand distance is clearly small.
                if self._evaluate_proximity_signal(person_min_hand_distance, hand_mouth_thresh):
                    hand_near_mouth = True
                    person_hand_state.append((person_min_hand_distance, hand_mouth_thresh))
        
        # ====== OBJECT DETECTION ======
        if obj_results.boxes is not None:
            boxes = obj_results.boxes.xyxy.cpu().numpy()
            confs = obj_results.boxes.conf.cpu().numpy()
            classes = obj_results.boxes.cls.cpu().numpy()
            
            for box, conf, cls in zip(boxes, confs, classes):
                x1, y1, x2, y2 = box
                # Use lower threshold for small objects that might be in hand
                box_area = (x2 - x1) * (y2 - y1)
                threshold = self.small_object_conf_thresh if box_area < 5000 else max(self.conf_thresh, self.hand_near_object_conf_thresh)
                
                if conf < threshold:
                    # Collect lower-confidence near-hand candidates for inference
                    if conf >= self.hand_near_object_conf_thresh:
                        object_candidate_boxes.append((x1, y1, x2, y2))
                    continue
                if int(cls) == 0:  # Skip person class
                    continue
                
                center = utils.box_center((x1, y1, x2, y2))
                detected_objects.append(center)
                detected_boxes.append((x1, y1, x2, y2))
                
                # Draw object bounding box
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), 
                              (0, 255, 0), 2)
        
        # ====== HAND-OBJECT INTERACTION ======
        if self.use_hand_detection and hand_results is not None:
            try:
                for hand_data in hand_results:
                    index_tip = self.hand_detector.get_index_finger_tip(hand_data)
                    if index_tip is not None:
                        wrists.append(np.array(index_tip, dtype=np.float32))
            except Exception:
                pass

        for wrist in wrists:
            nearest_dist, nearest_idx, nearest_point = utils.get_nearest_object_box(
                wrist, detected_boxes
            )
            
            if nearest_idx >= 0 and nearest_dist <= object_scan_threshold:
                d_hand_obj = min(d_hand_obj, nearest_dist)
                
                # Draw distance line to nearest object edge
                utils.draw_distance_line(
                    frame, wrist, nearest_point,
                    label=f"H-O: {nearest_dist:.1f}",
                    color=(255, 255, 0)
                )
                
                if nearest_dist <= object_scan_threshold:
                    hand_holding_obj = True

        # Evaluate object-to-mouth using a dynamic threshold scaled to body size.
        object_to_mouth_signal = False
        if hand_near_mouth and detected_boxes:
            # Use the nearest object to the mouth and compare it to a dynamic threshold.
            mouth_reference = effective_mouth if 'effective_mouth' in locals() else nose
            relevant_boxes = self._filter_objects_for_person(
                detected_boxes,
                mouth_reference,
                wrists,
                [left_shoulder, right_shoulder] if 'left_shoulder' in locals() else [],
                hand_obj_thresh
            )
            if relevant_boxes:
                nearest_object_distance = 999.0
                nearest_object_point = np.array([0.0, 0.0])
                for box in relevant_boxes:
                    x1, y1, x2, y2 = box
                    closest_x = min(max(mouth_reference[0], x1), x2)
                    closest_y = min(max(mouth_reference[1], y1), y2)
                    object_point = np.array([closest_x, closest_y])
                    dist = utils.distance(mouth_reference, object_point)
                    if dist < nearest_object_distance:
                        nearest_object_distance = dist
                        nearest_object_point = object_point

                if self._evaluate_object_to_mouth_signal(
                    nearest_object_distance,
                    person_min_hand_distance if 'person_min_hand_distance' in locals() else 999.0,
                    hand_near_mouth,
                    d_hand_obj,
                    hand_obj_thresh
                ):
                    object_to_mouth_signal = True
                    hand_holding_obj = True
                    d_hand_obj = min(d_hand_obj, nearest_object_distance)

        if hand_boxes and hand_confs.size > 0:
            combined_object_boxes = detected_boxes + object_candidate_boxes
            hand_grasp_signal = self._detect_hand_grasp_signal(
                hand_boxes,
                hand_confs,
                combined_object_boxes,
                nose,
                wrists,
                hand_obj_thresh
            )
            if hand_grasp_signal:
                hand_holding_obj = True
                d_hand_obj = min(d_hand_obj, hand_obj_thresh * 0.6)

        # Determine if there is a nearby low-confidence object candidate
        candidate_nearby = False
        if object_candidate_boxes:
            for wrist in wrists:
                candidate_dist, candidate_idx, candidate_point = utils.get_nearest_object_box(
                    wrist, object_candidate_boxes
                )
                if candidate_dist < hand_obj_thresh * 1.2:
                    candidate_nearby = True
                    break

        # ====== INFERRED OBJECT DETECTION (per person) ======
        # Only infer object hold if there is a strong grasping signal
        # AND a nearby candidate object or extremely close hand-to-mouth distance.
        if not hand_holding_obj and hand_near_mouth and d_hand_mouth < self.inferred_object_distance_thresh * 0.85:
            hand_closing = self._detect_hand_closing(keypoints, nose, wrists)
            if hand_closing and (candidate_nearby or d_hand_mouth < self.inferred_object_distance_thresh * 0.35):
                hand_holding_obj = True
                d_hand_obj = d_hand_mouth
        
        if object_to_mouth_signal:
            hand_holding_obj = True

        # ====== DETERMINE STATUS ======
        current_time = time.time()
        
        if not hand_near_mouth:
            self.danger_start_time = None
            self._danger_state_since = None
            danger_duration = 0.0
            self._confirmation_counter = 0
            self._confirmed_status = "SAFE"
            status = "SAFE"
        elif hand_near_mouth and not hand_holding_obj:
            if self.danger_start_time is None:
                self.danger_start_time = current_time
            danger_duration = current_time - self.danger_start_time
            status = self._resolve_confirmed_status("HAND_TO_MOUTH")
        else:  # hand_near_mouth and hand_holding_obj
            if self.danger_start_time is None:
                self.danger_start_time = current_time
            danger_duration = current_time - self.danger_start_time
            status = self._resolve_confirmed_status("OBJECT_TO_MOUTH")

        if status != "SAFE":
            if self._danger_state_since is None:
                self._danger_state_since = current_time
            if current_time - self._danger_state_since < self.sustained_danger_duration:
                status = "SAFE"
                danger_duration = 0.0
        else:
            self._danger_state_since = None
        
        # ====== TRIGGER ALERTS ======
        danger_threshold = self.config.get("alerts.danger_duration_threshold", 3.0)
        if danger_duration > danger_threshold:
            self.alert_manager.trigger_alert(status, danger_duration)
        
        # ====== LOG EVENTS ======
        current_log_time = time.time()
        if current_log_time - self.last_event_log_time > self.event_log_cooldown:
            if status != "SAFE":
                self.logger.log_event(
                    status=status,
                    duration=danger_duration,
                    hand_mouth_distance=d_hand_mouth,
                    hand_object_distance=d_hand_obj
                )
            self.last_event_log_time = current_log_time
        
        # ====== SAVE DANGER CLIPS ======
        current_clip_time = time.time()
        if self.save_danger_clips and status != "SAFE":
            if current_clip_time - self.last_danger_clip_time > self.danger_clip_cooldown:
                try:
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    clip_filename = f"{status}_{timestamp}.jpg"
                    clip_path = os.path.join(self.danger_clips_dir, clip_filename)
                    cv2.imwrite(clip_path, frame)
                    self.logger.log_info(f"💾 Saved danger clip: {clip_path}")
                    self.last_danger_clip_time = current_clip_time
                except Exception as e:
                    self.logger.log_error(f"Failed to save danger clip: {e}")
        
        # ====== DRAW COMPOSED DISPLAY ======
        info_dict = {
            'h_m_dist': d_hand_mouth,
            'h_m_thresh': hand_mouth_thresh,
            'h_o_dist': d_hand_obj,
            'h_o_thresh': hand_obj_thresh,
            'duration': danger_duration,
            'status': status,
            'status_color': utils.get_status_color(status)
        }
        frame, skeleton_button = utils.compose_display_frame(
            frame,
            info_dict,
            status,
            show_info_panel=self.show_info_panel,
            skeleton_enabled=self.show_skeleton
        )
        
        # ====== DRAW FPS ======
        perf_metrics = {}
        if self.show_fps and self.perf_monitor:
            perf_metrics = self.perf_monitor.end_frame(frame_start)
            fps = perf_metrics.get('fps', 0)
            cv2.putText(frame, f"FPS: {fps:.1f}",
                        (10, self.img_size - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        elif self.show_fps:
            elapsed = time.time() - self.start_time
            fps = self.frame_count / elapsed if elapsed > 0 else 0
            cv2.putText(frame, f"FPS: {fps:.1f}",
                        (10, self.img_size - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        # Update statistics
        is_danger = hand_near_mouth and hand_holding_obj
        self.detection_stats.update(
            detected_pose=bool(pose_results.keypoints),
            objects_count=len(detected_objects),
            is_danger=is_danger
        )
        
        return frame, {
            'status': status,
            'duration': danger_duration,
            'skeleton_button': skeleton_button,
            'hand_mouth_distance': d_hand_mouth,
            'hand_object_distance': d_hand_obj,
            'hand_near_mouth': hand_near_mouth,
            'hand_holding_obj': hand_holding_obj,
            'pose_detected': pose_results.keypoints is not None and len(pose_results.keypoints.xy) > 0,
            'num_objects': len(obj_results.boxes) if obj_results.boxes is not None else 0,
            **perf_metrics
        }
    
    def _get_object_proximity_threshold(self, shoulder_width: float) -> float:
        """Return the object-scanning threshold as half of the shoulder width, with a floor."""
        if shoulder_width is None:
            return max(20.0, self.hand_obj_thresh)
        return max(20.0, float(shoulder_width) * 0.5)

    def _is_object_near_mouth(self, box: Tuple[float, float, float, float], mouth_reference: np.ndarray,
                              threshold: float) -> bool:
        """Only treat an object as mouth-relevant when it is both close and plausibly small."""
        self.object_near_mouth_min_distance = getattr(self, 'object_near_mouth_min_distance', 18)
        self.object_size_limit_multiplier = getattr(self, 'object_size_limit_multiplier', 0.35)

        x1, y1, x2, y2 = box
        if x2 <= x1 or y2 <= y1:
            return False

        closest_point = np.array([
            np.clip(mouth_reference[0], x1, x2),
            np.clip(mouth_reference[1], y1, y2)
        ])
        mouth_distance = float(np.linalg.norm(mouth_reference - closest_point))

        if mouth_distance > max(self.object_near_mouth_min_distance, threshold * 0.8):
            return False

        box_area = (x2 - x1) * (y2 - y1)
        size_limit = max(3000.0, threshold * threshold * self.object_size_limit_multiplier)
        if box_area > size_limit:
            return False

        return True

    def _evaluate_proximity_signal(self, distance: float, threshold: float) -> bool:
        """Require the hand to stay close across history and remain close in the current frame."""
        self.proximity_history = getattr(self, 'proximity_history', [])
        self.proximity_history_window = getattr(self, 'proximity_history_window', 3)

        current_signal = distance <= max(10.0, threshold * 0.85)
        self.proximity_history.append(current_signal)
        if len(self.proximity_history) > self.proximity_history_window:
            self.proximity_history.pop(0)

        if len(self.proximity_history) < self.proximity_history_window:
            return False

        return (
            sum(self.proximity_history) >= max(2, int(self.proximity_history_window * 0.7))
            and current_signal
        )

    def _filter_objects_for_person(self, boxes: List[Tuple[float, float, float, float]], mouth_reference: np.ndarray,
                                   wrists: List[np.ndarray], shoulders: List[np.ndarray],
                                   reference_distance: float) -> List[Tuple[float, float, float, float]]:
        """Keep only objects in the upper-body chest-to-mouth region to reduce false positives."""
        self.object_region_multiplier = getattr(self, 'object_region_multiplier', 1.2)

        if not boxes:
            return []

        region_radius = max(reference_distance, 80.0) * self.object_region_multiplier
        filtered = []
        for box in boxes:
            if not self._is_object_near_mouth(box, mouth_reference, reference_distance):
                continue

            x1, y1, x2, y2 = box
            center = np.array([(x1 + x2) / 2.0, (y1 + y2) / 2.0])

            if shoulders and len(shoulders) >= 2:
                left_shoulder, right_shoulder = shoulders[0], shoulders[1]
                shoulder_mid = (left_shoulder + right_shoulder) / 2.0
                chest_y = shoulder_mid[1]
                mouth_y = mouth_reference[1]
                region_top = min(chest_y, mouth_y) - region_radius * 0.35
                region_bottom = max(chest_y, mouth_y) + region_radius * 0.35
                region_left = min(left_shoulder[0], mouth_reference[0], shoulder_mid[0]) - region_radius * 0.8
                region_right = max(right_shoulder[0], mouth_reference[0], shoulder_mid[0]) + region_radius * 0.8

                in_region = (
                    region_left <= center[0] <= region_right and
                    region_top <= center[1] <= region_bottom
                )
            else:
                in_region = False

            if not in_region and wrists:
                wrist_distances = [np.linalg.norm(center - wrist) for wrist in wrists]
                in_region = np.linalg.norm(center - mouth_reference) <= region_radius * 0.9 or min(wrist_distances) <= region_radius * 0.7

            if in_region:
                filtered.append(box)
        return filtered

    def _evaluate_object_to_mouth_signal(self, object_mouth_distance: float, hand_mouth_distance: float,
                                         hand_near_mouth: bool, hand_object_distance: float,
                                         threshold: float) -> bool:
        """Use a conservative dynamic threshold and require repeated evidence before triggering."""
        self.object_mouth_multiplier = getattr(self, 'object_mouth_multiplier', 0.6)
        self.object_mouth_history = getattr(self, 'object_mouth_history', [])
        self.object_mouth_history_window = getattr(self, 'object_mouth_history_window', 3)
        self.dynamic_threshold = getattr(self, 'dynamic_threshold', True)

        if not hand_near_mouth:
            return False

        body_scale = max(threshold, 1.0)
        object_threshold = body_scale * self.object_mouth_multiplier * 0.75
        hand_threshold = body_scale * 0.6
        object_hand_threshold = body_scale * 0.55

        object_close = object_mouth_distance <= object_threshold
        hand_close = hand_mouth_distance <= hand_threshold
        object_in_hand = hand_object_distance <= object_hand_threshold

        signal = object_close and hand_close and object_in_hand
        self.object_mouth_history.append(signal)
        if len(self.object_mouth_history) > self.object_mouth_history_window:
            self.object_mouth_history.pop(0)

        if len(self.object_mouth_history) < self.object_mouth_history_window:
            return False

        return sum(self.object_mouth_history) >= max(2, int(self.object_mouth_history_window * 0.7))

    def _resolve_confirmed_status(self, candidate_status: str) -> str:
        """Require the same danger signal to persist across several frames before reporting it."""
        if candidate_status == self._confirmed_status:
            self._confirmation_counter += 1
        else:
            self._confirmation_counter = 1
            self._confirmed_status = candidate_status

        if self._confirmation_counter >= self.confirmation_frames:
            return candidate_status
        return "SAFE"

    def process_video(self, video_path: str, output_path: Optional[str] = None):
        """
        Process video file
        
        Args:
            video_path: Path to input video
            output_path: Optional path to save output video
        """
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            self.logger.log_error(f"Cannot open video: {video_path}")
            return
        
        # Get video properties
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Setup output video writer if requested
        out = None
        if output_path:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (self.img_size, self.img_size))
        
        self.logger.log_info(f"Processing video: {video_path}")
        cv2.namedWindow("BabyWatcher", cv2.WINDOW_NORMAL)
        cv2.setMouseCallback("BabyWatcher", self._handle_mouse_toggle)
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                output_frame, info = self.process_frame(frame)
                self._last_click_button = info.get('skeleton_button')
                
                cv2.imshow("BabyWatcher", output_frame)
                
                if out:
                    out.write(output_frame)
                
                # Press 'q' to exit
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        
        finally:
            cap.release()
            if out:
                out.release()
            cv2.destroyAllWindows()
            self.logger.log_info("✅ Video processing completed")
    
    def process_camera(self, camera_index: Union[int, str] = 0, output_path: Optional[str] = None):
        """
        Process live camera feed.
        
        Args:
            camera_index: Camera index or device string
            output_path: Optional path to save output video
        """
        try:
            if isinstance(camera_index, str) and camera_index.isdigit():
                cap = cv2.VideoCapture(int(camera_index))
            else:
                cap = cv2.VideoCapture(camera_index)
        except Exception:
            cap = cv2.VideoCapture(camera_index)
        
        if not cap.isOpened():
            self.logger.log_error(f"Cannot open camera: {camera_index}")
            return
        
        fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
        
        out = None
        if output_path:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (self.img_size, self.img_size))
        
        self.logger.log_info(f"Processing camera: {camera_index}")
        cv2.namedWindow("BabyWatcher", cv2.WINDOW_NORMAL)
        cv2.setMouseCallback("BabyWatcher", self._handle_mouse_toggle)
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                output_frame, info = self.process_frame(frame)
                self._last_click_button = info.get('skeleton_button')
                
                cv2.imshow("BabyWatcher", output_frame)
                
                if out:
                    out.write(output_frame)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        finally:
            cap.release()
            if out:
                out.release()
            cv2.destroyAllWindows()
            self.logger.log_info("✅ Camera processing completed")
    
    def process_image(self, image_path: str, output_path: Optional[str] = None):
        """
        Process single image
        
        Args:
            image_path: Path to input image
            output_path: Optional path to save output image
        """
        frame = cv2.imread(image_path)
        
        if frame is None:
            self.logger.log_error(f"Cannot read image: {image_path}")
            return
        
        output_frame, info = self.process_frame(frame)
        self._last_click_button = info.get('skeleton_button')
        cv2.namedWindow("BabyWatcher", cv2.WINDOW_NORMAL)
        cv2.setMouseCallback("BabyWatcher", self._handle_mouse_toggle)
        cv2.imshow("BabyWatcher", output_frame)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        
        if output_path:
            cv2.imwrite(output_path, output_frame)
            self.logger.log_info(f"Output saved: {output_path}")
    
    def process_file(self, file_path: str, output_path: Optional[str] = None):
        """
        Process image or video file (auto-detect)
        
        Args:
            file_path: Path to input file
            output_path: Optional path to save output
        """
        ext = os.path.splitext(file_path)[1].lower()
        
        if file_path.isdigit() or file_path.lower() in ["camera", "cam", "webcam"] or file_path.lower().startswith("camera") or file_path.lower().startswith("cam"):
            # Support local camera by index or alias
            camera_index = 0
            if file_path.isdigit():
                camera_index = int(file_path)
            elif file_path.lower().startswith("camera") and file_path[6:].isdigit():
                camera_index = int(file_path[6:])
            elif file_path.lower().startswith("cam") and file_path[3:].isdigit():
                camera_index = int(file_path[3:])
            self.process_camera(camera_index, output_path)
        elif ext in [".jpg", ".jpeg", ".png", ".bmp"]:
            self.process_image(file_path, output_path)
        else:
            self.process_video(file_path, output_path)
    
    def get_stats(self, date: Optional[str] = None) -> Dict:
        """
        Get statistics for a specific date
        
        Args:
            date: Date in format 'YYYY-MM-DD' (default: today)
        
        Returns:
            Statistics dictionary
        """
        stats = self.logger.get_daily_stats(date)
        stats['detection_stats'] = self.detection_stats.get_summary()
        if self.perf_monitor:
            stats['performance'] = self.perf_monitor.get_summary()
        return stats
    
    def _detect_hand_grasp_signal(self, hand_boxes: np.ndarray, hand_confs: np.ndarray,
                                  object_boxes: List[Tuple[float, float, float, float]],
                                  mouth: np.ndarray, wrists: List[np.ndarray],
                                  proximity_thresh: float) -> bool:
        """Use hand-box detections to infer a grasping action near the mouth or object."""
        if hand_boxes is None or len(hand_boxes) == 0:
            return False

        if not object_boxes:
            return False

        for box, conf in zip(hand_boxes, hand_confs):
            if conf < self.hand_closing_thresh:
                continue

            x1, y1, x2, y2 = box
            hand_center = np.array([(x1 + x2) / 2, (y1 + y2) / 2])

            mouth_dist = utils.distance(hand_center, mouth)
            wrist_dist = min(
                [utils.distance(hand_center, wrist) for wrist in wrists] if wrists else [float('inf')]
            )

            if mouth_dist < proximity_thresh or wrist_dist < proximity_thresh * 0.8:
                nearest_dist, _, _ = utils.get_nearest_object_box(hand_center, object_boxes)
                if nearest_dist < proximity_thresh * 0.9:
                    return True

        return False

    def _handle_mouse_toggle(self, event, x, y, flags, param):
        """Toggle skeleton visibility when the skeleton button is clicked."""
        if event != cv2.EVENT_LBUTTONDOWN or self._last_click_button is None:
            return

        x1, y1, x2, y2 = self._last_click_button
        if x1 <= x <= x2 and y1 <= y <= y2:
            self.show_skeleton = not self.show_skeleton

    def _get_palm_center_proxies(self, keypoints: Dict, wrists: List) -> List[np.ndarray]:
        """Return a palm-center proxy for each hand using elbow and wrist information."""
        proxies = []
        if not wrists:
            return proxies

        try:
            left_wrist = keypoints.get('left_wrist', None)
            right_wrist = keypoints.get('right_wrist', None)
            left_elbow = keypoints.get('left_elbow', None)
            right_elbow = keypoints.get('right_elbow', None)

            for wrist in wrists:
                if wrist is None:
                    continue

                if left_wrist is not None and left_elbow is not None and np.allclose(wrist, left_wrist):
                    # Estimate palm center as a point halfway between wrist and elbow, shifted slightly outward.
                    direction = left_wrist - left_elbow
                    palm_center = left_wrist + 0.45 * direction
                    proxies.append(palm_center)
                elif right_wrist is not None and right_elbow is not None and np.allclose(wrist, right_wrist):
                    direction = right_wrist - right_elbow
                    palm_center = right_wrist + 0.45 * direction
                    proxies.append(palm_center)
                else:
                    proxies.append(wrist)
        except Exception:
            proxies = wrists

        return proxies

    def _detect_hand_closing(self, keypoints: Dict, nose: np.ndarray, wrists: List) -> bool:
        """
        Detect if hand is closed (holding object) based on hand region size.
        When hand is open, fingers extend outward. When closed, hand is compact.
        
        Args:
            keypoints: Dictionary of detected keypoints
            nose: Position of nose
            wrists: List of wrist positions
        
        Returns:
            True if hand appears to be closed/holding object
        """
        if not wrists:
            return False
        
        try:
            # Get hand-related keypoints
            left_wrist = keypoints.get('left_wrist', None)
            right_wrist = keypoints.get('right_wrist', None)
            left_elbow = keypoints.get('left_elbow', None)
            right_elbow = keypoints.get('right_elbow', None)
            
            # Check if hand is very close to mouth (indicating grasping)
            for wrist in wrists:
                dist_to_mouth = utils.distance(wrist, nose)
                
                if dist_to_mouth >= self.inferred_object_distance_thresh:
                    continue
                
                # Require elbow/wrist relation if elbow is available.
                if left_elbow is not None and left_wrist is not None:
                    elbow_to_mouth = utils.distance(left_elbow, nose)
                    wrist_to_mouth = dist_to_mouth
                    if wrist_to_mouth < elbow_to_mouth * 0.65:
                        return True
                
                if right_elbow is not None and right_wrist is not None:
                    elbow_to_mouth = utils.distance(right_elbow, nose)
                    wrist_to_mouth = dist_to_mouth
                    if wrist_to_mouth < elbow_to_mouth * 0.65:
                        return True
                
                # Only infer without elbow if hand is extremely close
                if dist_to_mouth < self.inferred_object_distance_thresh * 0.4:
                    return True
            
            return False
        except Exception:
            # If error in detection, do not infer held object to avoid false positives
            return False
    
    def _detect_platform(self) -> str:
        """Detect running platform"""
        try:
            # Check for Jetson
            with open('/proc/device-tree/model', 'r') as f:
                model = f.read().lower()
                if 'jetson' in model:
                    if 'nano' in model:
                        return "jetson_nano"
                    elif 'tx2' in model:
                        return "jetson_tx2"
                    elif 'xavier' in model:
                        return "jetson_xavier"
                    elif 'orin' in model:
                        return "jetson_orin"
                    else:
                        return "jetson"
        except:
            pass

        # Check for Raspberry Pi
        try:
            with open('/proc/cpuinfo', 'r') as f:
                if 'Raspberry Pi' in f.read():
                    return "raspberry_pi"
        except:
            pass

        # Default to desktop
        return "desktop"
    
    def _setup_jetson(self):
        """Setup Jetson-specific configurations"""
        try:
            # Set power mode
            power_mode = self.config.get("hardware.power_mode", "maxn")
            subprocess.run(['sudo', 'nvpmodel', '-m', power_mode], check=True)
            subprocess.run(['sudo', 'jetson_clocks'], check=True)
            print(f"🔌 Jetson power mode set to: {power_mode}")

            # Enable TensorRT if requested
            if self.config.get("hardware.enable_tensorrt", True):
                os.environ['USE_TENSORRT'] = '1'
                print("🚀 TensorRT enabled for Jetson")

        except Exception as e:
            print(f"⚠️  Jetson setup warning: {e}")
    
    def _setup_device(self, device_config: str) -> Tuple[str, str]:
        """Setup device with platform consideration"""
        if device_config.lower() == "auto":
            if self.platform.startswith("jetson"):
                # Jetson always has GPU
                device = "cuda:0"
                device_name = f"Jetson {self.platform.split('_')[1].upper()} GPU"
            elif torch.cuda.is_available():
                device = "cuda:0"
                device_name = "GPU (CUDA)"
            else:
                device = "cpu"
                device_name = "CPU"
        else:
            device = device_config
            if device == "cpu":
                device_name = "CPU"
            else:
                device_name = f"GPU ({device})"
        
        return device, device_name
    
    def _load_models(self, pose_path: str, obj_path: str, hand_path: str, face_path: str,
                    device: str, half_precision: bool, max_det: int, enable_tensorrt: bool):
        """Load models with platform-specific optimizations"""
        print("🔄 Loading YOLO pose and object models...")

        # Load pose model
        pose_model = YOLO(pose_path)
        if self.platform.startswith("jetson") and enable_tensorrt:
            try:
                pose_model.export(format='engine', device=device)
                pose_model = YOLO(pose_path.replace('.pt', '.engine'))
                print("🚀 Pose model converted to TensorRT")
            except Exception as e:
                print(f"⚠️  TensorRT conversion failed for pose model: {e}")
        pose_model.to(device)
        if half_precision and device != "cpu":
            pose_model.half()

        # Load object model
        obj_model = YOLO(obj_path)
        if self.platform.startswith("jetson") and enable_tensorrt:
            try:
                obj_model.export(format='engine', device=device)
                obj_model = YOLO(obj_path.replace('.pt', '.engine'))
                print("🚀 Object model converted to TensorRT")
            except Exception as e:
                print(f"⚠️  TensorRT conversion failed for object model: {e}")
        obj_model.to(device)
        if half_precision and device != "cpu":
            obj_model.half()

        hand_model = None
        face_model = None
        print("ℹ️  Hand and face models are disabled; using pose + object logic only")

        return pose_model, obj_model, hand_model, face_model
    
    def print_stats(self):
        """Print comprehensive statistics"""
        print("\n" + "="*60)
        print("📊 BABYWATCHER STATISTICS")
        print("="*60)
        print(f"Platform: {self.platform}")
        print(f"Total Frames Processed: {self.frame_count}")
        print(f"Total Runtime: {time.time() - self.start_time:.2f}s")
        
        if self.perf_monitor:
            perf_stats = self.perf_monitor.get_summary()
            print("\n⚡ PERFORMANCE METRICS")
            print("-"*30)
            for key, value in perf_stats.items():
                if isinstance(value, float):
                    print(f"{key:.<40} {value:.2f}")
                else:
                    print(f"{key:.<40} {value}")
        
        detection_stats = self.detection_stats.get_summary()
        print("\n🎯 DETECTION STATISTICS")
        print("-"*30)
        for key, value in detection_stats.items():
            if isinstance(value, float):
                print(f"{key:.<40} {value:.2f}")
            else:
                print(f"{key:.<40} {value}")
    
    def __repr__(self) -> str:
        return (f"<BabyWatcher: "
                f"Platform={self.platform}, "
                f"Models Loaded, "
                f"Frames: {self.frame_count}, "
                f"Alerts: {self.alert_manager}>")
