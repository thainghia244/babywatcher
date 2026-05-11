"""BabyWatcher - Main detection engine"""

import cv2
import numpy as np
import time
import os
import platform
import subprocess
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

        # Detect platform
        self.platform = self._detect_platform()
        print(f"🖥️  Platform detected: {self.platform}")

        # Jetson-specific setup
        if self.platform == "jetson":
            self._setup_jetson()

        # Extract configuration values
        self.img_size = self.config.get("detection.img_size", 640)
        self.conf_thresh = self.config.get("detection.conf_thresh", 0.4)
        self.hand_mouth_thresh = self.config.get("detection.hand_mouth_thresh", 45)
        self.hand_obj_thresh = self.config.get("detection.hand_obj_thresh", 60)
        self.dynamic_threshold = self.config.get("detection.dynamic_threshold", True)
        
        # Enhanced object detection for small/occluded objects
        self.small_object_conf_thresh = 0.2  # Lower threshold for small objects
        self.hand_closing_thresh = 0.5  # Hand confidence threshold
        self.inferred_object_distance_thresh = 25  # If hand-mouth < 25px, infer object

        # Load models
        pose_model_path = self.config.get("models.pose_model_path", "yolo26n-pose.pt")
        obj_model_path = self.config.get("models.object_model_path", "yolo26n.pt")
        device_config = self.config.get("models.device", "auto")
        half_precision = self.config.get("models.half_precision", False)
        max_det = self.config.get("models.max_det", 300)
        enable_tensorrt = self.config.get("hardware.enable_tensorrt", True)

        # Auto-detect device with platform consideration
        device, device_name = self._setup_device(device_config)
        print(f"🖥️  Using {device_name}")

        # Load models with optimizations
        self.pose_model, self.obj_model = self._load_models(
            pose_model_path, obj_model_path, device, half_precision,
            max_det, enable_tensorrt
        )

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
        detected_boxes = []
        object_candidate_boxes = []
        
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
                # Use lower threshold for small objects that might be in hand
                box_area = (box[2] - box[0]) * (box[3] - box[1])
                threshold = self.small_object_conf_thresh if box_area < 5000 else self.conf_thresh
                
                if conf < threshold:
                    # Collect lower-confidence near-hand candidates for inference
                    if conf >= self.small_object_conf_thresh:
                        object_candidate_boxes.append((x1, y1, x2, y2))
                    continue
                if int(cls) == 0:  # Skip person class
                    continue
                
                x1, y1, x2, y2 = box
                center = utils.box_center((x1, y1, x2, y2))
                detected_objects.append(center)
                detected_boxes.append((x1, y1, x2, y2))
                
                # Draw object bounding box
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), 
                              (0, 255, 0), 2)
        
        # ====== HAND-OBJECT INTERACTION ======
        for wrist in wrists:
            nearest_dist, nearest_idx, nearest_point = utils.get_nearest_object_box(
                wrist, detected_boxes
            )
            
            if nearest_idx >= 0:
                nearest_obj = detected_boxes[nearest_idx]
                d_hand_obj = min(d_hand_obj, nearest_dist)
                
                # Draw distance line to nearest object edge
                utils.draw_distance_line(
                    frame, wrist, nearest_point,
                    label=f"H-O: {nearest_dist:.1f}",
                    color=(255, 255, 0)
                )
                
                if nearest_dist < hand_obj_thresh:
                    hand_holding_obj = True

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
        if not hand_holding_obj and hand_near_mouth and d_hand_mouth < self.inferred_object_distance_thresh:
            hand_closing = self._detect_hand_closing(keypoints, nose, wrists)
            if hand_closing and (candidate_nearby or d_hand_mouth < self.inferred_object_distance_thresh * 0.4):
                hand_holding_obj = True
                d_hand_obj = d_hand_mouth
        
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
    
    def _load_models(self, pose_path: str, obj_path: str, device: str,
                    half_precision: bool, max_det: int, enable_tensorrt: bool):
        """Load models with platform-specific optimizations"""
        print("🔄 Loading YOLO models...")

        # Load pose model
        pose_model = YOLO(pose_path)

        # Jetson-specific optimizations
        if self.platform.startswith("jetson") and enable_tensorrt:
            try:
                # Export to TensorRT
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

        # Jetson-specific optimizations
        if self.platform.startswith("jetson") and enable_tensorrt:
            try:
                # Export to TensorRT
                obj_model.export(format='engine', device=device)
                obj_model = YOLO(obj_path.replace('.pt', '.engine'))
                print("🚀 Object model converted to TensorRT")
            except Exception as e:
                print(f"⚠️  TensorRT conversion failed for object model: {e}")

        obj_model.to(device)
        if half_precision and device != "cpu":
            obj_model.half()

        return pose_model, obj_model
    
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
