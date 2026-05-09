"""Threaded video feeds + YOLO inference adapter.

Each lane runs in its own thread, reading frames from its .mp4 and running
YOLO inference at a throttled rate. The control loop reads atomic snapshots
via ``get_all_lane_data()`` — the return shape matches DemoSimulation.step()
so the optimizer / DB / WebSocket layer don't need any changes.

Phase state (current_phase, phase_remaining, green_times) is kept here for
the same reason: DemoSimulation owns it today, and we want a drop-in swap.
"""
from __future__ import annotations

import json
import os
import random
import threading
import time
from datetime import datetime
from typing import Dict, Optional

import cv2
import numpy as np

from .config import LANE_VIDEO_MAP, det_config
from .vehicle_detector import vehicle_detector


LANES = ["N", "E", "S", "W"]

# JSON file that persists user-uploaded video paths across restarts.
# Lives next to the .mp4 files so paths in it stay valid relative to CWD.
UPLOADED_PATHS_STATE = os.path.join("video", "_uploaded_paths.json")


class _LaneState:
    """Per-lane shared state, guarded by ``lock``."""

    def __init__(self, lane: str):
        self.lane = lane
        self.lock = threading.RLock()

        # Latest detection results
        self.boxes = np.empty((0, 4))
        self.class_ids = np.empty((0,), dtype=int)
        self.counts: Dict[str, int] = {"car": 0, "truck": 0, "bus": 0, "motorcycle": 0}
        self.vehicle_count: int = 0

        # Latest JPEG (for MJPEG streaming)
        self.jpeg: Optional[bytes] = None

        # Ambulance / emergency
        self.ambulance: bool = False
        self.frame_idx: int = 0


class FeedManager:
    """Owns the YOLO threads and the signal-phase state machine."""

    def __init__(self):
        self.lanes = LANES
        self.states: Dict[str, _LaneState] = {l: _LaneState(l) for l in self.lanes}

        # Per-lane current video path. Defaults from config; overridden by any
        # entries in UPLOADED_PATHS_STATE (set when the user uploads via the API).
        self.current_paths: Dict[str, str] = dict(LANE_VIDEO_MAP)
        self._reload_evts: Dict[str, threading.Event] = {
            l: threading.Event() for l in self.lanes
        }
        self._load_uploaded_paths()

        # Phase state machine (mirrors DemoSimulation)
        # 0 = N/S green, 1 = N/S yellow, 2 = E/W green, 3 = E/W yellow
        self.current_phase: int = 0
        self.phase_remaining: int = 10
        self.green_times: Dict[str, int] = {l: 10 for l in self.lanes}
        self.yellow_time: int = 4
        self.step_count: int = 0
        self._phase_lock = threading.RLock()

        # Emergency override: when set, that lane forces green and all others red.
        # The broadcast layer + MJPEG overlay both read _lane_phase, so this
        # propagates everywhere automatically.
        self._emergency_lane: Optional[str] = None
        self._emergency_remaining: int = 0

        # Worker threads
        self._stop_evt = threading.Event()
        self._threads: list[threading.Thread] = []

        # Optional ambulance detector — wired up by detection/__init__.py
        self.ambulance_detector = None
        # Optional emergency handler callback (set by main bootstrap)
        self.emergency_handler = None
        # Manual gate. The bundled ambulance model has high false-positive rate
        # on ordinary traffic (mirrors the cloned repo's `emergency_detection_active`
        # default-off pattern), so detection must be explicitly enabled.
        self.ambulance_detection_enabled = False

    # ── Lifecycle ─────────────────────────────────────────────────────────────
    def start(self):
        if self._threads:
            return
        self._stop_evt.clear()
        for lane in self.lanes:
            t = threading.Thread(
                target=self._lane_loop, args=(lane,), daemon=True, name=f"feed-{lane}"
            )
            t.start()
            self._threads.append(t)
        print(f"✓ FeedManager started ({len(self._threads)} lanes)")

    def stop(self):
        self._stop_evt.set()
        for t in self._threads:
            t.join(timeout=2)
        self._threads.clear()
        print("✓ FeedManager stopped")

    # ── Per-lane worker ───────────────────────────────────────────────────────
    def _lane_loop(self, lane: str):
        path = self.current_paths[lane]
        if not os.path.exists(path):
            print(f"⚠️  [{lane}] video not found: {path} — thread exiting")
            return

        cap = cv2.VideoCapture(path)
        target_dt = 1.0 / max(1, det_config.inference_fps)
        last_inf = 0.0
        st = self.states[lane]

        while not self._stop_evt.is_set():
            # Hot-reload: pick up a newly uploaded video without restarting
            if self._reload_evts[lane].is_set():
                cap.release()
                new_path = self.current_paths[lane]
                if not os.path.exists(new_path):
                    print(f"⚠️  [{lane}] reload requested but file missing: {new_path}")
                    self._reload_evts[lane].clear()
                    return
                cap = cv2.VideoCapture(new_path)
                self._reload_evts[lane].clear()
                print(f"🔄 [{lane}] video swapped → {new_path}")

            ok, frame = cap.read()
            if not ok or frame is None:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

            frame = cv2.resize(frame, (det_config.display_width, det_config.display_height))
            now = time.time()

            # Throttle YOLO inference (CPU-bound). Reuse last detections for
            # frames in between so the displayed video stays smooth.
            do_inference = (now - last_inf) >= target_dt
            if do_inference:
                boxes, class_ids = vehicle_detector.detect(frame)
                counts, total = vehicle_detector.count_in_roi(boxes, class_ids, lane)
                with st.lock:
                    st.boxes = boxes
                    st.class_ids = class_ids
                    st.counts = {k: counts.get(k, 0) for k in ("car", "truck", "bus", "motorcycle")}
                    st.vehicle_count = total
                last_inf = now

                # Ambulance check (separate model, gated + throttled)
                st.frame_idx += 1
                if (
                    self.ambulance_detection_enabled
                    and self.ambulance_detector is not None
                    and st.frame_idx % det_config.ambulance_check_every_n_frames == 0
                ):
                    found = self.ambulance_detector.detect(frame)
                    if found and not st.ambulance:
                        print(f"🚑 [ALERT] Ambulance detected on lane {lane}")
                        if self.emergency_handler is not None:
                            try:
                                self.emergency_handler.trigger_emergency(lane, 'ambulance')
                            except Exception as e:
                                print(f"  emergency_handler.trigger_emergency failed: {e}")
                    st.ambulance = found

            # Snapshot read for overlay rendering (cheap)
            with st.lock:
                boxes_s, cls_s = st.boxes, st.class_ids
                vc = st.vehicle_count
                amb = st.ambulance
            phase = self._lane_phase(lane)
            timer = self._lane_remaining(lane)

            annotated = vehicle_detector.draw_overlay(
                frame, boxes_s, cls_s, lane, phase, timer, vc, amb
            )
            ok, buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ok:
                with st.lock:
                    st.jpeg = buf.tobytes()

            # Yield ~ display FPS
            time.sleep(0.04)

        cap.release()

    # ── Phase state machine (same shape as DemoSimulation) ────────────────────
    def _lane_phase(self, lane: str) -> str:
        with self._phase_lock:
            # Emergency override wins over the normal cycle
            if self._emergency_lane is not None:
                return "green" if lane == self._emergency_lane else "red"
            if self.current_phase == 0:
                return "green" if lane in ("N", "S") else "red"
            if self.current_phase == 2:
                return "green" if lane in ("E", "W") else "red"
            if self.current_phase == 1:
                return "yellow" if lane in ("N", "S") else "red"
            if self.current_phase == 3:
                return "yellow" if lane in ("E", "W") else "red"
            return "red"

    def _lane_remaining(self, lane: str) -> int:
        with self._phase_lock:
            if self._emergency_lane is not None:
                return self._emergency_remaining if lane == self._emergency_lane else 0
            return self.phase_remaining if self._lane_phase(lane) != "red" else 0

    def _next_phase(self):
        with self._phase_lock:
            self.current_phase = (self.current_phase + 1) % 4
            if self.current_phase in (1, 3):
                self.phase_remaining = self.yellow_time
            elif self.current_phase == 0:
                self.phase_remaining = max(self.green_times["N"], self.green_times["S"])
            else:  # phase 2
                self.phase_remaining = max(self.green_times["E"], self.green_times["W"])

    def set_green_times(self, green_times: Dict[str, int]):
        with self._phase_lock:
            self.green_times.update(green_times)

    def set_phase(self, phase_index: int):
        with self._phase_lock:
            self.current_phase = phase_index % 4

    def set_phase_duration(self, seconds: int):
        with self._phase_lock:
            self.phase_remaining = seconds

    def apply_emergency_override(self, lane: str, duration: int) -> None:
        """Force one lane green and all others red, regardless of the cycle."""
        if lane not in self.lanes:
            raise ValueError(f"unknown lane: {lane}")
        with self._phase_lock:
            self._emergency_lane = lane
            self._emergency_remaining = max(1, int(duration))

    def clear_emergency_override(self) -> None:
        with self._phase_lock:
            self._emergency_lane = None
            self._emergency_remaining = 0

    # ── Public API consumed by the control loop ───────────────────────────────
    def step(self) -> Dict[str, Dict]:
        """Advance phase by 1s and return the same lane_data shape as DemoSimulation."""
        self.step_count += 1
        with self._phase_lock:
            if self._emergency_lane is not None:
                self._emergency_remaining = max(0, self._emergency_remaining - 1)
            else:
                self.phase_remaining -= 1
                if self.phase_remaining <= 0:
                    self._next_phase()
        return self.get_all_lane_data()

    def get_all_lane_data(self) -> Dict[str, Dict]:
        out: Dict[str, Dict] = {}
        for lane in self.lanes:
            out[lane] = self._lane_data(lane)
        return out

    def _lane_data(self, lane: str) -> Dict:
        st = self.states[lane]
        with st.lock:
            counts = dict(st.counts)
            vc = st.vehicle_count
            amb = st.ambulance
        counts["total"] = vc

        # Weighted density score (matches optimizer.config weights)
        density = (
            counts["car"] * 1.0
            + counts["truck"] * 2.5
            + counts["bus"] * 3.0
            + counts["motorcycle"] * 0.5
        )

        phase = self._lane_phase(lane)
        is_green = phase == "green"

        # Heuristic speed / queue / waiting_time — same shape as DemoSimulation
        if is_green:
            congestion = min(1.0, vc / 40.0)
            speed = 50.0 * (1.0 - congestion * 0.6) + random.uniform(-3, 3)
            speed = max(0.0, min(50.0, speed))
            queue = int(vc * 0.3 * random.uniform(0.5, 1.0))
            waiting_time = queue * random.uniform(2, 5)
        else:
            speed = random.uniform(0, 5)
            queue = int(vc * 0.9 * random.uniform(0.9, 1.0))
            waiting_time = vc * random.uniform(8, 15)

        return {
            "vehicle_count": vc,
            "counts": counts,
            "density": density,
            "speed": speed,
            "queue": max(0, min(vc, queue)),
            "waiting_time": waiting_time,
            "phase": phase,
            "remaining": self._lane_remaining(lane),
            "ambulance": amb,
        }

    def get_snapshot(self) -> Dict:
        return {
            "timestamp": datetime.now().isoformat(),
            "step": self.step_count,
            "phase": self.current_phase,
            "lanes": self.get_all_lane_data(),
        }

    def get_latest_jpeg(self, lane: str) -> Optional[bytes]:
        if lane not in self.states:
            return None
        with self.states[lane].lock:
            return self.states[lane].jpeg

    # ── Compatibility shims so this is a drop-in for DemoSimulation ───────────
    def inject_emergency(self, lane: str) -> bool:
        if lane in self.states:
            with self.states[lane].lock:
                self.states[lane].ambulance = True
            return True
        return False

    # ── User-uploaded video swaps ─────────────────────────────────────────────
    def replace_video(self, lane: str, new_path: str) -> None:
        """Atomically swap the video file for a lane. Worker reopens the
        capture on its next loop iteration — no service restart required.
        """
        if lane not in self.lanes:
            raise ValueError(f"unknown lane: {lane}")
        if not os.path.exists(new_path):
            raise FileNotFoundError(new_path)
        self.current_paths[lane] = new_path
        self._save_uploaded_paths()
        self._reload_evts[lane].set()

    def _load_uploaded_paths(self) -> None:
        if not os.path.exists(UPLOADED_PATHS_STATE):
            return
        try:
            with open(UPLOADED_PATHS_STATE, "r") as f:
                data = json.load(f)
            for lane, path in data.items():
                if lane in self.lanes and os.path.exists(path):
                    self.current_paths[lane] = path
                    print(f"  [{lane}] using uploaded video: {path}")
        except Exception as e:
            print(f"  failed to load uploaded paths state: {e}")

    def _save_uploaded_paths(self) -> None:
        # Only persist entries that differ from the default (cleaner state file)
        diff = {l: p for l, p in self.current_paths.items() if p != LANE_VIDEO_MAP[l]}
        try:
            os.makedirs(os.path.dirname(UPLOADED_PATHS_STATE) or ".", exist_ok=True)
            with open(UPLOADED_PATHS_STATE, "w") as f:
                json.dump(diff, f, indent=2)
        except Exception as e:
            print(f"  failed to save uploaded paths state: {e}")
