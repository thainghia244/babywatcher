"""Performance monitoring utilities"""

import time
import psutil
import os
from collections import deque
from typing import Dict, Optional


class PerformanceMonitor:
    """Monitor system performance metrics (FPS, memory, CPU)"""
    
    def __init__(self, window_size: int = 30):
        """
        Initialize performance monitor
        
        Args:
            window_size: Number of frames to average metrics over
        """
        self.window_size = window_size
        self.frame_times = deque(maxlen=window_size)
        self.start_time = time.time()
        self.frame_count = 0
        self.process = psutil.Process(os.getpid())
        
    def start_frame(self) -> float:
        """Mark frame start time"""
        return time.time()
    
    def end_frame(self, frame_start_time: float) -> Dict[str, float]:
        """
        Mark frame end and return metrics
        
        Args:
            frame_start_time: Frame start time from start_frame()
        
        Returns:
            Dictionary with FPS and timing info
        """
        frame_time = time.time() - frame_start_time
        self.frame_times.append(frame_time)
        self.frame_count += 1
        
        # Calculate metrics
        avg_frame_time = sum(self.frame_times) / len(self.frame_times)
        fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 0
        
        return {
            'fps': fps,
            'frame_time_ms': frame_time * 1000,
            'avg_frame_time_ms': avg_frame_time * 1000
        }
    
    def get_system_metrics(self) -> Dict[str, float]:
        """Get system resource metrics"""
        try:
            cpu_percent = self.process.cpu_percent(interval=0.1)
            memory_info = self.process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            return {
                'cpu_percent': cpu_percent,
                'memory_mb': memory_mb
            }
        except:
            return {'cpu_percent': 0, 'memory_mb': 0}
    
    def get_summary(self) -> Dict:
        """Get performance summary"""
        if not self.frame_times:
            return {}
        
        avg_frame_time = sum(self.frame_times) / len(self.frame_times)
        fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 0
        
        sys_metrics = self.get_system_metrics()
        
        return {
            'fps': fps,
            'frame_count': self.frame_count,
            'avg_frame_time_ms': avg_frame_time * 1000,
            'total_time_s': time.time() - self.start_time,
            **sys_metrics
        }


class DetectionStats:
    """Track detection statistics"""
    
    def __init__(self):
        """Initialize detection stats"""
        self.total_frames = 0
        self.detected_poses = 0
        self.detected_objects = 0
        self.danger_frames = 0
        self.safe_frames = 0
        
    def update(self, detected_pose: bool, objects_count: int, is_danger: bool):
        """Update statistics for current frame"""
        self.total_frames += 1
        if detected_pose:
            self.detected_poses += 1
        self.detected_objects += objects_count
        if is_danger:
            self.danger_frames += 1
        else:
            self.safe_frames += 1

    def increment(self, key: str, value: int = 1):
        """Increment a named counter for custom detection stats."""
        if not hasattr(self, key):
            setattr(self, key, 0)
        setattr(self, key, getattr(self, key) + value)
    
    def get_summary(self) -> Dict:
        """Get statistics summary"""
        return {
            'total_frames': self.total_frames,
            'detected_poses': self.detected_poses,
            'pose_detection_rate': (self.detected_poses / self.total_frames * 100) if self.total_frames > 0 else 0,
            'avg_objects_per_frame': self.detected_objects / self.total_frames if self.total_frames > 0 else 0,
            'danger_frames': self.danger_frames,
            'danger_rate': (self.danger_frames / self.total_frames * 100) if self.total_frames > 0 else 0,
        }
