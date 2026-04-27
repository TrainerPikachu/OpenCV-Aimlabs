import pytest
import numpy as np
import cv2
import os
import yaml
from src.vision.detector import TargetDetector

@pytest.fixture
def dummy_config(tmp_path):
    config_data = {
        'vision': {
            'hsv_lower': [80, 100, 100],
            'hsv_upper': [100, 255, 255],
            'min_contour_area': 50,
            'max_contour_area': 5000
        }
    }
    config_file = tmp_path / "config.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)
    return str(config_file)

def test_detector_init(dummy_config):
    detector = TargetDetector(config_path=dummy_config)
    assert np.array_equal(detector.lower_color, np.array([80, 100, 100]))
    assert detector.min_area == 50

def test_detect_empty_frame(dummy_config):
    detector = TargetDetector(config_path=dummy_config)
    empty_frame = np.array([])
    offset, is_on_target, processed = detector.detect(empty_frame)
    assert offset == (0, 0)
    assert is_on_target == False

def test_detect_target(dummy_config):
    detector = TargetDetector(config_path=dummy_config)
    
    # Create a 200x200 black image
    frame = np.zeros((200, 200, 3), dtype=np.uint8)
    
    # Center is at (100, 100)
    # Draw a cyan circle at (150, 150)
    # In BGR, Cyan is (255, 255, 0)
    cv2.circle(frame, (150, 150), 10, (255, 255, 0), -1)
    
    (dx, dy), is_on_target, processed = detector.detect(frame)
    
    # Target is at 150, center is at 100. So offset should be 50.
    # Allow some tolerance for contour center calculation
    assert 48 <= dx <= 52
    assert 48 <= dy <= 52
    # The center (100, 100) is far from the circle at (150, 150), so is_on_target should be False
    assert is_on_target == False
