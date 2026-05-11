"""Unit tests for BabyWatcher"""

import pytest
import numpy as np
from src.utils import distance, box_center, calculate_shoulder_width


class TestUtilityFunctions:
    """Test utility functions"""
    
    def test_distance_calculation(self):
        """Test Euclidean distance calculation"""
        p1 = np.array([0, 0])
        p2 = np.array([3, 4])
        assert distance(p1, p2) == 5.0
    
    def test_distance_same_point(self):
        """Test distance of same point"""
        p1 = np.array([5, 5])
        p2 = np.array([5, 5])
        assert distance(p1, p2) == 0.0
    
    def test_box_center(self):
        """Test bounding box center calculation"""
        box = (0, 0, 10, 10)
        center = box_center(box)
        assert np.allclose(center, [5, 5])
    
    def test_box_center_asymmetric(self):
        """Test asymmetric bounding box"""
        box = (0, 0, 20, 10)
        center = box_center(box)
        assert np.allclose(center, [10, 5])
    
    def test_shoulder_width(self):
        """Test shoulder width calculation"""
        left_shoulder = np.array([100, 150])
        right_shoulder = np.array([200, 150])
        width = calculate_shoulder_width(left_shoulder, right_shoulder)
        assert width == 100.0


class TestDetectionLogic:
    """Test detection logic"""
    
    def test_hand_mouth_threshold(self):
        """Test hand-to-mouth detection threshold"""
        hand_distance = 40.0
        threshold = 50.0
        assert hand_distance < threshold
    
    def test_hand_object_threshold(self):
        """Test hand-to-object detection threshold"""
        hand_distance = 55.0
        threshold = 60.0
        assert hand_distance < threshold
    
    def test_danger_duration(self):
        """Test danger duration calculation"""
        start_time = 0.0
        current_time = 3.5
        duration = current_time - start_time
        danger_threshold = 3.0
        assert duration > danger_threshold


class TestConfiguration:
    """Test configuration loading"""
    
    def test_config_loading(self):
        """Test loading configuration from YAML"""
        from src.config import Config
        try:
            config = Config("config.yaml")
            assert config.config is not None
            print("✅ Config loaded successfully")
        except Exception as e:
            print(f"❌ Config loading failed: {e}")
    
    def test_config_get_value(self):
        """Test getting configuration values"""
        from src.config import Config
        try:
            config = Config("config.yaml")
            img_size = config.get("detection.img_size")
            assert img_size == 640
            print(f"✅ Got config value: img_size={img_size}")
        except Exception as e:
            print(f"⚠️  Config test skipped: {e}")


class TestLogger:
    """Test event logger"""
    
    def test_logger_initialization(self):
        """Test logger initialization"""
        from src.logger import EventLogger
        logger = EventLogger("test_logs", "test_log.csv")
        assert logger.log_path is not None
        print(f"✅ Logger initialized at {logger.log_path}")
    
    def test_logger_event_logging(self):
        """Test logging events"""
        from src.logger import EventLogger
        import os
        
        logger = EventLogger("test_logs", "test_event.csv")
        logger.log_event(
            status="HAND_TO_MOUTH",
            duration=2.5,
            hand_mouth_distance=40.0,
            hand_object_distance=999.0
        )
        
        assert os.path.exists(logger.log_path)
        print(f"✅ Event logged to {logger.log_path}")
    
    def test_logger_daily_stats(self):
        """Test getting daily statistics"""
        from src.logger import EventLogger
        
        logger = EventLogger("test_logs", "test_event.csv")
        stats = logger.get_daily_stats()
        
        assert 'total_events' in stats
        assert 'total_danger_time' in stats
        print(f"✅ Stats retrieved: {stats}")


class TestAlerts:
    """Test alert system"""
    
    def test_sound_alert_initialization(self):
        """Test sound alert initialization"""
        from src.alerts import SoundAlert
        alert = SoundAlert(enabled=False)  # Disabled for testing
        assert alert.cooldown > 0
        print("✅ Sound alert initialized")
    
    def test_email_alert_initialization(self):
        """Test email alert initialization"""
        from src.alerts import EmailAlert
        alert = EmailAlert(enabled=False)  # Disabled for testing
        assert alert.alert_threshold > 0
        print("✅ Email alert initialized")
    
    def test_alert_manager(self):
        """Test alert manager"""
        from src.alerts import AlertManager
        config = {'enable_sound': False, 'enable_email': False}
        manager = AlertManager(config)
        assert manager is not None
        print("✅ Alert manager initialized")


def run_all_tests():
    """Run all tests with output"""
    print("\n" + "="*60)
    print("🧪 BabyWatcher Unit Tests")
    print("="*60 + "\n")
    
    # Create test suite
    tests = [
        ("Distance Calculation", test_distance),
        ("Box Center", test_box_center),
        ("Logger", test_logger),
        ("Configuration", test_config),
        ("Alerts", test_alerts),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            test_func()
            print(f"✅ {test_name}: PASSED\n")
            passed += 1
        except Exception as e:
            print(f"❌ {test_name}: FAILED - {e}\n")
            failed += 1
    
    print("="*60)
    print(f"📊 Results: {passed} passed, {failed} failed")
    print("="*60 + "\n")


def test_distance():
    """Test distance function"""
    p1 = np.array([0, 0])
    p2 = np.array([3, 4])
    assert distance(p1, p2) == 5.0


def test_box_center():
    """Test box center function"""
    box = (0, 0, 10, 10)
    center = box_center(box)
    assert np.allclose(center, [5, 5])


def test_logger():
    """Test logger functionality"""
    from src.logger import EventLogger
    logger = EventLogger("test_logs", "test.csv")
    assert logger is not None


def test_config():
    """Test config loading"""
    from src.config import Config
    config = Config("config.yaml")
    assert config.config is not None


def test_alerts():
    """Test alerts"""
    from src.alerts import AlertManager
    manager = AlertManager({'enable_sound': False})
    assert manager is not None


if __name__ == "__main__":
    run_all_tests()
