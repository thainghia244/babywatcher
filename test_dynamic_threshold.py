import numpy as np

from src.config import Config
from src.detector import BabyWatcher


def test_dynamic_threshold_multiplier_defaults():
    config = Config('config.yaml')

    assert config.get('detection.hand_mouth_multiplier', 0.5) == 0.5
    assert config.get('detection.hand_object_multiplier', 0.5) == 0.5
    assert config.get('models.hand_model_path', '') == ''


def test_confirmation_state_requires_repeated_danger_frames():
    watcher = BabyWatcher.__new__(BabyWatcher)
    watcher.confirmation_frames = 3
    watcher._confirmation_counter = 0
    watcher._confirmed_status = 'SAFE'

    assert watcher._resolve_confirmed_status('HAND_TO_MOUTH') == 'SAFE'
    assert watcher._resolve_confirmed_status('HAND_TO_MOUTH') == 'SAFE'
    assert watcher._resolve_confirmed_status('HAND_TO_MOUTH') == 'HAND_TO_MOUTH'


def test_proximity_signal_uses_smoothed_history():
    watcher = BabyWatcher.__new__(BabyWatcher)
    watcher.proximity_history = []
    watcher.proximity_history_window = 3

    assert watcher._evaluate_proximity_signal(35, 40) is False
    assert watcher._evaluate_proximity_signal(35, 40) is False
    assert watcher._evaluate_proximity_signal(20, 40) is True


def test_sustained_danger_filter_applies_to_both_statuses():
    watcher = BabyWatcher.__new__(BabyWatcher)
    watcher.confirmation_frames = 3
    watcher._confirmation_counter = 0
    watcher._confirmed_status = 'SAFE'

    assert watcher._resolve_confirmed_status('HAND_TO_MOUTH') == 'SAFE'
    assert watcher._resolve_confirmed_status('HAND_TO_MOUTH') == 'SAFE'
    assert watcher._resolve_confirmed_status('HAND_TO_MOUTH') == 'HAND_TO_MOUTH'

    watcher._confirmation_counter = 0
    watcher._confirmed_status = 'SAFE'
    assert watcher._resolve_confirmed_status('OBJECT_TO_MOUTH') == 'SAFE'
    assert watcher._resolve_confirmed_status('OBJECT_TO_MOUTH') == 'SAFE'
    assert watcher._resolve_confirmed_status('OBJECT_TO_MOUTH') == 'OBJECT_TO_MOUTH'


def test_object_to_mouth_uses_dynamic_thresholds():
    watcher = BabyWatcher.__new__(BabyWatcher)
    watcher.object_mouth_multiplier = 0.6
    watcher.dynamic_threshold = True

    assert watcher._evaluate_object_to_mouth_signal(10, 20, True, 10, 60) is True
    assert watcher._evaluate_object_to_mouth_signal(50, 20, True, 10, 60) is False


def test_filter_objects_by_person_region():
    watcher = BabyWatcher.__new__(BabyWatcher)
    watcher.object_region_multiplier = 1.0

    nose = np.array([200, 180])
    wrists = [np.array([210, 210]), np.array([250, 250])]
    shoulders = [np.array([170, 220]), np.array([230, 220])]
    boxes = [
        (180, 190, 220, 210),
        (250, 250, 290, 280),
        (160, 170, 190, 190),
    ]

    filtered = watcher._filter_objects_for_person(boxes, nose, wrists, shoulders, 100)
    assert len(filtered) == 2


def test_object_proximity_threshold_uses_half_shoulder_width():
    watcher = BabyWatcher.__new__(BabyWatcher)
    watcher.hand_obj_thresh = 60

    assert watcher._get_object_proximity_threshold(100.0) == 50.0
    assert watcher._get_object_proximity_threshold(20.0) == 20.0


def test_object_to_mouth_uses_history_for_dynamic_thresholds():
    watcher = BabyWatcher.__new__(BabyWatcher)
    watcher.object_mouth_multiplier = 0.6
    watcher.dynamic_threshold = True
    watcher.object_mouth_history = []
    watcher.object_mouth_history_window = 3

    assert watcher._evaluate_object_to_mouth_signal(40, 25, True, 15, 60) is False
    assert watcher._evaluate_object_to_mouth_signal(40, 25, True, 15, 60) is True


if __name__ == '__main__':
    test_dynamic_threshold_multiplier_defaults()
    test_confirmation_state_requires_repeated_danger_frames()
    test_proximity_signal_uses_smoothed_history()
    test_sustained_danger_filter_applies_to_both_statuses()
    print('Dynamic threshold multipliers verified: 0.5')
    print('Hand model path verified: empty (disabled)')
    print('Confirmation logic verified')
    print('Proximity smoothing verified')
    print('Sustained danger filter verified')
