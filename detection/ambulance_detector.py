"""Ambulance / fire-truck detector using a custom-trained YOLO model.

Runs on a separate thread budget — only invoked every Nth frame per lane to
keep CPU usage manageable when paired with the main vehicle detector.
"""
from typing import Optional

import numpy as np
from ultralytics import YOLO

from .config import AMBULANCE_CLASSES, det_config


class AmbulanceDetector:
    """Wraps the custom ambulance YOLO model. Lazy-loaded — instantiating is cheap;
    inference loads the model into RAM (~50MB)."""

    def __init__(self, model_path: Optional[str] = None):
        path = model_path or det_config.ambulance_model_path
        print(f"⏳ Loading ambulance YOLO model: {path}")
        self.model = YOLO(path)
        self.model.fuse()
        self._names = self.model.names
        print(f"✓ Ambulance model loaded ({len(self._names)} classes)")

    def detect(self, frame: np.ndarray, conf: float = 0.4) -> bool:
        """Return True if any class in AMBULANCE_CLASSES is detected in the frame."""
        results = self.model(frame, conf=conf, verbose=False)
        r = results[0]
        if r.boxes is None or len(r.boxes) == 0:
            return False
        for cls_id in r.boxes.cls.cpu().numpy():
            cname = self._names[int(cls_id)]
            if cname in AMBULANCE_CLASSES:
                return True
        return False


# Lazy singleton — built on first use to avoid loading the model when in demo mode
_instance: Optional[AmbulanceDetector] = None


def get_ambulance_detector() -> AmbulanceDetector:
    global _instance
    if _instance is None:
        _instance = AmbulanceDetector()
    return _instance
