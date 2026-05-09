"""YOLO-based vehicle detector with per-lane ROI counting"""
from collections import defaultdict
from typing import Dict, Optional, Tuple

import cv2
import numpy as np
from ultralytics import YOLO

from .config import (
    VEHICLE_CLASSES, VEHICLE_TYPE_MAP, ROAD_POLYGONS, det_config,
)


class VehicleDetector:
    """Single shared YOLO model. Inference is thread-safe (Ultralytics holds the GIL)."""

    def __init__(self, model_path: Optional[str] = None):
        path = model_path or det_config.yolo_model_path
        print(f"⏳ Loading YOLO model: {path}")
        self.model = YOLO(path)
        self.model.fuse()
        print("✓ YOLO model loaded")

    def detect(self, frame: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Run inference on one frame. Returns (boxes_xyxy, class_ids)."""
        results = self.model(
            frame,
            classes=list(VEHICLE_CLASSES.keys()),
            conf=det_config.yolo_conf,
            imgsz=det_config.yolo_img_size,
            verbose=False,
        )
        r = results[0]
        if r.boxes is None or len(r.boxes) == 0:
            return np.empty((0, 4)), np.empty((0,), dtype=int)
        return r.boxes.xyxy.cpu().numpy(), r.boxes.cls.cpu().numpy().astype(int)

    @staticmethod
    def count_in_roi(
        boxes: np.ndarray, class_ids: np.ndarray, lane: str
    ) -> Tuple[Dict[str, int], int]:
        """Count vehicles whose bbox bottom-center is inside the lane's ROI polygon."""
        poly = ROAD_POLYGONS[lane]
        counts: Dict[str, int] = defaultdict(int)
        total = 0
        for box, cid in zip(boxes, class_ids):
            cname = VEHICLE_CLASSES.get(int(cid))
            if cname is None:
                continue
            bx, by = int((box[0] + box[2]) / 2), int(box[3])
            if cv2.pointPolygonTest(poly, (bx, by), False) >= 0:
                bucket = VEHICLE_TYPE_MAP[cname]
                counts[bucket] += 1
                total += 1
        return dict(counts), total

    @staticmethod
    def draw_overlay(
        frame: np.ndarray,
        boxes: np.ndarray,
        class_ids: np.ndarray,
        lane: str,
        signal_state: str,
        timer: int,
        vehicle_count: int,
        ambulance: bool = False,
    ) -> np.ndarray:
        """Draw ROI polygon, bboxes, and an info panel on the frame. Returns the annotated frame."""
        poly = ROAD_POLYGONS[lane]

        if signal_state == "green":
            sig_color, alpha, label = (0, 255, 0), 0.25, "GO"
        elif signal_state == "yellow":
            sig_color, alpha, label = (0, 200, 255), 0.15, "CLEARING"
        else:
            sig_color, alpha, label = (0, 0, 255), 0.05, "STOP"

        ov = frame.copy()
        cv2.fillPoly(ov, [poly], sig_color)
        cv2.addWeighted(ov, alpha, frame, 1 - alpha, 0, frame)
        cv2.polylines(frame, [poly], True, sig_color, 2)

        type_colors = {
            "car": (255, 255, 0), "truck": (80, 80, 255),
            "bus": (100, 200, 255), "motorcycle": (255, 100, 255),
        }
        for box, cid in zip(boxes, class_ids):
            cname = VEHICLE_CLASSES.get(int(cid))
            if cname is None:
                continue
            bx, by = int((box[0] + box[2]) / 2), int(box[3])
            if cv2.pointPolygonTest(poly, (bx, by), False) < 0:
                continue
            x1, y1, x2, y2 = map(int, box)
            col = type_colors.get(VEHICLE_TYPE_MAP[cname], (0, 255, 0))
            cv2.rectangle(frame, (x1, y1), (x2, y2), col, 2)
            cv2.putText(frame, cname.upper(), (x1, y1 - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, 2)

        # Info panel (bottom-left). Wider + taller so the COUNT and TIMER
        # numbers can be drawn at large sizes — readable from across the room.
        h, w = frame.shape[:2]
        pw, ph = 460, 230
        px, py = 16, h - ph - 16
        ov2 = frame.copy()
        cv2.rectangle(ov2, (px, py), (px + pw, py + ph), (0, 0, 0), -1)
        cv2.addWeighted(ov2, 0.88, frame, 0.12, 0, frame)
        cv2.rectangle(frame, (px, py), (px + pw, py + ph), sig_color, 3)

        # Lane name + state label (top of the panel)
        cv2.putText(frame, f"{lane}  {label}", (px + 14, py + 44),
                    cv2.FONT_HERSHEY_DUPLEX, 1.2, sig_color, 3)
        cv2.line(frame, (px + 14, py + 60), (px + pw - 14, py + 60), sig_color, 2)

        # Vehicle count — big number
        cv2.putText(frame, "VEHICLES", (px + 14, py + 92),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (170, 170, 170), 2)
        cv2.putText(frame, str(vehicle_count), (px + 14, py + 148),
                    cv2.FONT_HERSHEY_DUPLEX, 1.8, (255, 255, 255), 4)

        # Countdown timer — also big, on the right side of the panel
        cv2.putText(frame, "TIMER", (px + 240, py + 92),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (170, 170, 170), 2)
        timer_color = (0, 255, 0) if signal_state == "green" else (
            (0, 200, 255) if signal_state == "yellow" else (0, 0, 255)
        )
        cv2.putText(frame, f"{timer}s", (px + 240, py + 148),
                    cv2.FONT_HERSHEY_DUPLEX, 1.8, timer_color, 4)

        # Status hint at the bottom of the panel
        if signal_state != "green":
            cv2.putText(frame, "VIDEO PAUSED (waiting for green)",
                        (px + 14, py + 196), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                        (140, 140, 140), 2)

        if ambulance:
            cv2.rectangle(frame, (w - 260, 16), (w - 16, 60), (0, 0, 200), -1)
            cv2.putText(frame, "AMBULANCE", (w - 250, 47),
                        cv2.FONT_HERSHEY_DUPLEX, 0.9, (255, 255, 255), 2)
        return frame


# Singleton — shared across all lane workers
vehicle_detector = VehicleDetector()
