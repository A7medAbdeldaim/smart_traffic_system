# Smart Traffic Control System — How It Works

A single-intersection AI traffic controller. Four cameras (one per lane), a YOLO
model that counts vehicles in real time, an optimizer that allocates green time
proportionally to traffic density, plus emergency-vehicle preemption and
red-light violation capture.

This document explains the architecture, the data flow, and the algorithms.
Code references are `path/to/file.py:line` so you can jump straight to the source.

---

## 1. The big picture

```
                  ┌────────────────────────────────────────────────┐
                  │                  Browser                       │
                  │  Dashboard (HTML/JS) ◄── WebSocket ──── /ws/live │
                  │                       ◄── MJPEG ──── /api/video/{N,E,S,W}
                  └────────────────────────────────────────────────┘
                                            ▲
                                            │ FastAPI app
                  ┌────────────────────────────────────────────────┐
                  │                                                │
                  │  ┌──────────────┐    ┌──────────────────────┐  │
                  │  │  Control     │───►│  Optimizer           │  │
                  │  │  loop        │    │  (density → green s) │  │
                  │  │  (1 Hz)      │◄───┴──────────────────────┘  │
                  │  └──────┬───────┘                              │
                  │         │ step()                                │
                  │         ▼                                       │
                  │  ┌──────────────┐    ┌──────────────────────┐  │
                  │  │ FeedManager  │───►│  YOLOv11 inference   │  │
                  │  │ (4 threads)  │    │  per frame           │  │
                  │  └──────┬───────┘    └──────────────────────┘  │
                  │         │ frames                                │
                  │         ▼                                       │
                  │   video/*.mp4                                   │
                  │                                                │
                  │  ┌─────────────────────┐  ┌──────────────────┐│
                  │  │ EmergencyHandler    │  │ ViolationDetector││
                  │  │ ambulance / manual  │  │ MOG2 + EasyOCR   ││
                  │  └─────────────────────┘  └────────┬─────────┘│
                  │                                    │ callback   │
                  │  ┌─────────────────────────────────▼─────────┐ │
                  │  │   SQLAlchemy / SQLite  (smart_traffic.db) │ │
                  │  │   intersections, signals, logs,           │ │
                  │  │   emergencies, violations                 │ │
                  │  └───────────────────────────────────────────┘ │
                  │                                                │
                  └────────────────────────────────────────────────┘
```

---

## 2. The main loop (1 Hz)

The whole system is driven by **one async loop** that runs once per second.
There are two implementations of it (a known wart) — one in `main.py:97` and
one in `api/app.py:111`. They do the same thing.

Each tick, the loop:

1. **Asks the traffic source for fresh data**: `lane_data = traffic_source.step()`
   - In **video mode** the source is `FeedManager` — it returns the latest
     vehicle counts that the YOLO threads have written.
   - In **demo mode** it's `DemoSimulation` — synthetic counts.
2. **Checks for emergency timeout**: 30 s since override was triggered → clear it.
3. **If emergency active**, force the source's signals into the override and
   skip optimization. Else:
4. **Optimize**: `green_times = signal_optimizer.optimize_green_times(lane_data)`
5. **Feed green times back**: `traffic_source.set_green_times(green_times)`
6. **Log to DB** (every 5 cycles for signal state, every 10 for traffic data).
7. **Broadcast** the new state to all connected WebSocket clients.

The loop never blocks — DB writes are async, YOLO inference happens in
separate threads.

---

## 3. Vehicle detection (the "AI")

### Per-lane worker thread (`detection/feed_manager.py:114`)

For each of the 4 lanes (N, E, S, W) there is one daemon thread:

```
┌────────────────────────────────────────────────────────────┐
│ while not stopped:                                         │
│   1. read next frame from video/<lane>.mp4 (or uploaded)   │
│   2. resize to 1280×720                                    │
│   3. if green AND it's been ≥ 1/inference_fps since last:  │
│        run YOLOv11 → boxes, classes                        │
│        keep only those whose bottom-center is inside the   │
│        lane's ROI polygon (drops sidewalks, oncoming etc.) │
│        update shared counts (car/truck/bus/motorcycle)     │
│   4. draw overlay (bboxes, ROI, info panel) on frame       │
│   5. JPEG-encode → publish for /api/video/{lane}           │
└────────────────────────────────────────────────────────────┘
```

### Freezeframe-on-red

When the lane's signal is **red or yellow**, the worker:
- doesn't read a new video frame (re-uses the last one)
- skips YOLO inference (the count can't change on a frozen frame)

This both **saves CPU** and visually shows that traffic is stopped.

### YOLO setup

- Model: `yolo11n.pt` (the nano variant — small, CPU-friendly).
- Input size: `imgsz=480` (configurable via `YOLO_IMG_SIZE`).
- Confidence threshold: `0.3`.
- Filtered to COCO classes [1, 2, 3, 5, 7] = bicycle, car, motorcycle, bus, truck.

### Why ROI polygons?

A lane camera sees the road **plus** sidewalks, opposite lanes, parking, etc.
Counting every vehicle in the frame would be misleading. Each lane has a
hand-drawn polygon (`detection/config.py:55-66`) that approximates the road
area; we only count vehicles whose bbox **bottom-center** falls inside it.

---

## 4. Phase state machine

A 4-way intersection cycles through 4 phases:

```
  Phase 0:  N/S green, E/W red          → for green_time seconds
  Phase 1:  N/S yellow, E/W red         → for 4 seconds
  Phase 2:  E/W green, N/S red          → for green_time seconds
  Phase 3:  E/W yellow, N/S red         → for 4 seconds
```

`current_phase` lives in the traffic source (`FeedManager` or
`DemoSimulation`). `step()` decrements `phase_remaining` by 1 each tick;
when it hits 0 we advance to the next phase and re-arm the timer using the
current `green_times` dict.

---

## 5. Optimizer — how green times are decided

### Vehicle weights (`optimizer/config.py`)

Different vehicle types contribute different "weight" to a lane's density:

| Type        | Weight | Why |
|-------------|--------|-----|
| Car         | 1.0    | baseline |
| Truck       | 2.5    | takes longer to clear, blocks more space |
| Bus         | 3.0    | even longer |
| Motorcycle  | 0.5    | smaller, faster off the line |

### Density score

For each lane:

```
density_lane  =  Σ_i  count_i  ×  weight_i
```

### Green time allocation (`optimizer/signal_optimizer.py:42`)

**Density-weighted proportional allocation.** Total cycle time
(`CYCLE_TIME=180`) minus mandatory yellow phases is divided across lanes
in proportion to their density:

```
available     = CYCLE_TIME − (4 yellow phases × YELLOW_TIME)        # 180−16 = 164
total_density = density_N + density_S + density_E + density_W
green_lane    = (density_lane / total_density) × available
green_lane    = clamp(green_lane, MIN_GREEN, MAX_GREEN)             # [10, 120]
```

If `total_density` is 0, every lane gets `MIN_GREEN` (10 s).

### AI mode vs Fixed mode

| Mode             | Behavior                                       |
|------------------|------------------------------------------------|
| **AI**           | green_times = optimizer output (varies 10–120 s) |
| **Fixed**        | green_times = 30 s for every lane             |

Toggled via the dashboard "AI Mode / Fixed Timer" chip or
`POST /api/mode/toggle`.

---

## 6. Emergency vehicle preemption

Two ways an emergency can trigger:

1. **Automatic** — the ambulance YOLO model (`ambulance_detection.pt`) detects
   an ambulance/fire-truck class on a lane (must be enabled via
   `POST /api/ambulance_detection/start` because the bundled model has a high
   false-positive rate).
2. **Manual** — the dashboard 🚨 button or `POST /api/emergency/override` with
   `{"lane": "N"}`.

When triggered:

```
  EmergencyHandler.trigger_emergency(lane)
        │
        ▼
  active_emergency = {lane, start_time}
        │
        ▼  (next control-loop tick)
  traffic_source.apply_emergency_override(lane, 30)
        │
        ▼
  _lane_phase(lane)  → "green"
  _lane_phase(other) → "red"
        │
        ▼  (broadcast)
  WebSocket clients see the override; MJPEG overlay reflects it
```

After 30 seconds (`EMERGENCY_OVERRIDE_DURATION`) the override clears
automatically and the normal cycle resumes.

---

## 7. Red-light violation detection

Runs on a separate dedicated camera (`video/violation.mp4`) in its own thread
(`detection/violation_detector.py`). Default off — toggle with
`POST /api/violation_detection/start`.

```
┌─────────────────────────────────────────────────────────────────┐
│ while running:                                                  │
│   1. read next frame from violation.mp4                         │
│   2. internal red/green cycle (10 s green, then red)            │
│   3. if RED and detection enabled:                              │
│        a. background subtraction (MOG2) below stop line         │
│        b. find contours; for each contour > 2500 px area:       │
│             - cooldown check (≥ 2 s since last capture)         │
│             - crop the bounding box                             │
│             - run EasyOCR on the crop → plate text              │
│             - regex-clean to A-Z 0-9 (≥ 4 chars else "UNKNOWN") │
│             - save annotated frame to static/captures/          │
│             - call back into the API → DB insert                │
│   4. publish annotated frame for /api/video/violation/stream    │
└─────────────────────────────────────────────────────────────────┘
```

EasyOCR is **lazy-loaded** on the first violation (~500 MB RAM, ~3 s cold
start) so the system stays light when violations aren't enabled.

The DB layer (`database/manager.py:log_violation`) writes a `Violation` row
with the plate, image path, direction, timestamp, and `status="Unpaid"`.
The dashboard's API (`/api/violations`, `/api/violations/{id}/pay`) drives a
listing + pay-fine workflow.

---

## 8. Real-time UI

### Two tabs

- **Live Videos**: 2×2 grid of MJPEG streams. Each tile is a plain
  `<img src="/api/video/N">` — the browser handles
  `multipart/x-mixed-replace` natively, no JS player. The phase badge
  (RED / GREEN / YELLOW) flips live from the WebSocket broadcast.
- **Simulation**: an animated SVG schematic of the intersection with
  cars, lights, and timers. Driven by the same WebSocket data via
  `frontend/js/intersection.js`.

### Per-lane sidebar

Always visible: vehicles, queue, density, countdown timer, signal indicator.
Updates 1 Hz from the WebSocket.

### Per-tile upload

Each video tile has a small **⤴** button. Clicking it uploads an `.mp4`
(or `.mov/.mkv/.avi/.webm`, ≤200 MB) to `POST /api/video/upload/{lane}`,
which writes it to disk and signals the worker thread to release the old
`cv2.VideoCapture` and reopen on the new path. The live feed switches in
about a second; no service restart needed. Uploaded paths persist across
restarts via `video/_uploaded_paths.json`.

---

## 9. Data persistence

SQLite via SQLAlchemy async (`database/models.py`). Tables:

| Table             | What it holds |
|-------------------|---------------|
| `intersections`   | one row — geographic config |
| `cameras`         | one row per lane — URL + status |
| `traffic_signals` | current phase per lane (DB-backed for `/api/status` consistency) |
| `traffic_data_logs` | rolling history — counts, density, speed, queue, waiting time |
| `emergency_events` | every emergency that fires |
| `violations`      | red-light violations with plate + image path |

DB is created on first boot via `Base.metadata.create_all`.
WAL mode + busy-timeout are enabled so the async loop and the violation
thread don't fight for the same SQLite file.

---

## 10. REST + WebSocket API

| Method | Path                                  | Purpose |
|--------|---------------------------------------|---------|
| `GET`  | `/`                                   | dashboard HTML |
| `GET`  | `/api/status`                         | current phases + counts (DB-backed) |
| `GET`  | `/api/logs?minutes=30`                | historical traffic data |
| `GET`  | `/api/stats`                          | aggregate metrics |
| `POST` | `/api/mode/toggle`                    | switch AI ↔ Fixed |
| `POST` | `/api/emergency/override`             | manual override `{"lane": "N"}` |
| `GET`  | `/api/emergency/history`              | past emergencies |
| `POST` | `/api/ambulance_detection/{action}`   | enable/disable auto-detect |
| `POST` | `/api/violation_detection/{action}`   | enable/disable auto-capture |
| `GET`  | `/api/violations`                     | list violations |
| `POST` | `/api/violations/{id}/pay`            | mark paid |
| `POST` | `/api/video/upload/{lane}`            | replace lane video (multipart) |
| `GET`  | `/api/video/sources`                  | which file each lane is reading |
| `GET`  | `/api/video/{lane}`                   | MJPEG stream (live YOLO) |
| `GET`  | `/api/video/{lane}/snapshot`          | single JPEG |
| `GET`  | `/api/video/violation/stream`         | MJPEG of violation cam |
| `WS`   | `/ws/live`                            | 1 Hz state broadcast |

---

## 11. Configuration

Settings come from `.env` (see `.env.example`). Most useful knobs:

```
DETECTION_MODE=video              # or "demo" for the synthetic generator
YOLO_MODEL_PATH=./models/yolo11n.pt
YOLO_IMG_SIZE=480                 # smaller = faster on CPU
YOLO_CONF=0.3
INFERENCE_FPS=3                   # how often each lane runs YOLO

MIN_GREEN_TIME=10
MAX_GREEN_TIME=120
YELLOW_TIME=4
CYCLE_TIME=180

EMERGENCY_OVERRIDE_DURATION=30

CAR_WEIGHT=1.0
TRUCK_WEIGHT=2.5
BUS_WEIGHT=3.0
MOTORCYCLE_WEIGHT=0.5

API_HOST=0.0.0.0
API_PORT=8000
```

Defaults in code already match production (`DETECTION_MODE=video`), so an
out-of-the-box `python main.py` runs the full real-detection pipeline.

---

## 12. Threading model — what runs where

| Thread / task          | What it does |
|------------------------|--------------|
| **asyncio main loop**  | FastAPI, control loop, WebSocket broadcast, DB writes |
| **4 × FeedManager threads** | One per lane: `cv2.VideoCapture` + YOLO + draw overlay |
| **ViolationDetector thread** | Reads `violation.mp4`, runs MOG2 + EasyOCR |
| **MJPEG client tasks** | One async task per connected `<img>` — just yields the latest JPEG |

YOLO inference is CPU-bound but holds the GIL only during the C++ call — so
the threads make real progress in parallel. The async loop never blocks on
inference; it only reads atomic snapshots that the threads update under a
per-lane lock.

---

## 13. Deployment

The system runs on a single VM (Compute Engine in our deploy). The
`run.sh` wrapper is a 4-line restart-loop that the user's `@reboot` cron
launches on boot. Visit `http://<VM_EXTERNAL_IP>:8000` to use the dashboard.

For local dev:

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python main.py        # http://localhost:8000
```

Switch to demo mode (no GPU/video deps needed) by setting
`DETECTION_MODE=demo` in `.env`.

---

## 14. Known limitations

- **One intersection only** — the database schema supports multiple
  (`Intersection.id` is a foreign key everywhere), but the control loop and
  the dashboard are hard-wired to one.
- **No TLS** out of the box — put nginx in front for HTTPS.
- **Bundled ambulance model has high false positives** on ordinary traffic;
  must be explicitly enabled. A retrained model would let it be on by default.
- **Two control loops** in the codebase (`main.py` and `api/app.py:lifespan`)
  duplicate work when the app is launched via `python main.py`. Functional
  but wasteful — would consolidate in a refactor.
- **Speed / queue / waiting_time are heuristic** when sourced from a real
  camera. They derive from `vehicle_count + signal_phase` rather than being
  measured. To get real speeds, wire YOLO's `model.track()` and compute
  centroid velocities.
