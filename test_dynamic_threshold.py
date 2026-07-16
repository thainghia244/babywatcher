from src.config import Config


def test_dynamic_threshold_multiplier_defaults():
    config = Config('config.yaml')

    assert config.get('detection.hand_mouth_multiplier', 0.5) == 0.5
    assert config.get('detection.hand_object_multiplier', 0.5) == 0.5
    assert config.get('models.hand_model_path', 'yolo26n-hand.pt') == 'yolo26n-hand.pt'


if __name__ == '__main__':
    test_dynamic_threshold_multiplier_defaults()
    print('Dynamic threshold multipliers verified: 0.5')
    print('Hand model path verified: yolo26n-hand.pt')
