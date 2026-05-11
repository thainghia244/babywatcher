"""Advanced small object detection algorithms"""

import cv2
import numpy as np
from typing import List, Tuple, Dict, Optional


class SmallObjectDetector:
    """Specialized detector for small objects in hand"""
    
    def __init__(self, 
                 min_object_size: int = 10,
                 max_object_size: int = 200,
                 confidence_threshold: float = 0.15):
        """
        Initialize small object detector
        
        Args:
            min_object_size: Minimum bounding box size to consider
            max_object_size: Maximum bounding box size (or 0 for unlimited)
            confidence_threshold: Lower threshold for small objects
        """
        self.min_object_size = min_object_size
        self.max_object_size = max_object_size
        self.confidence_threshold = confidence_threshold
    
    def filter_by_size(self, 
                      boxes: np.ndarray, 
                      confs: np.ndarray,
                      classes: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Filter objects by bounding box size
        
        Args:
            boxes: Bounding boxes (N, 4)
            confs: Confidences (N,)
            classes: Class IDs (N,)
        
        Returns:
            Filtered boxes, confidences, classes
        """
        valid_indices = []
        
        for idx, box in enumerate(boxes):
            x1, y1, x2, y2 = box
            width = x2 - x1
            height = y2 - y1
            size = min(width, height)
            
            # Filter by size
            if size < self.min_object_size:
                continue
            if self.max_object_size > 0 and size > self.max_object_size:
                continue
            
            valid_indices.append(idx)
        
        valid_indices = np.array(valid_indices)
        if len(valid_indices) == 0:
            return np.empty((0, 4)), np.empty(0), np.empty(0)
        
        return boxes[valid_indices], confs[valid_indices], classes[valid_indices]
    
    def merge_nearby_detections(self,
                               boxes: np.ndarray,
                               confs: np.ndarray,
                               iou_threshold: float = 0.5) -> Tuple[np.ndarray, np.ndarray]:
        """
        Merge nearby detections (same small object detected multiple times)
        
        Args:
            boxes: Bounding boxes (N, 4)
            confs: Confidences (N,)
            iou_threshold: IoU threshold for merging
        
        Returns:
            Merged boxes, confidences
        """
        if len(boxes) == 0:
            return boxes, confs
        
        # Sort by confidence (highest first)
        sorted_idx = np.argsort(confs)[::-1]
        boxes = boxes[sorted_idx]
        confs = confs[sorted_idx]
        
        merged_boxes = []
        merged_confs = []
        used = set()
        
        for i, box_i in enumerate(boxes):
            if i in used:
                continue
            
            # Start new group
            group_boxes = [box_i]
            group_confs = [confs[i]]
            used.add(i)
            
            # Find nearby boxes
            for j, box_j in enumerate(boxes[i+1:], start=i+1):
                if j in used:
                    continue
                
                iou = self._calculate_iou(box_i, box_j)
                if iou > iou_threshold:
                    group_boxes.append(box_j)
                    group_confs.append(confs[j])
                    used.add(j)
            
            # Merge group
            merged_box = self._merge_boxes(group_boxes)
            merged_conf = max(group_confs)  # Use highest confidence
            
            merged_boxes.append(merged_box)
            merged_confs.append(merged_conf)
        
        return np.array(merged_boxes), np.array(merged_confs)
    
    @staticmethod
    def _calculate_iou(box1: np.ndarray, box2: np.ndarray) -> float:
        """Calculate IoU between two boxes"""
        x1_min, y1_min, x1_max, y1_max = box1
        x2_min, y2_min, x2_max, y2_max = box2
        
        # Intersection
        inter_min_x = max(x1_min, x2_min)
        inter_min_y = max(y1_min, y2_min)
        inter_max_x = min(x1_max, x2_max)
        inter_max_y = min(y1_max, y2_max)
        
        if inter_max_x < inter_min_x or inter_max_y < inter_min_y:
            return 0.0
        
        inter_area = (inter_max_x - inter_min_x) * (inter_max_y - inter_min_y)
        
        # Union
        box1_area = (x1_max - x1_min) * (y1_max - y1_min)
        box2_area = (x2_max - x2_min) * (y2_max - y2_min)
        union_area = box1_area + box2_area - inter_area
        
        return inter_area / union_area if union_area > 0 else 0.0
    
    @staticmethod
    def _merge_boxes(boxes: List[np.ndarray]) -> np.ndarray:
        """Merge multiple boxes into one"""
        if len(boxes) == 1:
            return boxes[0]
        
        boxes = np.array(boxes)
        return np.array([
            boxes[:, 0].min(),  # x1 min
            boxes[:, 1].min(),  # y1 min
            boxes[:, 2].max(),  # x2 max
            boxes[:, 3].max()   # y2 max
        ])
    
    def extract_hand_roi(self,
                        frame: np.ndarray,
                        wrists: List[np.ndarray],
                        expansion: float = 1.5) -> List[Tuple[np.ndarray, Tuple[int, int, int, int]]]:
        """
        Extract Region of Interest (ROI) around each wrist/hand
        
        Args:
            frame: Input frame
            wrists: List of wrist coordinates
            expansion: ROI expansion factor (1.5x means 50% larger)
        
        Returns:
            List of (ROI image, ROI coordinates)
        """
        rois = []
        h, w = frame.shape[:2]
        
        for wrist in wrists:
            if wrist is None:
                continue
            
            wx, wy = wrist.astype(int)
            
            # Define ROI size (hand radius)
            hand_size = 100  # pixels
            roi_size = int(hand_size * expansion)
            
            # Calculate ROI bounds
            x1 = max(0, wx - roi_size)
            y1 = max(0, wy - roi_size)
            x2 = min(w, wx + roi_size)
            y2 = min(h, wy + roi_size)
            
            roi = frame[y1:y2, x1:x2]
            rois.append((roi, (x1, y1, x2, y2)))
        
        return rois
    
    def detect_in_hand_roi(self,
                          yolo_model,
                          frame: np.ndarray,
                          wrists: List[np.ndarray],
                          conf_thresh: float = 0.1,
                          skip_person: bool = True) -> List[Tuple[np.ndarray, float, int]]:
        """
        Detect objects specifically in hand ROI (more sensitive)
        
        Args:
            yolo_model: YOLO object detection model
            frame: Input frame
            wrists: List of wrist coordinates
            conf_thresh: Confidence threshold for detection
            skip_person: Skip person class
        
        Returns:
            List of (box_center, confidence, class_id)
        """
        detected_objects = []
        
        # Get hand ROIs
        rois = self.extract_hand_roi(frame, wrists)
        
        for roi_img, (roi_x1, roi_y1, roi_x2, roi_y2) in rois:
            if roi_img.size == 0:
                continue
            
            # Run detection on ROI with higher sensitivity
            results = yolo_model.predict(
                roi_img,
                imgsz=416,  # Smaller size for ROI = faster
                conf=conf_thresh,
                verbose=False
            )[0]
            
            if results.boxes is None:
                continue
            
            boxes = results.boxes.xyxy.cpu().numpy()
            confs = results.boxes.conf.cpu().numpy()
            classes = results.boxes.cls.cpu().numpy()
            
            for box, conf, cls in zip(boxes, confs, classes):
                cls_id = int(cls)
                
                # Skip person
                if skip_person and cls_id == 0:
                    continue
                
                # Convert ROI coordinates back to frame coordinates
                x1, y1, x2, y2 = box
                x1 += roi_x1
                y1 += roi_y1
                x2 += roi_x1
                y2 += roi_y1
                
                center = np.array([(x1 + x2) / 2, (y1 + y2) / 2])
                detected_objects.append((center, conf, cls_id))
        
        return detected_objects


class MultiScaleDetector:
    """Multi-scale object detection for catching objects at different distances"""
    
    def __init__(self, scales: List[int] = None):
        """
        Initialize multi-scale detector
        
        Args:
            scales: List of image sizes to process (e.g., [640, 960, 1280])
        """
        self.scales = scales or [640, 960, 1280]
    
    def detect_multi_scale(self,
                          yolo_model,
                          frame: np.ndarray,
                          conf_thresh: float = 0.25) -> List[Tuple[np.ndarray, float, int]]:
        """
        Detect objects at multiple scales and merge results
        
        Args:
            yolo_model: YOLO model
            frame: Input frame
            conf_thresh: Confidence threshold
        
        Returns:
            List of merged detections with highest confidence per object
        """
        all_detections = []
        
        for scale in self.scales:
            # Resize frame
            h, w = frame.shape[:2]
            aspect = w / h
            new_w = int(scale * aspect)
            scaled_frame = cv2.resize(frame, (new_w, scale))
            
            # Run detection
            results = yolo_model.predict(
                scaled_frame,
                imgsz=scale,
                conf=conf_thresh,
                verbose=False
            )[0]
            
            if results.boxes is None:
                continue
            
            boxes = results.boxes.xyxy.cpu().numpy()
            confs = results.boxes.conf.cpu().numpy()
            classes = results.boxes.cls.cpu().numpy()
            
            # Scale boxes back to original frame size
            scale_x = w / new_w
            scale_y = h / scale
            
            for box, conf, cls in zip(boxes, confs, classes):
                if int(cls) == 0:  # Skip person
                    continue
                
                x1, y1, x2, y2 = box
                x1, x2 = x1 * scale_x, x2 * scale_x
                y1, y2 = y1 * scale_y, y2 * scale_y
                
                center = np.array([(x1 + x2) / 2, (y1 + y2) / 2])
                all_detections.append((center, conf, cls, (x1, y1, x2, y2)))
        
        # Merge nearby detections
        return self._merge_detections(all_detections)
    
    @staticmethod
    def _merge_detections(detections: List) -> List[Tuple[np.ndarray, float, int]]:
        """Merge detections from multiple scales"""
        if not detections:
            return []
        
        merged = {}
        distance_threshold = 50  # pixels
        
        for center, conf, cls, box in detections:
            key = None
            
            # Find existing cluster
            for existing_key in merged:
                existing_center, _, _ = merged[existing_key]
                dist = np.linalg.norm(center - existing_center)
                
                if dist < distance_threshold:
                    key = existing_key
                    break
            
            # Create new cluster or update
            if key is None:
                key = len(merged)
                merged[key] = (center, conf, cls)
            else:
                # Keep highest confidence
                existing_conf = merged[key][1]
                if conf > existing_conf:
                    merged[key] = (center, conf, cls)
        
        return list(merged.values())
