"""BabyWatcher - Main detection engine"""

import cv2
import numpy as np
import time
import os
from typing import Tuple, Optional, Dict, List
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
        
        # Extract configuration values
        self.img_size = self.config.get("detection.img_size", 640)
        self.conf_thresh = self.config.get("detection.conf_thresh", 0.4)
        self.hand_mouth_thresh = self.config.get("detection.hand_mouth_thresh", 45)
        self.hand_obj_thresh = self.config.get("detection.hand_obj_thresh", 60)
        self.dynamic_threshold = self.config.get("detection.dynamic_threshold", True)
        
        # Load models
        pose_model_path = self.config.get("models.pose_model_path", "yolo26n-pose.pt")
        obj_model_path = self.config.get("models.object_model_path", "yolo26n.pt")
        device_config = self.config.get("models.device", "auto")
        half_precision = self.config.get("models.half_precision", False)
        max_det = self.config.get("models.max_det", 300)
        
        # Auto-detect device
        if device_config.lower() == "auto":
            device = 0 if torch.cuda.is_available() else "cpu"
            device_name = "GPU (CUDA)" if torch.cuda.is_available() else "CPU"
        else:
            device = device_config
            device_name = f"GPU ({device})" if device != "cpu" else "CPU"
        
        print(f"🖥️  Using {device_name}")
        print("🔄 Loading YOLO models...")
        
        self.pose_model = YOLO(pose_model_path)
        self.pose_model.to(device)
        if half_precision and device != "cpu":
            self.pose_model.half()
        
        self.obj_model = YOLO(obj_model_path)
        self.obj_model.to(device)
        if half_precision and device != "cpu":
            self.obj_model.half()
        
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
        
        # Initialize alert manager
        alerts_config = self.config.get_dict("alerts")
        self.alert_manager = AlertManager(alerts_config)
        
        # State variables
        self.danger_start_time = None
        self.frame_count = 0
        self.start_time = time.time()
        self.last_event_log_time = 0
        self.event_log_cooldown = 1.0  # Log events max once per second
        
        # Display settings
        self.show_skeleton = self.config.get("display.show_skeleton", True)
        self.show_keypoints = self.config.get("display.show_keypoints", True)
        self.show_info_panel = self.config.get("display.show_info_panel", True)
        self.show_fps = self.config.get("display.show_fps", True)
        
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
        
        # Resize frame
        frame = cv2.resize(frame, (self.img_size, self.img_size))
        
        # Run YOLO predictions with optimized settings
        pose_results = self.pose_model.predict(
            frame, 
            imgsz=self.img_size, 
            conf=self.conf_thresh,
            max_det=self.max_det,
            verbose=False
        )[0]
        
        obj_results = self.obj_model.predict(
            frame, 
            imgsz=self.img_size, 
            conf=self.conf_thresh,
            max_det=self.max_det,
            verbose=False
        )[0]
        
        # Initialize variables
        wrists = []
        hand_near_mouth = False
        hand_holding_obj = False
        detected_objects = []
        
        d_hand_mouth = 999.0
        d_hand_obj = 999.0
        
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
                
                # Draw skeleton
                if self.show_skeleton:
                    utils.draw_skeleton(frame, person)
                
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
                    hand_mouth_thresh = shoulder_width * 0.9
                    hand_obj_thresh = shoulder_width * 0.8
                else:
                    hand_mouth_thresh = self.hand_mouth_thresh
                    hand_obj_thresh = self.hand_obj_thresh
                
                # Check hand-to-mouth distance
                for wrist in wrists:
                    d = utils.distance(wrist, nose)
                    
                    if d < d_hand_mouth:
                        d_hand_mouth = d
                    
                    # Draw distance line
                    utils.draw_distance_line(
                        frame, wrist, nose,
                        label=f"H-M: {d:.1f}",
                        color=(0, 0, 255)
                    )
                    
                    if d < hand_mouth_thresh:
                        hand_near_mouth = True
        
        # ====== OBJECT DETECTION ======
        if obj_results.boxes is not None:
            boxes = obj_results.boxes.xyxy.cpu().numpy()
            confs = obj_results.boxes.conf.cpu().numpy()
            classes = obj_results.boxes.cls.cpu().numpy()
            
            for box, conf, cls in zip(boxes, confs, classes):
                if conf < self.conf_thresh:
                    continue
                if int(cls) == 0:  # Skip person class
                    continue
                
                x1, y1, x2, y2 = box
                center = utils.box_center((x1, y1, x2, y2))
                detected_objects.append(center)
                
                # Draw object bounding box
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), 
                              (0, 255, 0), 2)
        
        # ====== HAND-OBJECT INTERACTION ======
        for wrist in wrists:
            nearest_dist, nearest_idx = utils.get_nearest_object(
                wrist, detected_objects
            )
            
            if nearest_idx >= 0:
                nearest_obj = detected_objects[nearest_idx]
                d_hand_obj = min(d_hand_obj, nearest_dist)
                
                # Draw distance line
                utils.draw_distance_line(
                    frame, wrist, nearest_obj,
                    label=f"H-O: {nearest_dist:.1f}",
                    color=(255, 255, 0)
                )
                
                if nearest_dist < hand_obj_thresh:
                    hand_holding_obj = True
        
        # ====== DETERMINE STATUS ======
        current_time = time.time()
        
        if not hand_near_mouth:
            self.danger_start_time = None
            danger_duration = 0.0
            status = "SAFE"
        elif hand_near_mouth and not hand_holding_obj:
            if self.danger_start_time is None:
                self.danger_start_time = current_time
            danger_duration = current_time - self.danger_start_time
            status = "HAND_TO_MOUTH"
        else:  # hand_near_mouth and hand_holding_obj
            if self.danger_start_time is None:
                self.danger_start_time = current_time
            danger_duration = current_time - self.danger_start_time
            status = "OBJECT_TO_MOUTH"
        
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
        
        # ====== DRAW INFO PANEL ======
        if self.show_info_panel:
            info_dict = {
                'h_m_dist': d_hand_mouth,
                'h_m_thresh': hand_mouth_thresh,
                'h_o_dist': d_hand_obj,
                'h_o_thresh': hand_obj_thresh,
                'duration': danger_duration,
                'status': status,
                'status_color': utils.get_status_color(status)
            }
            utils.draw_info_panel(frame, info_dict)
        
        # ====== DRAW WARNING BANNER ======
        utils.draw_warning_banner(frame, status)
        
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
            'hand_mouth_distance': d_hand_mouth,
            'hand_object_distance': d_hand_obj,
            'hand_near_mouth': hand_near_mouth,
            'hand_holding_obj': hand_holding_obj,
            **perf_metrics
        }
    
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
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                output_frame, info = self.process_frame(frame)
                
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
        
        if ext in [".jpg", ".jpeg", ".png", ".bmp"]:
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
    
    def print_stats(self):
        """Print processing statistics to console"""
        detection_stats = self.detection_stats.get_summary()
        print("\n" + "="*50)
        print("📊 DETECTION STATISTICS")
        print("="*50)
        for key, value in detection_stats.items():
            if isinstance(value, float):
                print(f"{key:.<40} {value:.2f}")
            else:
                print(f"{key:.<40} {value}")
        
        if self.perf_monitor:
            perf_stats = self.perf_monitor.get_summary()
            print("\n" + "="*50)
            print("⚡ PERFORMANCE METRICS")
            print("="*50)
            for key, value in perf_stats.items():
                if isinstance(value, float):
                    print(f"{key:.<40} {value:.2f}")
                else:
                    print(f"{key:.<40} {value}")
    
    def __repr__(self) -> str:
        return (f"<BabyWatcher: "
                f"Models Loaded, "
                f"Frames: {self.frame_count}, "
                f"Alerts: {self.alert_manager}>")
