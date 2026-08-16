import pytest

from src.detector import BabyWatcher


def test_single_image_prefers_object_to_mouth_with_near_mouth_object():
    watcher = BabyWatcher.__new__(BabyWatcher)
    watcher._force_immediate_confirmation = True
    watcher.object_mouth_multiplier = 0.6
    watcher.object_mouth_history = []
    watcher.object_mouth_history_window = 3
    watcher.dynamic_threshold = True
    watcher.enable_fallback_fixed_threshold = True
    watcher.fallback_hand_object_thresh = 60
    watcher.fallback_object_mouth_thresh = 60

    assert watcher._evaluate_object_to_mouth_signal(
        object_mouth_distance=22.0,
        hand_mouth_distance=18.0,
        hand_near_mouth=True,
        hand_object_distance=18.0,
        threshold=60.0,
    )


def test_single_image_does_not_trigger_without_object_context():
    watcher = BabyWatcher.__new__(BabyWatcher)
    watcher._force_immediate_confirmation = True
    watcher.object_mouth_multiplier = 0.6
    watcher.object_mouth_history = []
    watcher.object_mouth_history_window = 3
    watcher.dynamic_threshold = True
    watcher.enable_fallback_fixed_threshold = True
    watcher.fallback_hand_object_thresh = 60
    watcher.fallback_object_mouth_thresh = 60

    assert not watcher._evaluate_object_to_mouth_signal(
        object_mouth_distance=80.0,
        hand_mouth_distance=18.0,
        hand_near_mouth=True,
        hand_object_distance=80.0,
        threshold=60.0,
    )
