"""Video detection configuration"""
from pydantic_settings import BaseSettings


class DetectionConfig(BaseSettings):
    """Settings for YOLO-based video vehicle detection"""

    # Source mode: "video" (real videos + YOLO) or "demo" (synthetic generator)
    detection_mode: str = "demo"

    # Models
    yolo_model_path: str = "./models/yolo11n.pt"
    ambulance_model_path: str = "./models/ambulance_detection.pt"

    # Lane → video mapping (matches cloned-repo lane order: 0=N, 1=E, 2=S, 3=W)
    video_path_n: str = "./video/video_0.mp4"
    video_path_e: str = "./video/video_1.mp4"
    video_path_s: str = "./video/video_2.mp4"
    video_path_w: str = "./video/video_3.mp4"
    video_path_violation: str = "./video/violation.mp4"

    # CPU inference tuning
    yolo_img_size: int = 480
    yolo_conf: float = 0.3
    inference_fps: int = 3
    ambulance_check_every_n_frames: int = 30

    # Display frame size (also defines polygon coordinates below)
    display_width: int = 1280
    display_height: int = 720

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


det_config = DetectionConfig()


# COCO class IDs we care about (yolo11n is COCO-pretrained)
VEHICLE_CLASSES = {
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}

# Map COCO names → optimizer's vehicle types (DemoSimulation uses car/truck/bus/motorcycle)
VEHICLE_TYPE_MAP = {
    "car": "car",
    "truck": "truck",
    "bus": "bus",
    "motorcycle": "motorcycle",
    "bicycle": "motorcycle",  # weight ~0.5, closest match
}

# ROI polygons per lane (in display_width × display_height space).
# Copied from cloned repo main.py:49-54 — focuses counts on the road area
# inside each camera frame so trees/sidewalks aren't counted.
import numpy as np

ROAD_POLYGONS = {
    "N": np.array([[100, 720], [1180, 720], [900, 300], [380, 300]], np.int32),
    "E": np.array([[60, 720], [1220, 720], [960, 240], [320, 240]], np.int32),
    "S": np.array([[40, 720], [1240, 720], [1000, 280], [280, 280]], np.int32),
    "W": np.array([[40, 720], [1240, 720], [1000, 280], [280, 280]], np.int32),
}

# Lane → video file path (resolved via config)
LANE_VIDEO_MAP = {
    "N": det_config.video_path_n,
    "E": det_config.video_path_e,
    "S": det_config.video_path_s,
    "W": det_config.video_path_w,
}

# Ambulance class names from the custom-trained model (cloned repo main.py:62-66)
AMBULANCE_CLASSES = {
    "ambulance", "ambulance_108", "ambulance_SOL",
    "fire_truck", "fireladder", "firelamp",
    "firesymbol", "firewriting",
}
