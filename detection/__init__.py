"""Video-based vehicle detection module (YOLOv11 + threaded feeds).

Exposes a single ``feed_manager`` instance that mirrors the public API of
``simulation.demo_sim`` (step, set_green_times, set_phase, get_snapshot,
inject_emergency, start, stop). Switch via ``DETECTION_MODE=video`` in .env.
"""
from .config import det_config, ROAD_POLYGONS, VEHICLE_CLASSES, AMBULANCE_CLASSES
from .vehicle_detector import VehicleDetector, vehicle_detector
from .ambulance_detector import AmbulanceDetector, get_ambulance_detector
from .feed_manager import FeedManager
from .violation_detector import ViolationDetector, violation_detector

# Singleton — created lazily so importing this module doesn't spin up threads
feed_manager = FeedManager()


def enable_ambulance_detection(emergency_handler=None) -> None:
    """Load the ambulance model and wire it into ``feed_manager``.

    Call this once at startup *only when* video detection is enabled —
    loading the second YOLO model adds ~50MB RAM and ~150ms/frame CPU.
    """
    feed_manager.ambulance_detector = get_ambulance_detector()
    if emergency_handler is not None:
        feed_manager.emergency_handler = emergency_handler


__all__ = [
    "det_config",
    "ROAD_POLYGONS",
    "VEHICLE_CLASSES",
    "AMBULANCE_CLASSES",
    "VehicleDetector",
    "vehicle_detector",
    "AmbulanceDetector",
    "get_ambulance_detector",
    "FeedManager",
    "feed_manager",
    "enable_ambulance_detection",
    "ViolationDetector",
    "violation_detector",
]
