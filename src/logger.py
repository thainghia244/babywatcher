"""Event logging system for BabyWatcher"""

import csv
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import logging


class EventLogger:
    """Log dangerous events to CSV and system logs"""
    
    def __init__(self, log_dir: str = "logs", log_file: str = "events_log.csv"):
        """
        Initialize event logger
        
        Args:
            log_dir: Directory to store log files
            log_file: CSV file name for events
        """
        self.log_dir = log_dir
        self.log_file = log_file
        self.log_path = os.path.join(log_dir, log_file)
        
        # Create log directory if not exists
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        
        # Initialize CSV file with headers if not exists
        self._init_csv()
        
        # Setup system logger
        self.logger = self._setup_logger()
    
    def _init_csv(self):
        """Initialize CSV file with headers"""
        if not os.path.exists(self.log_path):
            try:
                with open(self.log_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        'timestamp',
                        'status',
                        'duration_seconds',
                        'hand_mouth_distance',
                        'hand_object_distance',
                        'frame_saved',
                        'notes'
                    ])
                print(f"✅ CSV log file created: {self.log_path}")
            except Exception as e:
                print(f"❌ Error creating CSV file: {e}")
    
    def _setup_logger(self) -> logging.Logger:
        """Setup Python logging"""
        logger = logging.getLogger('BabyWatcher')
        logger.setLevel(logging.DEBUG)
        
        # File handler
        log_file_path = os.path.join(self.log_dir, 'babywatcher.log')
        file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers
        if not logger.handlers:
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)
        
        return logger
    
    def log_event(self, 
                  status: str,
                  duration: float,
                  hand_mouth_distance: float = 0.0,
                  hand_object_distance: float = 0.0,
                  frame_saved: bool = False,
                  notes: str = ""):
        """
        Log a danger event to CSV
        
        Args:
            status: Event status (SAFE, HAND_TO_MOUTH, OBJECT_TO_MOUTH)
            duration: Duration of dangerous behavior in seconds
            hand_mouth_distance: Distance between hand and mouth
            hand_object_distance: Distance between hand and object
            frame_saved: Whether the frame was saved
            notes: Additional notes
        """
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            with open(self.log_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    timestamp,
                    status,
                    f"{duration:.2f}",
                    f"{hand_mouth_distance:.2f}",
                    f"{hand_object_distance:.2f}",
                    int(frame_saved),
                    notes
                ])
            
            # Also log to system logger
            if status != "SAFE":
                self.logger.warning(
                    f"Event: {status} | Duration: {duration:.2f}s | "
                    f"H-M: {hand_mouth_distance:.2f} | H-O: {hand_object_distance:.2f}"
                )
        
        except Exception as e:
            self.logger.error(f"Error logging event: {e}")
    
    def log_warning(self, message: str):
        """Log a warning message"""
        self.logger.warning(message)
    
    def log_error(self, message: str):
        """Log an error message"""
        self.logger.error(message)
    
    def log_info(self, message: str):
        """Log an info message"""
        self.logger.info(message)
    
    def get_daily_stats(self, date: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics for a specific day
        
        Args:
            date: Date in format 'YYYY-MM-DD' (default: today)
        
        Returns:
            Dictionary with daily statistics
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        stats = {
            'date': date,
            'total_events': 0,
            'hand_to_mouth_count': 0,
            'object_to_mouth_count': 0,
            'total_danger_time': 0.0,
            'max_danger_duration': 0.0,
            'events': []
        }
        
        try:
            with open(self.log_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Check if timestamp starts with target date
                    if row['timestamp'].startswith(date):
                        stats['total_events'] += 1
                        
                        status = row['status']
                        duration = float(row['duration_seconds'])
                        
                        if status == 'HAND_TO_MOUTH':
                            stats['hand_to_mouth_count'] += 1
                        elif status == 'OBJECT_TO_MOUTH':
                            stats['object_to_mouth_count'] += 1
                        
                        if status != 'SAFE':
                            stats['total_danger_time'] += duration
                            stats['max_danger_duration'] = max(stats['max_danger_duration'], duration)
                        
                        stats['events'].append(row)
        
        except Exception as e:
            self.logger.error(f"Error reading stats: {e}")
        
        return stats
    
    def __repr__(self) -> str:
        return f"<EventLogger at {self.log_path}>"
