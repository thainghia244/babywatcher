"""BabyWatcher - Main detection engine"""

import cv2
import numpy as np
import time
import os
import platform
import subprocess
from collections import deque
from typing import Tuple, Optional, Dict, List, Union
from ultralytics import YOLO
import torch

from .config import Config
from .logger import EventLogger
from .alerts import AlertManager
from .performance import PerformanceMonitor, DetectionStats
from .hazard_gallery import HazardGallery, extract_embedding
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
        self.object_hand_hold_multiplier = self.config.get("detection.object_hand_hold_multiplier", 0.3)
        self.object_region_multiplier = self.config.get("detection.object_region_multiplier", 1.2)
        self.enable_fallback_fixed_threshold = self.config.get("detection.enable_fallback_fixed_threshold", True)
        self.fallback_hand_mouth_thresh = self.config.get("detection.fallback_hand_mouth_thresh", 60)
        self.fallback_hand_object_thresh = self.config.get("detection.fallback_hand_object_thresh", 60)
        self.fallback_object_mouth_thresh = self.config.get("detection.fallback_object_mouth_thresh", 60)
        
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

        self.device_name = device_name
        self.current_source = "unknown"

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

        # Initialize danger VIDEOS -- separate from the single-JPG "danger clip"
        # above. Uses a rolling pre-event frame buffer (see _update_video_buffer())
        # so the saved clip also captures the lead-up to the danger, not just the
        # moment it was confirmed.
        self.save_danger_videos = self.config.get("logging.save_danger_videos", True)
        self.danger_videos_dir = self.config.get("logging.danger_videos_dir", "danger_clips/videos")
        self.danger_video_pre_seconds = self.config.get("logging.danger_video_pre_seconds", 2.0)
        self.danger_video_post_seconds = self.config.get("logging.danger_video_post_seconds", 3.0)
        self.danger_video_max_seconds = self.config.get("logging.danger_video_max_seconds", 15.0)
        self.danger_video_fps = self.config.get("logging.danger_video_fps", 8)
        if self.save_danger_videos and not os.path.exists(self.danger_videos_dir):
            os.makedirs(self.danger_videos_dir)
            self.logger.log_info(f"Created danger videos directory: {self.danger_videos_dir}")
        self._video_frame_buffer = deque()  # (timestamp, annotated_frame) pairs, trimmed to pre_seconds
        self._video_writer = None
        self._video_writer_path = None
        self._video_recording_started_at = None
        self._video_last_danger_at = None
        self._video_status_label = "DANGER"

        # Initialize alert manager
        alerts_config = self.config.get_dict("alerts")
        email_config = self.config.get_dict("email")
        self.alert_manager = AlertManager(alerts_config, email_config)
        
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
        self._force_immediate_confirmation = False
        self._single_image_mode = False
        self.proximity_history_window = self.config.get("detection.proximity_history_window", 3)
        self.proximity_history = []
        self.object_mouth_history_window = self.config.get("detection.object_mouth_history_window", 3)
        self.object_mouth_history = []
        self.sustained_danger_duration = self.config.get("detection.sustained_danger_duration", 0.6)
        self._danger_state_since = None

        # Hazard gallery: reinforces (never gates) OBJECT_TO_MOUTH for objects the
        # caregiver pre-registered as dangerous -- see src/hazard_gallery.py.
        hazard_gallery_path = self.config.get("detection.hazard_gallery_path", "")
        self.hazard_match_threshold = self.config.get("detection.hazard_match_threshold", 0.75)
        self.hazard_possible_match_threshold = self.config.get("detection.hazard_possible_match_threshold", 0.5)
        self.hazard_confirmation_frames = self.config.get("detection.hazard_confirmation_frames", 1)
        self.hazard_sustained_danger_duration = self.config.get("detection.hazard_sustained_danger_duration", 0.2)
        self.hazard_gallery = HazardGallery(hazard_gallery_path)
        self._last_hazard_debug = None  # (name, similarity, box) from the most recent _match_hazard() attempt, pass or fail
        if self.hazard_gallery.enabled:
            print(f"⚠️  Hazard gallery loaded: {len(self.hazard_gallery.entries)} vật thể đã đăng ký")

        # Display settings
        self.show_skeleton = self.config.get("display.show_skeleton", True)
        self.show_keypoints = self.config.get("display.show_keypoints", True)
        self.show_info_panel = self.config.get("display.show_info_panel", True)
        self.show_fps = self.config.get("display.show_fps", True)
        self.display_width = int(self.config.get("display.frame_width", 960))
        self.display_height = int(self.config.get("display.frame_height", 960))
        self.display_enhance_contrast = self.config.get("display.enhance_contrast", True)
        self.display_sharpen = self.config.get("display.sharpen", True)
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

        # Undrawn copy for hazard-gallery embedding extraction -- `frame` gets
        # skeleton lines, distance labels, and boxes drawn onto it in place as
        # process_frame runs, and cropping from an already-annotated frame
        # would feed those overlaid pixels into the embedding, changing it
        # enough to drop below the match threshold even for the exact
        # registered object.
        clean_frame = frame.copy()

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
        hazard_match = None  # (name, severity, similarity) if a candidate object matches the hazard gallery
        hazard_match_box = None  # (x1, y1, x2, y2) of the box that matched, for drawing
        self._last_hazard_debug = None  # reset each frame -- see _match_hazard()
        
        d_hand_mouth = 999.0
        d_hand_obj = 999.0
        hand_mouth_thresh = self.hand_mouth_thresh
        hand_obj_thresh = self.hand_obj_thresh
        object_scan_threshold = max(20.0, self.hand_obj_thresh * 0.7)
        nose = None
        effective_mouth = None
        effective_wrists = []
        left_shoulder = None
        right_shoulder = None
        person_min_hand_distance = 999.0
        shoulder_width = None
        
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
                # _evaluate_proximity_signal() requires a few frames of history to agree
                # before it fires (see its docstring) -- fine for continuous video, but a
                # single-image call never accumulates that history, so it would always
                # return False. For single-image mode we still need *some* signal, but it
                # must stay grounded in this frame's actual measured distance: check
                # against the same threshold directly instead of unconditionally treating
                # every detected person as "hand near mouth" regardless of how far the
                # hand actually is (that unconditional bypass used to live here and made
                # process_image() flag nearly every photo as dangerous).
                if self._force_immediate_confirmation:
                    proximity_signal = person_min_hand_distance <= max(10.0, hand_mouth_thresh * 0.85)
                else:
                    proximity_signal = self._evaluate_proximity_signal(person_min_hand_distance, hand_mouth_thresh)
                if proximity_signal:
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

                # Draw object bounding box (blanket suppressed on-screen by
                # request -- still detected/used in the danger logic above,
                # just not drawn, since it cluttered the display).
                class_name = self.obj_model.names.get(int(cls), '') if hasattr(self.obj_model, 'names') else ''
                if class_name != 'blanket':
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

        # Priority step: identify what (if anything) is actually held in each
        # hand FIRST -- independent of, and before, any mouth-proximity
        # reasoning. This is the primary signal; the mouth-region rescan and
        # fallback thresholds below only run to cover what this step misses.
        held_object_box = None
        held_object_distance = 999.0
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

                hand_holding_obj = True
                if nearest_dist < held_object_distance:
                    held_object_distance = nearest_dist
                    held_object_box = detected_boxes[nearest_idx]

        mouth_reference = effective_mouth if effective_mouth is not None else nose

        # Hazard-gallery check, in priority order:
        #  1. The object already identified as held (highest confidence --
        #     the object detector found it AND it's close enough to a hand).
        #  2. Otherwise, a region around each wrist scanned directly against
        #     the gallery -- catches a registered hazard that doesn't
        #     visually resemble the trained baby/blanket/toy classes (e.g. a
        #     button, coin, pill) and so obj_model never detected it at all.
        if self.hazard_gallery.enabled and hand_near_mouth:
            if held_object_box is not None:
                match = self._match_hazard(clean_frame, held_object_box)
                if match is not None:
                    hazard_match = match
                    hazard_match_box = held_object_box
                    self._draw_hazard_overlay(frame, held_object_box, match)

            if hazard_match is None and effective_wrists:
                roi_half = max(20.0, hand_obj_thresh * 0.75)
                for wrist_point in effective_wrists:
                    wx, wy = wrist_point
                    wrist_box = (wx - roi_half, wy - roi_half, wx + roi_half, wy + roi_half)
                    match = self._match_hazard(clean_frame, wrist_box)
                    if match is not None:
                        hazard_match = match
                        hazard_match_box = wrist_box
                        self._draw_hazard_overlay(frame, wrist_box, match)
                        break

        # Evaluate object-to-mouth using a dynamic threshold scaled to body size.
        object_to_mouth_signal = hazard_match is not None
        if hazard_match is not None:
            hand_holding_obj = True
        if mouth_reference is not None and detected_boxes and (
            hand_near_mouth
            or hand_holding_obj
            or self._force_immediate_confirmation
            or self._has_near_mouth_object_context(detected_boxes, mouth_reference, hand_obj_thresh)
        ):
            # Use the nearest object to the mouth and compare it to a dynamic threshold.
            relevant_boxes = self._filter_objects_for_person(
                detected_boxes,
                mouth_reference,
                wrists,
                [left_shoulder, right_shoulder] if left_shoulder is not None and right_shoulder is not None else [],
                hand_obj_thresh
            )
            # Falling back to raw detected_boxes (when the stricter region
            # filter above found nothing) must still reject oversized boxes --
            # otherwise a person/animal the object detector misclassified as
            # toy/blanket could become the "nearest object" candidate simply
            # because nothing smaller happened to pass the region filter.
            size_limit = max(3000.0, hand_obj_thresh * hand_obj_thresh * self.object_size_limit_multiplier)
            sized_detected_boxes = [
                b for b in detected_boxes if (b[2] - b[0]) * (b[3] - b[1]) <= size_limit
            ]
            candidate_boxes = relevant_boxes if relevant_boxes else sized_detected_boxes
            if candidate_boxes:
                if hazard_match is None:
                    for candidate_box in candidate_boxes:
                        match = self._match_hazard(clean_frame, candidate_box)
                        if match is not None:
                            hazard_match = match
                            hazard_match_box = candidate_box
                            self._draw_hazard_overlay(frame, candidate_box, match)
                            break

                if held_object_box is not None:
                    # Reuse the object already identified as held, rather than
                    # re-deriving "nearest object" from the mouth-region scan --
                    # the held object is the higher-confidence signal (an
                    # object the detector found AND confirmed close to a hand).
                    nearest_object_point = self._get_box_point_nearest_reference(held_object_box, mouth_reference)
                    nearest_object_distance = utils.distance(mouth_reference, nearest_object_point)
                else:
                    nearest_object_distance, nearest_object_point = self._get_nearest_object_reference(
                        candidate_boxes,
                        mouth_reference
                    )

                hand_mouth_distance = person_min_hand_distance
                if effective_wrists:
                    hand_object_distance = min(
                        utils.distance(proxy_point, nearest_object_point)
                        for proxy_point in effective_wrists
                    )
                else:
                    hand_object_distance = d_hand_obj

                object_reference_distance = nearest_object_distance

                if self._force_immediate_confirmation and hand_near_mouth and candidate_boxes:
                    single_image_object_context = (
                        object_reference_distance <= max(80.0, hand_obj_thresh * 1.1)
                        or hand_object_distance <= max(80.0, hand_obj_thresh * 1.1)
                        or object_reference_distance <= max(220.0, hand_obj_thresh * 2.0)
                    )
                    if single_image_object_context:
                        object_to_mouth_signal = True
                        hand_holding_obj = True
                        d_hand_obj = min(d_hand_obj, hand_object_distance if hand_object_distance < 999 else object_reference_distance)
                elif self._evaluate_object_to_mouth_signal(
                    object_reference_distance,
                    hand_mouth_distance,
                    hand_near_mouth,
                    hand_object_distance,
                    hand_obj_thresh
                ) or self._should_trigger_proximity_only_signal(
                    object_reference_distance,
                    hand_near_mouth,
                    hand_object_distance,
                    hand_obj_thresh
                ):
                    object_to_mouth_signal = True
                    hand_holding_obj = True
                    d_hand_obj = min(d_hand_obj, hand_object_distance)
                elif self._evaluate_fallback_fixed_threshold(
                    object_reference_distance,
                    hand_mouth_distance,
                    hand_object_distance,
                    hand_near_mouth
                ):
                    object_to_mouth_signal = True
                    hand_holding_obj = True
                    d_hand_obj = min(d_hand_obj, hand_object_distance)

        if self._force_immediate_confirmation and hand_near_mouth and detected_boxes:
            mouth_reference = effective_mouth if effective_mouth is not None else nose
            if mouth_reference is not None:
                relevant_boxes = self._filter_objects_for_person(
                    detected_boxes,
                    mouth_reference,
                    wrists,
                    [left_shoulder, right_shoulder] if left_shoulder is not None and right_shoulder is not None else [],
                    hand_obj_thresh
                )
                if relevant_boxes:
                    nearest_object_distance, nearest_object_point = self._get_nearest_object_reference(
                        relevant_boxes,
                        mouth_reference
                    )
                    if nearest_object_distance <= max(220.0, hand_obj_thresh * 2.0):
                        object_to_mouth_signal = True
                        hand_holding_obj = True
                        d_hand_obj = min(d_hand_obj, nearest_object_distance)

        if hand_boxes and hand_confs.size > 0 and nose is not None:
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

        if object_to_mouth_signal:
            hand_holding_obj = True

        # ====== DETERMINE STATUS ======
        current_time = time.time()
        candidate_status = "SAFE"
        # A candidate object CONFIDENTLY matching the hazard gallery needs
        # fewer repeated frames/less sustained time to confirm -- see
        # src/hazard_gallery.py. A weaker "possible" match (hazard_match[3]
        # is False) still counts as an object-to-mouth signal but keeps
        # normal confirmation timing -- the evidence alone isn't strong
        # enough to justify skipping the usual sustained-signal safety margin.
        hazard_confident = hazard_match is not None and hazard_match[3]
        confirmation_override = self.hazard_confirmation_frames if hazard_confident else None

        if object_to_mouth_signal:
            hand_holding_obj = True
            candidate_status = "OBJECT_TO_MOUTH"
            if self.danger_start_time is None:
                self.danger_start_time = current_time
            danger_duration = current_time - self.danger_start_time
            status = self._resolve_confirmed_status(candidate_status, confirmation_override)
        # NOTE: single-image/instant mode used to have a dedicated branch here
        # ("force_immediate_confirmation and hand_near_mouth" -> always
        # OBJECT_TO_MOUTH) that fired before hand_holding_obj was even
        # checked -- meaning HAND_TO_MOUTH could never be reported in that
        # mode no matter what, regardless of whether an object was actually
        # detected near the hand. _resolve_confirmed_status() already skips
        # the multi-frame/time confirmation delay whenever
        # _force_immediate_confirmation or _single_image_mode is set, so
        # removing that branch doesn't lose the "instant" behavior -- it just
        # lets HAND_TO_MOUTH vs OBJECT_TO_MOUTH be decided by hand_holding_obj
        # like every other mode, instead of always escalating.
        elif not hand_near_mouth:
            self.danger_start_time = None
            self._danger_state_since = None
            danger_duration = 0.0
            self._confirmation_counter = 0
            self._confirmed_status = "SAFE"
            status = "SAFE"
        elif hand_near_mouth and not hand_holding_obj:
            candidate_status = "HAND_TO_MOUTH"
            if self.danger_start_time is None:
                self.danger_start_time = current_time
            danger_duration = current_time - self.danger_start_time
            status = self._resolve_confirmed_status(candidate_status)
        else:  # hand_near_mouth and hand_holding_obj
            candidate_status = "OBJECT_TO_MOUTH"
            if self.danger_start_time is None:
                self.danger_start_time = current_time
            danger_duration = current_time - self.danger_start_time
            status = self._resolve_confirmed_status(candidate_status, confirmation_override)

        effective_sustained_duration = (
            self.hazard_sustained_danger_duration if hazard_confident else self.sustained_danger_duration
        )
        if self._force_immediate_confirmation:
            if status != "SAFE":
                self._danger_state_since = current_time
            else:
                self._danger_state_since = None
        elif status != "SAFE":
            if self._danger_state_since is None:
                self._danger_state_since = current_time
            if current_time - self._danger_state_since < effective_sustained_duration:
                status = "SAFE"
                danger_duration = 0.0
        else:
            self._danger_state_since = None
        
        # ====== SAVE DANGER CLIP ======
        danger_clip_path = None
        current_clip_time = time.time()
        if self.save_danger_clips and status != "SAFE":
            if current_clip_time - self.last_danger_clip_time > self.danger_clip_cooldown:
                try:
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    clip_filename = f"{status}_{timestamp}.jpg"
                    danger_clip_path = os.path.join(self.danger_clips_dir, clip_filename)
                    cv2.imwrite(danger_clip_path, frame)
                    self.logger.log_info(f"💾 Saved danger clip: {danger_clip_path}")
                    self.last_danger_clip_time = current_clip_time
                except Exception as e:
                    self.logger.log_error(f"Failed to save danger clip: {e}")

        # ====== SAVE DANGER VIDEO ======
        # Complements the single-JPG snapshot above with an actual short video,
        # including a few seconds of lead-up via the rolling buffer -- see
        # logging.save_danger_videos in config.yaml.
        self._update_danger_video(frame, status, current_time)

        # ====== TRIGGER ALERTS ======
        hazard_notes = f"hazard_match={hazard_match[0]} (severity={hazard_match[1]}, sim={hazard_match[2]:.2f})" if hazard_match is not None else ""
        danger_threshold = self.config.get("alerts.danger_duration_threshold", 3.0)
        if self._should_trigger_alert(danger_duration, danger_threshold):
            alert_status = status if status != "SAFE" else candidate_status
            self.alert_manager.trigger_alert(
                alert_status,
                danger_duration,
                image_path=danger_clip_path,
                hazard_name=hazard_match[0] if hazard_match is not None else None
            )

        # ====== LOG EVENTS ======
        current_log_time = time.time()
        if current_log_time - self.last_event_log_time > self.event_log_cooldown:
            if status != "SAFE":
                self.logger.log_event(
                    status=status,
                    duration=danger_duration,
                    hand_mouth_distance=d_hand_mouth,
                    hand_object_distance=d_hand_obj,
                    frame_saved=danger_clip_path is not None,
                    source=self.current_source,
                    device=self.device_name,
                    platform=self.platform,
                    notes=hazard_notes
                )
            self.last_event_log_time = current_log_time
        
        # ====== DRAW COMPOSED DISPLAY ======
        info_dict = {
            'shoulder_width': shoulder_width,
            'h_m_dist': d_hand_mouth,
            'h_m_thresh': hand_mouth_thresh,
            'h_o_dist': d_hand_obj,
            'h_o_thresh': hand_obj_thresh,
            'duration': danger_duration,
            'status': status,
            'status_color': utils.get_status_color(status),
            'hazard_name': hazard_match[0] if hazard_match is not None else None,
            'hazard_confident': hazard_confident,
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

        frame = self._prepare_display_frame(frame)
        
        # Update statistics
        is_danger = hand_near_mouth and hand_holding_obj
        self.detection_stats.update(
            detected_pose=bool(pose_results.keypoints),
            objects_count=len(detected_objects),
            is_danger=status != "SAFE"
        )
        
        return frame, {
            'status': status,
            'duration': danger_duration,
            'skeleton_button': skeleton_button,
            'shoulder_width': shoulder_width,
            'hand_mouth_distance': d_hand_mouth,
            'hand_object_distance': d_hand_obj,
            'h_m_dist': d_hand_mouth,
            'h_m_thresh': hand_mouth_thresh,
            'h_o_dist': d_hand_obj,
            'h_o_thresh': hand_obj_thresh,
            'hand_near_mouth': hand_near_mouth,
            'hand_holding_obj': hand_holding_obj,
            'hazard_name': hazard_match[0] if hazard_match is not None else None,
            'hazard_severity': hazard_match[1] if hazard_match is not None else None,
            'hazard_confident': hazard_confident,
            'hazard_box': hazard_match_box,
            'hazard_debug': self._last_hazard_debug,  # (name, similarity, box) of the best attempt this frame, pass or fail
            'pose_detected': pose_results.keypoints is not None and len(pose_results.keypoints.xy) > 0,
            'num_objects': len(obj_results.boxes) if obj_results.boxes is not None else 0,
            **perf_metrics
        }
    
    def _prepare_display_frame(self, frame: np.ndarray) -> np.ndarray:
        """Enhance and resize the displayed frame for clearer visualization."""
        if frame is None:
            return frame

        if self.display_enhance_contrast:
            try:
                lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
                l, a, b = cv2.split(lab)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                l = clahe.apply(l)
                lab = cv2.merge((l, a, b))
                frame = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
            except Exception:
                pass

        if self.display_sharpen:
            try:
                blurred = cv2.GaussianBlur(frame, (0, 0), 1.2)
                frame = cv2.addWeighted(frame, 1.5, blurred, -0.5, 0)
            except Exception:
                pass

        if self.display_width and self.display_height:
            frame_h, frame_w = frame.shape[:2]
            target_w = max(320, int(self.display_width))
            target_h = max(320, int(self.display_height))
            if frame_w != target_w or frame_h != target_h:
                frame = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_CUBIC)

        return frame

    def _should_trigger_alert(self, duration: float, threshold: float) -> bool:
        """Trigger alerts when the danger duration reaches the configured threshold."""
        return float(duration) >= float(threshold)

    def _update_danger_video(self, frame: np.ndarray, status: str, current_time: float) -> None:
        """Maintain the rolling pre-event frame buffer and drive an active
        VideoWriter across a HAND_TO_MOUTH/OBJECT_TO_MOUTH episode.

        Unlike the single-JPG "danger clip" saved just above this call, this
        produces an actual short video -- including `danger_video_pre_seconds`
        of lead-up (from the rolling buffer, so the moment that triggered the
        alert is visible, not just what came after) and
        `danger_video_post_seconds` of trailing footage once the danger signal
        clears, so the clip also shows the child safe again at the end.
        """
        if not self.save_danger_videos:
            return

        # Always maintain the rolling buffer, regardless of current status --
        # this is what lets a freshly-started recording include the seconds
        # BEFORE the danger was confirmed, not just from that instant onward.
        self._video_frame_buffer.append((current_time, frame.copy()))
        while (self._video_frame_buffer
               and current_time - self._video_frame_buffer[0][0] > self.danger_video_pre_seconds):
            self._video_frame_buffer.popleft()

        if status != "SAFE":
            self._video_last_danger_at = current_time
            if self._video_writer is None:
                self._start_danger_video(status, frame.shape[1], frame.shape[0])
            elif current_time - self._video_recording_started_at > self.danger_video_max_seconds:
                # Danger has persisted past the single-clip cap -- close this
                # segment out and immediately start a fresh one rather than
                # growing one unbounded file.
                self._finalize_danger_video()
                self._start_danger_video(status, frame.shape[1], frame.shape[0])
            if self._video_writer is not None:
                self._video_writer.write(frame)
            return

        # status == SAFE: if a recording is in progress, keep it rolling
        # through the post-event grace window (captures the tail showing the
        # danger has ended), then finalize once that window has elapsed.
        if self._video_writer is not None:
            if current_time - self._video_last_danger_at <= self.danger_video_post_seconds:
                self._video_writer.write(frame)
            else:
                self._finalize_danger_video()

    def _start_danger_video(self, status: str, width: int, height: int) -> None:
        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"{status}_{timestamp}.mp4"
            path = os.path.join(self.danger_videos_dir, filename)
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            writer = cv2.VideoWriter(path, fourcc, self.danger_video_fps, (width, height))
            if not writer.isOpened():
                self.logger.log_error(f"Failed to open danger video writer for {path}")
                return
            # Flush the buffered pre-event frames first, oldest to newest, so
            # the saved clip's lead-up matches what actually happened.
            for _, buffered_frame in self._video_frame_buffer:
                writer.write(buffered_frame)
            self._video_writer = writer
            self._video_writer_path = path
            self._video_recording_started_at = time.time()
            self._video_status_label = status
            self.logger.log_info(f"🎥 Started danger video: {path}")
        except Exception as e:
            self.logger.log_error(f"Failed to start danger video: {e}")

    def _finalize_danger_video(self) -> None:
        if self._video_writer is None:
            return
        try:
            self._video_writer.release()
            self.logger.log_info(f"💾 Saved danger video: {self._video_writer_path}")
        except Exception as e:
            self.logger.log_error(f"Failed to finalize danger video: {e}")
        finally:
            self._video_writer = None
            self._video_writer_path = None
            self._video_recording_started_at = None

    def _get_object_proximity_threshold(self, shoulder_width: float) -> float:
        """Return the object-scanning threshold ("vật gần tay", α_ho) as
        object_hand_hold_multiplier x shoulder width, with a floor."""
        multiplier = getattr(self, 'object_hand_hold_multiplier', 0.3)
        if shoulder_width is None:
            return max(20.0, self.hand_obj_thresh)
        return max(20.0, float(shoulder_width) * multiplier)

    def _is_object_near_mouth(self, box: Tuple[float, float, float, float], mouth_reference: np.ndarray,
                              threshold: float) -> bool:
        """Treat an object as mouth-relevant when it is physically near the mouth or when single-image confirmation is active."""
        self.object_near_mouth_min_distance = getattr(self, 'object_near_mouth_min_distance', 18)
        self.object_size_limit_multiplier = getattr(self, 'object_size_limit_multiplier', 0.35)

        x1, y1, x2, y2 = box
        if x2 <= x1 or y2 <= y1:
            return False

        # Reject oversized boxes FIRST, before any distance check -- a large
        # box (e.g. a person/animal the object detector misclassified as
        # toy/blanket) is very likely to have an edge close to the mouth
        # simply because it's large, which would otherwise let it slip past
        # every distance-based branch below undetected as "near enough".
        # A handheld object near a mouth is small; this filter must apply
        # regardless of how close it measures.
        box_area = (x2 - x1) * (y2 - y1)
        size_limit = max(3000.0, threshold * threshold * self.object_size_limit_multiplier)
        if box_area > size_limit:
            return False

        closest_point = np.array([
            np.clip(mouth_reference[0], x1, x2),
            np.clip(mouth_reference[1], y1, y2)
        ])
        mouth_distance = float(np.linalg.norm(mouth_reference - closest_point))

        if mouth_distance <= max(self.object_near_mouth_min_distance, threshold * 0.8):
            return True

        if getattr(self, '_force_immediate_confirmation', False) and mouth_distance <= max(220.0, threshold * 0.8):
            return True

        return mouth_distance <= max(120.0, threshold * 1.4)

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

    def _has_near_mouth_object_context(self, boxes: List[Tuple[float, float, float, float]],
                                       mouth_reference: np.ndarray, threshold: float) -> bool:
        """Return True when any detected object is clearly near the mouth region."""
        if not boxes:
            return False
        return any(self._is_object_near_mouth(box, mouth_reference, threshold) for box in boxes)

    def _should_trigger_proximity_only_signal(self, object_mouth_distance: float, hand_near_mouth: bool,
                                              hand_object_distance: float, threshold: float) -> bool:
        """Allow a very close object-to-mouth match to trigger even without sustained hand proximity.

        In continuous video this hand-independent fast-path is safe: a single
        frame's result still has to survive confirmation_frames/
        sustained_danger_duration in _resolve_confirmed_status() before it is
        actually reported, so one noisy "object touching mouth" reading (a
        slightly-off mouth-point estimate, a stray detector box) gets
        filtered out by requiring it to repeat. Single-image/instant mode
        (_force_immediate_confirmation) skips that outer confirmation
        entirely, so this fast-path must not fire on object-to-mouth distance
        alone there -- require at least a plausible hand signal too, with a
        tighter distance, instead of trusting one frame's raw detection.
        """
        if getattr(self, '_force_immediate_confirmation', False):
            if not (hand_near_mouth or hand_object_distance <= max(60.0, threshold * 0.85)):
                return False
            return object_mouth_distance <= max(60.0, threshold * 0.85)

        if object_mouth_distance <= max(80.0, threshold * 1.1):
            return True
        return (
            hand_near_mouth
            and object_mouth_distance <= max(220.0, threshold * 2.0)
            and hand_object_distance <= max(120.0, threshold * 1.6)
        )

    def _filter_objects_for_person(self, boxes: List[Tuple[float, float, float, float]], mouth_reference: np.ndarray,
                                   wrists: List[np.ndarray], shoulders: List[np.ndarray],
                                   reference_distance: float) -> List[Tuple[float, float, float, float]]:
        """Keep only objects in the upper-body chest-to-mouth region to reduce false positives."""
        self.object_region_multiplier = getattr(self, 'object_region_multiplier', 1.2)

        if not boxes:
            return []

        region_radius = max(reference_distance, 40.0) * max(0.7, self.object_region_multiplier * 0.8)
        filtered = []
        if getattr(self, '_force_immediate_confirmation', False):
            if boxes:
                candidate_boxes = []
                for box in boxes:
                    x1, y1, x2, y2 = box
                    center = np.array([(x1 + x2) / 2.0, (y1 + y2) / 2.0])
                    distance_to_mouth = float(np.linalg.norm(center - mouth_reference))
                    if distance_to_mouth <= max(220.0, reference_distance * 1.6):
                        candidate_boxes.append(box)
                if candidate_boxes:
                    return candidate_boxes
            return []

        for box in boxes:
            if not self._is_object_near_mouth(box, mouth_reference, reference_distance):
                continue

            x1, y1, x2, y2 = box
            center = np.array([(x1 + x2) / 2.0, (y1 + y2) / 2.0])
            closest_point = self._get_box_point_nearest_reference(box, mouth_reference)
            distance_to_mouth = float(np.linalg.norm(closest_point - mouth_reference))

            if distance_to_mouth <= max(120.0, reference_distance * 1.3):
                filtered.append(box)
                continue

            if shoulders and len(shoulders) >= 2:
                left_shoulder, right_shoulder = shoulders[0], shoulders[1]
                shoulder_mid = (left_shoulder + right_shoulder) / 2.0
                chest_y = shoulder_mid[1]
                mouth_y = mouth_reference[1]
                region_top = min(chest_y, mouth_y) - region_radius * 0.6
                region_bottom = max(chest_y, mouth_y) + region_radius * 0.6
                region_left = min(left_shoulder[0], mouth_reference[0], shoulder_mid[0]) - region_radius * 1.1
                region_right = max(right_shoulder[0], mouth_reference[0], shoulder_mid[0]) + region_radius * 1.1

                in_region = (
                    region_left <= center[0] <= region_right and
                    region_top <= center[1] <= region_bottom
                )
                if not in_region and distance_to_mouth <= region_radius * 1.4:
                    in_region = True
            else:
                in_region = False

            if not in_region and wrists:
                wrist_distances = [np.linalg.norm(center - wrist) for wrist in wrists]
                in_region = distance_to_mouth <= region_radius * 0.9 or min(wrist_distances) <= region_radius * 0.7

            if in_region:
                filtered.append(box)
        return filtered

    def _match_hazard(self, frame: np.ndarray, box: Tuple[float, float, float, float]) -> Optional[Tuple[str, str, float, bool]]:
        """Check a candidate object box against the hazard gallery, at two
        confidence tiers:

        - similarity >= hazard_match_threshold (default 0.75): CONFIDENT --
          fast-tracked confirmation (see hazard_confirmation_frames /
          hazard_sustained_danger_duration in process_frame).
        - hazard_possible_match_threshold (default 0.5) <= similarity < 0.75:
          POSSIBLE -- still counts as an object-to-mouth signal and is shown
          on screen, but keeps the normal (non-fast-tracked) confirmation
          timing, since the visual evidence is weaker.

        Returns (name, severity, similarity, confident) or None below both
        thresholds. Never raises -- embedding/matching failures are treated
        as "no match" so a gallery problem can't block the normal detection
        path.

        Also records the best attempt regardless of threshold into
        self._last_hazard_debug (name, similarity, box), even on failure --
        surfaced via info_dict['hazard_debug'] so a near-miss is visible to
        callers (see debug_hazard_live.py) instead of only pass/fail.
        """
        if not self.hazard_gallery.enabled:
            return None
        x1, y1, x2, y2 = [int(v) for v in box]
        x1, y1 = max(0, x1), max(0, y1)
        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            return None
        try:
            embedding = extract_embedding(crop)
        except Exception:
            return None

        best = self.hazard_gallery.best_match(embedding)
        if best is None:
            return None
        best_entry, best_sim = best
        self._last_hazard_debug = (best_entry['name'], best_sim, box)

        if best_sim >= self.hazard_match_threshold:
            return best_entry['name'], best_entry['severity'], best_sim, True
        if best_sim >= self.hazard_possible_match_threshold:
            return best_entry['name'], best_entry['severity'], best_sim, False
        return None

    def _draw_hazard_overlay(self, frame: np.ndarray, box: Tuple[float, float, float, float],
                             match: Tuple[str, str, float, bool]) -> None:
        """Draw a highlighted box + label over a box that matched the hazard gallery.
        Confident matches get a solid box; possible (lower-confidence) matches
        get a thinner box and a '?' in the label, to visually distinguish them."""
        x1, y1, x2, y2 = [int(v) for v in box]
        name, severity, similarity, confident = match
        color = (0, 0, 255) if severity == 'critical' else (0, 128, 255)
        thickness = 3 if confident else 1
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
        label = f"HAZARD: {name} ({similarity:.2f})" if confident else f"HAZARD? {name} ({similarity:.2f})"
        cv2.putText(
            frame, label,
            (x1, max(20, y1 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2 if confident else 1
        )

    def _get_box_point_nearest_reference(self, box: Tuple[float, float, float, float], reference_point: np.ndarray) -> np.ndarray:
        """Return the point on a box that is closest to a given reference point."""
        x1, y1, x2, y2 = box
        closest_x = min(max(reference_point[0], x1), x2)
        closest_y = min(max(reference_point[1], y1), y2)
        return np.array([closest_x, closest_y], dtype=np.float32)

    def _get_nearest_object_reference(self, boxes: List[Tuple[float, float, float, float]], reference_point: np.ndarray) -> Tuple[float, np.ndarray]:
        """Return the closest object-reference distance and the corresponding point on the object box."""
        nearest_distance = 999.0
        nearest_point = np.array([0.0, 0.0], dtype=np.float32)

        for box in boxes:
            object_point = self._get_box_point_nearest_reference(box, reference_point)
            dist = utils.distance(reference_point, object_point)
            if dist < nearest_distance:
                nearest_distance = dist
                nearest_point = object_point

        return nearest_distance, nearest_point

    def _evaluate_fallback_fixed_threshold(self, object_mouth_distance: float, hand_mouth_distance: float,
                                           hand_object_distance: float, hand_near_mouth: bool) -> bool:
        """Fallback fixed-threshold logic: warn when the object is near the mouth and the hand/object context is within warning range."""
        self.enable_fallback_fixed_threshold = getattr(self, 'enable_fallback_fixed_threshold', True)
        if not self.enable_fallback_fixed_threshold:
            return False

        hand_context = hand_near_mouth or hand_object_distance <= self.fallback_hand_object_thresh
        immediate_single_image = getattr(self, '_force_immediate_confirmation', False)
        return (
            (hand_context or immediate_single_image) and
            object_mouth_distance <= self.fallback_object_mouth_thresh and
            (hand_object_distance <= self.fallback_hand_object_thresh or immediate_single_image)
        )

    def _evaluate_object_to_mouth_signal(self, object_mouth_distance: float, hand_mouth_distance: float,
                                         hand_near_mouth: bool, hand_object_distance: float,
                                         threshold: float) -> bool:
        """Use a conservative dynamic threshold and require repeated evidence before triggering."""
        self.object_mouth_multiplier = getattr(self, 'object_mouth_multiplier', 0.6)
        self.object_mouth_history = getattr(self, 'object_mouth_history', [])
        self.object_mouth_history_window = getattr(self, 'object_mouth_history_window', 3)
        self.dynamic_threshold = getattr(self, 'dynamic_threshold', True)

        hand_context = hand_near_mouth or hand_object_distance <= max(20.0, threshold * 0.55)
        immediate_single_image = getattr(self, '_force_immediate_confirmation', False)
        if not hand_context and not immediate_single_image:
            return False

        body_scale = max(threshold, 1.0)
        object_threshold = body_scale * self.object_mouth_multiplier * 0.75
        hand_threshold = body_scale * 0.6
        object_hand_threshold = body_scale * 0.55

        object_close = object_mouth_distance <= object_threshold
        hand_close = hand_mouth_distance <= hand_threshold
        object_in_hand = hand_object_distance <= object_hand_threshold

        signal = object_close and object_in_hand
        if immediate_single_image:
            # Single-image mode has no confirmation_frames/sustained_danger_duration
            # gate to absorb a noisy one-off reading (see
            # _should_trigger_proximity_only_signal's docstring for the same
            # reasoning) -- so unlike continuous video, "some object happens
            # to be near the mouth" must NOT fire on its own here. Every
            # branch below requires hand_near_mouth as corroboration.
            return (
                signal
                or (hand_near_mouth and object_close)
                or (hand_near_mouth and object_mouth_distance <= max(80.0, threshold * 1.1))
                or (hand_near_mouth and hand_object_distance <= max(80.0, threshold * 1.1))
            )

        self.object_mouth_history.append(signal)
        if len(self.object_mouth_history) > self.object_mouth_history_window:
            self.object_mouth_history.pop(0)

        if len(self.object_mouth_history) < self.object_mouth_history_window:
            return False

        return sum(self.object_mouth_history) >= max(2, int(self.object_mouth_history_window * 0.7))

    def _resolve_confirmed_status(self, candidate_status: str, confirmation_frames_override: Optional[int] = None) -> str:
        """Require the same danger signal to persist across several frames before reporting it, unless running a single-image inference.

        Args:
            confirmation_frames_override: When set (e.g. the candidate object matched
                the hazard gallery), use this instead of self.confirmation_frames --
                a known-dangerous object needs fewer repeated frames to confirm.
        """
        if self._force_immediate_confirmation or self._single_image_mode:
            self._confirmation_counter = 0
            self._confirmed_status = candidate_status
            return candidate_status

        if candidate_status == self._confirmed_status:
            self._confirmation_counter += 1
        else:
            self._confirmation_counter = 1
            self._confirmed_status = candidate_status

        required_frames = confirmation_frames_override if confirmation_frames_override is not None else self.confirmation_frames
        if self._confirmation_counter >= required_frames:
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

        # Setup output video writer if requested. NOTE: cv2.VideoWriter.write()
        # silently fails ("Failed to write frame") on every call whose frame
        # size doesn't exactly match the size given to VideoWriter() -- this
        # used to be (self.img_size, self.img_size) (the model's square
        # inference resolution, e.g. 640x640), but process_frame()'s actual
        # output is resized to (display.frame_width, display.frame_height)
        # (960x960 by default) in _apply_display_effects(). That mismatch
        # produced a near-empty output file regardless of the source video's
        # own resolution. Determine the writer size from the first processed
        # frame's real shape instead of assuming any particular config value,
        # so this stays correct even if the display-resize logic changes.
        out = None
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')

        self.current_source = video_path
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

                if output_path and out is None:
                    out_h, out_w = output_frame.shape[:2]
                    out = cv2.VideoWriter(output_path, fourcc, fps, (out_w, out_h))
                    if not out.isOpened():
                        self.logger.log_error(f"Failed to open output video writer for {output_path}")
                        out = None
                if out:
                    out.write(output_frame)

                # Press 'q' to exit
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        
        finally:
            cap.release()
            if out:
                out.release()
            self._finalize_danger_video()
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

        # See process_video()'s comment on the same pattern: the writer size
        # must match process_frame()'s actual output shape, not img_size.
        out = None
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')

        self.current_source = f"camera:{camera_index}"
        self.logger.log_info(f"Processing camera: {camera_index}")
        cv2.namedWindow("BabyWatcher", cv2.WINDOW_NORMAL)
        cv2.setMouseCallback("BabyWatcher", self._handle_mouse_toggle)
        
        consecutive_failures = 0
        # Windows/MSMF cameras commonly fail the first few grabFrame() calls
        # right after opening (warm-up delay) -- treat a handful of failed
        # reads as transient and retry, instead of exiting on the very first one.
        max_consecutive_failures = 30
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    consecutive_failures += 1
                    if consecutive_failures >= max_consecutive_failures:
                        self.logger.log_error(
                            f"Camera {camera_index} không trả về frame sau {max_consecutive_failures} lần thử."
                        )
                        break
                    continue
                consecutive_failures = 0

                output_frame, info = self.process_frame(frame)
                self._last_click_button = info.get('skeleton_button')

                cv2.imshow("BabyWatcher", output_frame)

                if output_path and out is None:
                    out_h, out_w = output_frame.shape[:2]
                    out = cv2.VideoWriter(output_path, fourcc, fps, (out_w, out_h))
                    if not out.isOpened():
                        self.logger.log_error(f"Failed to open output video writer for {output_path}")
                        out = None
                if out:
                    out.write(output_frame)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        finally:
            cap.release()
            if out:
                out.release()
            self._finalize_danger_video()
            cv2.destroyAllWindows()
            self.logger.log_info("✅ Camera processing completed")
    
    def process_image(self, image_path: str, output_path: Optional[str] = None, show_window: bool = False):
        """
        Process a single image -- a quick-look DEBUG tool, not an accuracy benchmark.

        This sets _force_immediate_confirmation=True, which skips the
        confirmation_frames / sustained_danger_duration gates that
        process_video()/process_camera() rely on to turn a single noisy
        reading into a confirmed alert. Those gates are the system's main
        defense against false positives, and BabyWatcher's real use case is
        continuous camera monitoring, not one-off photos -- so a single
        process_image() call is structurally more trigger-happy than the
        real product and should NOT be used to measure system accuracy
        (confirmed empirically: ~55-60% accuracy on the same 121-image
        ground-truth set vs. 72.7% for the continuous-video-equivalent
        evaluation methodology in compare_fixed_thresholds.py). Use this to
        eyeball what the system thinks of one photo while debugging; use
        compare_fixed_thresholds.py / a real video for anything you intend to
        report as a performance number.

        Args:
            image_path: Path to input image
            output_path: Optional path to save output image
            show_window: Whether to display the processed image in a GUI window
        """
        frame = cv2.imread(image_path)
        
        if frame is None:
            self.logger.log_error(f"Cannot read image: {image_path}")
            return
        
        self.current_source = image_path
        self._force_immediate_confirmation = True
        self._single_image_mode = True
        output_frame, info = self.process_frame(frame)
        self._last_click_button = info.get('skeleton_button')
        self._force_immediate_confirmation = False
        self._single_image_mode = False

        if output_path:
            cv2.imwrite(output_path, output_frame)
            self.logger.log_info(f"Output saved: {output_path}")

        if show_window:
            cv2.namedWindow("BabyWatcher", cv2.WINDOW_NORMAL)
            cv2.setMouseCallback("BabyWatcher", self._handle_mouse_toggle)
            cv2.imshow("BabyWatcher", output_frame)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        else:
            self.logger.log_info(f"✅ Image processing completed: {image_path}")
    
    def process_file(self, file_path: str, output_path: Optional[str] = None, show_window: bool = False):
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
            self.process_image(file_path, output_path, show_window=show_window)
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
