"""Red-light violation detector.

Reads ``video/violation.mp4`` in a background thread, runs background
subtraction to find moving vehicles, and when a vehicle crosses the
stop-line during a red phase, captures the frame and runs EasyOCR for
plate recognition. Violations are reported via a callback so the caller
(api/app.py) can persist them through the async DB layer without us
needing an event loop here.

Design follows the cloned repo's ``traffic_logic()`` (main.py:387-477)
but adapted to:
  * use a callback instead of TinyDB
  * lazy-load EasyOCR on first violation (saves ~500MB RAM if unused)
  * keep its own internal red/green cycle so it stays self-contained
    regardless of what the main intersection controller is doing
"""
from __future__ import annotations

import os
import re
import threading
import time
from datetime import datetime
from typing import Callable, Optional

import cv2
import numpy as np

from .config import det_config


CAPTURE_DIR = "static/captures"
LINE_POSITION_RATIO = 0.6
MIN_VEHICLE_AREA = 2500
CAPTURE_COOLDOWN_SEC = 2.0


# Reported to the registered callback. Caller is responsible for persisting
# (typically via db_manager.log_violation in an asyncio task).
ViolationCallback = Callable[[dict], None]


class ViolationDetector:
    def __init__(self, video_path: Optional[str] = None):
        self.video_path = video_path or det_config.video_path_violation
        self.enabled: bool = False
        self.callback: Optional[ViolationCallback] = None

        os.makedirs(CAPTURE_DIR, exist_ok=True)

        self._thread: Optional[threading.Thread] = None
        self._stop_evt = threading.Event()

        self._frame_lock = threading.Lock()
        self._latest_jpeg: Optional[bytes] = None

        # EasyOCR is heavy (~500MB) — lazy load
        self._ocr = None
        self._ocr_lock = threading.Lock()

        # Internal red/green cycle (10s green, then red until next loop)
        self._green_duration = 10
        self._cycle_start = time.time()

    # ── Lifecycle ─────────────────────────────────────────────────────────────
    def start(self):
        if self._thread:
            return
        self._stop_evt.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="violation")
        self._thread.start()
        print(f"✓ ViolationDetector started ({self.video_path})")

    def stop(self):
        self._stop_evt.set()
        if self._thread:
            self._thread.join(timeout=2)
        self._thread = None

    def set_callback(self, cb: ViolationCallback):
        self.callback = cb

    def get_latest_jpeg(self) -> Optional[bytes]:
        with self._frame_lock:
            return self._latest_jpeg

    # ── OCR (lazy) ────────────────────────────────────────────────────────────
    def _get_ocr(self):
        if self._ocr is not None:
            return self._ocr
        with self._ocr_lock:
            if self._ocr is None:
                print("⏳ Loading EasyOCR (~500MB, first use only)…")
                import easyocr  # local import — only paid when first violation hits
                self._ocr = easyocr.Reader(['en'], gpu=False)
                print("✓ EasyOCR loaded")
        return self._ocr

    def _read_plate(self, car_img: np.ndarray) -> str:
        try:
            ocr = self._get_ocr()
            gray = cv2.cvtColor(car_img, cv2.COLOR_BGR2GRAY)
            text_res = ocr.readtext(gray, detail=0)
            plate_text = "".join(text_res).strip()
            cleaned = re.sub(r"[^A-Z0-9]", "", plate_text.upper())
            if len(cleaned) >= 4:
                return cleaned
        except Exception as e:
            print(f"  OCR failed: {e}")
        return "UNKNOWN"

    # ── Worker ────────────────────────────────────────────────────────────────
    def _loop(self):
        if not os.path.exists(self.video_path):
            print(f"⚠️  ViolationDetector: video not found ({self.video_path}) — exiting")
            return

        cap = cv2.VideoCapture(self.video_path)
        bg_sub = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=50)
        last_capture_t = 0.0

        while not self._stop_evt.is_set():
            ok, frame = cap.read()
            if not ok or frame is None:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                self._cycle_start = time.time()
                continue

            frame = cv2.resize(frame, (640, 360))
            h, w = frame.shape[:2]
            line_y = int(h * LINE_POSITION_RATIO)

            elapsed = time.time() - self._cycle_start
            if elapsed < self._green_duration:
                is_red = False
                color, label = (0, 255, 0), f"GREEN: {int(self._green_duration - elapsed)}s"
            else:
                is_red = True
                color, label = (0, 0, 255), "RED LIGHT"

            if is_red and self.enabled:
                roi = frame[line_y:h, 0:w]
                mask = bg_sub.apply(roi)
                _, mask = cv2.threshold(mask, 254, 255, cv2.THRESH_BINARY)
                mask = cv2.medianBlur(mask, 5)
                contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

                for cnt in contours:
                    if cv2.contourArea(cnt) <= MIN_VEHICLE_AREA:
                        continue
                    now = time.time()
                    if (now - last_capture_t) <= CAPTURE_COOLDOWN_SEC:
                        continue
                    last_capture_t = now

                    x, y, ww, hh = cv2.boundingRect(cnt)
                    abs_y = y + line_y
                    car_img = frame[abs_y:abs_y + hh, x:x + ww]
                    plate = self._read_plate(car_img) if car_img.size else "UNKNOWN"

                    fname = f"violation_{plate}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    cv2.rectangle(frame, (x, abs_y), (x + ww, abs_y + hh), (0, 0, 255), 2)
                    cv2.putText(frame, plate, (x, abs_y - 5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                    out_path = os.path.join(CAPTURE_DIR, fname)
                    cv2.imwrite(out_path, frame)
                    print(f"🚨 VIOLATION captured: {plate} → {out_path}")

                    if self.callback is not None:
                        try:
                            self.callback({
                                "plate_number": plate,
                                "image_path": out_path,
                                "direction": "S-CAM",
                                "reason": "Red Light",
                            })
                        except Exception as e:
                            print(f"  violation callback failed: {e}")

            # Annotate display
            cv2.line(frame, (0, line_y), (w, line_y), color, 2)
            cv2.putText(frame, label, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

            ok, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ok:
                with self._frame_lock:
                    self._latest_jpeg = buf.tobytes()

            time.sleep(0.03)

        cap.release()


# Singleton
violation_detector = ViolationDetector()
