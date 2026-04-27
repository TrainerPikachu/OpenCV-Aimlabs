import pytest
import numpy as np
from src.capture.screen import FastScreenCapture

def test_screen_capture_init():
    capture = FastScreenCapture(width=800, height=600)
    assert capture.w == 800
    assert capture.h == 600
    assert capture.screen_w > 0
    assert capture.screen_h > 0

def test_screen_capture_grab():
    capture = FastScreenCapture(width=100, height=100)
    frame = capture.grab()
    
    assert isinstance(frame, np.ndarray)
    # Shape should be (height, width, 3) for BGR
    assert frame.shape == (100, 100, 3)
    # Check if memory is contiguous
    assert frame.flags['C_CONTIGUOUS']
