import numpy as np

from src.detector import BabyWatcher


def test_close_box_is_considered_relevant_even_if_large():
    watcher = BabyWatcher.__new__(BabyWatcher)
    watcher.object_near_mouth_min_distance = 18
    watcher.object_size_limit_multiplier = 0.35

    box = (0.0, 0.0, 5000.0, 5000.0)
    mouth_reference = np.array([100.0, 100.0], dtype=np.float32)

    assert watcher._is_object_near_mouth(box, mouth_reference, 60.0)
