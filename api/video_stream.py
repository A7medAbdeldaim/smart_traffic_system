"""Video streaming endpoints for camera feeds"""
import cv2
import numpy as np
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional
import io

from .app import app_state

router = APIRouter(prefix="/api/video", tags=["video"])


def generate_placeholder_frame(lane: str, width: int = 640, height: int = 480) -> bytes:
    """Generate a placeholder frame when no video is available"""
    # Create dark background
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frame[:] = (10, 14, 23)  # Dark background color

    # Add text
    text = f"NO FEED - {lane}"
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1.5
    thickness = 3
    color = (100, 100, 100)  # Gray text

    # Get text size to center it
    (text_width, text_height), _ = cv2.getTextSize(text, font, font_scale, thickness)
    x = (width - text_width) // 2
    y = (height + text_height) // 2

    cv2.putText(frame, text, (x, y), font, font_scale, color, thickness)

    # Add lane direction indicator
    direction_text = f"Lane {lane}"
    cv2.putText(frame, direction_text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX,
                0.8, (150, 150, 150), 2)

    # Encode as JPEG
    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    return buffer.tobytes()


def draw_car(frame, x, y, color, vertical=True):
    """Draw a simple car icon"""
    if vertical:  # Car moving up/down
        # Body
        cv2.rectangle(frame, (x-15, y-25), (x+15, y+25), color, -1)
        cv2.rectangle(frame, (x-15, y-25), (x+15, y+25), (255, 255, 255), 2)
        # Windshield
        cv2.rectangle(frame, (x-12, y-15), (x+12, y), (100, 100, 100), -1)
        # Wheels
        cv2.circle(frame, (x-12, y-20), 4, (50, 50, 50), -1)
        cv2.circle(frame, (x+12, y-20), 4, (50, 50, 50), -1)
        cv2.circle(frame, (x-12, y+20), 4, (50, 50, 50), -1)
        cv2.circle(frame, (x+12, y+20), 4, (50, 50, 50), -1)
    else:  # Car moving left/right
        # Body
        cv2.rectangle(frame, (x-25, y-15), (x+25, y+15), color, -1)
        cv2.rectangle(frame, (x-25, y-15), (x+25, y+15), (255, 255, 255), 2)
        # Windshield
        cv2.rectangle(frame, (x-15, y-12), (x, y+12), (100, 100, 100), -1)
        # Wheels
        cv2.circle(frame, (x-20, y-12), 4, (50, 50, 50), -1)
        cv2.circle(frame, (x-20, y+12), 4, (50, 50, 50), -1)
        cv2.circle(frame, (x+20, y-12), 4, (50, 50, 50), -1)
        cv2.circle(frame, (x+20, y+12), 4, (50, 50, 50), -1)


def draw_truck(frame, x, y, color, vertical=True):
    """Draw a simple truck icon"""
    if vertical:
        # Cargo area
        cv2.rectangle(frame, (x-18, y-35), (x+18, y+10), color, -1)
        cv2.rectangle(frame, (x-18, y-35), (x+18, y+10), (255, 255, 255), 2)
        # Cabin
        cv2.rectangle(frame, (x-15, y+10), (x+15, y+30), color, -1)
        cv2.rectangle(frame, (x-15, y+10), (x+15, y+30), (255, 255, 255), 2)
        # Windshield
        cv2.rectangle(frame, (x-12, y+12), (x+12, y+22), (100, 100, 100), -1)
        # Wheels
        cv2.circle(frame, (x-15, y+28), 5, (50, 50, 50), -1)
        cv2.circle(frame, (x+15, y+28), 5, (50, 50, 50), -1)
    else:
        # Cargo area
        cv2.rectangle(frame, (x-35, y-18), (x+10, y+18), color, -1)
        cv2.rectangle(frame, (x-35, y-18), (x+10, y+18), (255, 255, 255), 2)
        # Cabin
        cv2.rectangle(frame, (x+10, y-15), (x+30, y+15), color, -1)
        cv2.rectangle(frame, (x+10, y-15), (x+30, y+15), (255, 255, 255), 2)
        # Windshield
        cv2.rectangle(frame, (x+12, y-12), (x+22, y+12), (100, 100, 100), -1)
        # Wheels
        cv2.circle(frame, (x+28, y-15), 5, (50, 50, 50), -1)
        cv2.circle(frame, (x+28, y+15), 5, (50, 50, 50), -1)


def draw_bus(frame, x, y, color, vertical=True):
    """Draw a simple bus icon"""
    if vertical:
        # Body
        cv2.rectangle(frame, (x-20, y-40), (x+20, y+40), color, -1)
        cv2.rectangle(frame, (x-20, y-40), (x+20, y+40), (255, 255, 255), 2)
        # Windows
        cv2.rectangle(frame, (x-16, y-35), (x+16, y-20), (150, 150, 150), -1)
        cv2.rectangle(frame, (x-16, y-15), (x+16, y), (150, 150, 150), -1)
        cv2.rectangle(frame, (x-16, y+5), (x+16, y+20), (150, 150, 150), -1)
        # Wheels
        cv2.circle(frame, (x-16, y+35), 5, (50, 50, 50), -1)
        cv2.circle(frame, (x+16, y+35), 5, (50, 50, 50), -1)
    else:
        # Body
        cv2.rectangle(frame, (x-40, y-20), (x+40, y+20), color, -1)
        cv2.rectangle(frame, (x-40, y-20), (x+40, y+20), (255, 255, 255), 2)
        # Windows
        cv2.rectangle(frame, (x-35, y-16), (x-20, y+16), (150, 150, 150), -1)
        cv2.rectangle(frame, (x-15, y-16), (x, y+16), (150, 150, 150), -1)
        cv2.rectangle(frame, (x+5, y-16), (x+20, y+16), (150, 150, 150), -1)
        # Wheels
        cv2.circle(frame, (x+35, y-16), 5, (50, 50, 50), -1)
        cv2.circle(frame, (x+35, y+16), 5, (50, 50, 50), -1)


def draw_motorcycle(frame, x, y, color, vertical=True):
    """Draw a simple motorcycle icon"""
    if vertical:
        # Body (small)
        cv2.rectangle(frame, (x-8, y-15), (x+8, y+15), color, -1)
        cv2.rectangle(frame, (x-8, y-15), (x+8, y+15), (255, 255, 255), 2)
        # Wheels
        cv2.circle(frame, (x, y-12), 4, (50, 50, 50), -1)
        cv2.circle(frame, (x, y+12), 4, (50, 50, 50), -1)
    else:
        # Body (small)
        cv2.rectangle(frame, (x-15, y-8), (x+15, y+8), color, -1)
        cv2.rectangle(frame, (x-15, y-8), (x+15, y+8), (255, 255, 255), 2)
        # Wheels
        cv2.circle(frame, (x-12, y), 4, (50, 50, 50), -1)
        cv2.circle(frame, (x+12, y), 4, (50, 50, 50), -1)


def generate_demo_frame(lane: str, vehicle_count: int, phase: str = 'red', queue: int = 0, width: int = 640, height: int = 480) -> bytes:
    """Generate a synthetic traffic frame with realistic vehicle icons that respect traffic signals"""
    # Create dark road background
    frame = np.zeros((height, width, 3), dtype=np.uint8)

    # Draw road (dark gray)
    road_color = (40, 40, 40)
    cv2.rectangle(frame, (0, 0), (width, height), road_color, -1)

    # Determine if vertical or horizontal lane
    vertical = lane in ['N', 'S']

    # Draw lane markings
    lane_color = (200, 200, 200)
    if vertical:
        for y in range(0, height, 40):
            cv2.rectangle(frame, (width // 2 - 2, y), (width // 2 + 2, y + 20), lane_color, -1)
        # Draw stop line at bottom
        cv2.line(frame, (0, height - 80), (width, height - 80), (255, 255, 255), 3)
    else:
        for x in range(0, width, 40):
            cv2.rectangle(frame, (x, height // 2 - 2), (x + 20, height // 2 + 2), lane_color, -1)
        # Draw stop line at right
        cv2.line(frame, (width - 80, 0), (width - 80, height), (255, 255, 255), 3)

    # Vehicle type distribution (based on typical traffic)
    np.random.seed(hash(lane) % 1000 + vehicle_count)

    # Generate vehicle list with types
    vehicles = []
    for i in range(min(vehicle_count, 12)):  # Max 12 visible vehicles
        rand = np.random.random()
        if rand < 0.70:
            vtype = 'car'
            color = (0, 200, 100)  # Green
        elif rand < 0.85:
            vtype = 'truck'
            color = (255, 100, 0)  # Blue
        elif rand < 0.95:
            vtype = 'bus'
            color = (0, 50, 255)  # Red
        else:
            vtype = 'motorcycle'
            color = (0, 220, 220)  # Yellow

        vehicles.append({'type': vtype, 'color': color})

    # Draw vehicles based on traffic signal phase
    if vertical:
        # Arrange vehicles vertically in FOUR lanes
        lane_offset = [width // 5, 2 * width // 5, 3 * width // 5, 4 * width // 5]

        if phase == 'red':
            # RED LIGHT: Vehicles stopped at stop line (queued)
            queued_count = min(queue, len(vehicles))

            # Queued vehicles (stopped at light)
            for i in range(queued_count):
                x = lane_offset[i % 4]
                # Stack them close to stop line
                y = height - 120 - (i // 4) * 60  # Stack back from stop line

                if vehicles[i]['type'] == 'car':
                    draw_car(frame, x, y, vehicles[i]['color'], vertical=True)
                elif vehicles[i]['type'] == 'truck':
                    draw_truck(frame, x, y, vehicles[i]['color'], vertical=True)
                elif vehicles[i]['type'] == 'bus':
                    draw_bus(frame, x, y, vehicles[i]['color'], vertical=True)
                else:
                    draw_motorcycle(frame, x, y, vehicles[i]['color'], vertical=True)

            # Other vehicles approaching (further back)
            for i in range(queued_count, len(vehicles)):
                x = lane_offset[i % 4]
                y = 100 + (i - queued_count) * 80  # Spaced further back

                if y < height - 200:  # Don't overlap with queue
                    if vehicles[i]['type'] == 'car':
                        draw_car(frame, x, y, vehicles[i]['color'], vertical=True)
                    elif vehicles[i]['type'] == 'truck':
                        draw_truck(frame, x, y, vehicles[i]['color'], vertical=True)
                    elif vehicles[i]['type'] == 'bus':
                        draw_bus(frame, x, y, vehicles[i]['color'], vertical=True)
                    else:
                        draw_motorcycle(frame, x, y, vehicles[i]['color'], vertical=True)
        else:
            # GREEN/YELLOW LIGHT: Vehicles moving (spread out evenly)
            spacing = (height - 160) // (len(vehicles) + 1)

            for i, vehicle in enumerate(vehicles):
                x = lane_offset[i % 4]
                y = 100 + i * spacing  # Evenly distributed along road

                if vehicle['type'] == 'car':
                    draw_car(frame, x, y, vehicle['color'], vertical=True)
                elif vehicle['type'] == 'truck':
                    draw_truck(frame, x, y, vehicle['color'], vertical=True)
                elif vehicle['type'] == 'bus':
                    draw_bus(frame, x, y, vehicle['color'], vertical=True)
                else:
                    draw_motorcycle(frame, x, y, vehicle['color'], vertical=True)
    else:
        # Arrange vehicles horizontally in FOUR lanes
        lane_offset = [height // 5, 2 * height // 5, 3 * height // 5, 4 * height // 5]

        if phase == 'red':
            # RED LIGHT: Vehicles stopped at stop line
            queued_count = min(queue, len(vehicles))

            # Queued vehicles
            for i in range(queued_count):
                y = lane_offset[i % 4]
                x = width - 120 - (i // 4) * 60  # Stack back from stop line

                if vehicles[i]['type'] == 'car':
                    draw_car(frame, x, y, vehicles[i]['color'], vertical=False)
                elif vehicles[i]['type'] == 'truck':
                    draw_truck(frame, x, y, vehicles[i]['color'], vertical=False)
                elif vehicles[i]['type'] == 'bus':
                    draw_bus(frame, x, y, vehicles[i]['color'], vertical=False)
                else:
                    draw_motorcycle(frame, x, y, vehicles[i]['color'], vertical=False)

            # Other vehicles approaching
            for i in range(queued_count, len(vehicles)):
                y = lane_offset[i % 4]
                x = 100 + (i - queued_count) * 80

                if x < width - 200:
                    if vehicles[i]['type'] == 'car':
                        draw_car(frame, x, y, vehicles[i]['color'], vertical=False)
                    elif vehicles[i]['type'] == 'truck':
                        draw_truck(frame, x, y, vehicles[i]['color'], vertical=False)
                    elif vehicles[i]['type'] == 'bus':
                        draw_bus(frame, x, y, vehicles[i]['color'], vertical=False)
                    else:
                        draw_motorcycle(frame, x, y, vehicles[i]['color'], vertical=False)
        else:
            # GREEN/YELLOW LIGHT: Vehicles moving
            spacing = (width - 160) // (len(vehicles) + 1)

            for i, vehicle in enumerate(vehicles):
                x = 100 + i * spacing
                y = lane_offset[i % 4]

                if vehicle['type'] == 'car':
                    draw_car(frame, x, y, vehicle['color'], vertical=False)
                elif vehicle['type'] == 'truck':
                    draw_truck(frame, x, y, vehicle['color'], vertical=False)
                elif vehicle['type'] == 'bus':
                    draw_bus(frame, x, y, vehicle['color'], vertical=False)
                else:
                    draw_motorcycle(frame, x, y, vehicle['color'], vertical=False)

    # Add info overlay with phase indicator
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (width, 60), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

    # Add text
    cv2.putText(frame, f"Lane {lane}", (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(frame, f"Vehicles: {vehicle_count}", (10, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

    # Show signal phase
    phase_color = (0, 255, 0) if phase == 'green' else ((0, 255, 255) if phase == 'yellow' else (0, 0, 255))
    phase_text = phase.upper()
    cv2.putText(frame, phase_text, (width - 100, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, phase_color, 2)

    # Encode as JPEG
    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    return buffer.tobytes()


def _current_lane_frame(lane: str) -> bytes:
    """Return the JPEG frame to serve for ``lane``.

    Prefers the live YOLO-annotated feed in video mode; falls back to the
    synthetic generator when in demo mode (or before any frames are ready).
    """
    detector = app_state.get('detector')
    if detector is not None:
        live = detector.get_latest_jpeg(lane)
        if live is not None:
            return live

    simulation = app_state.get('simulation')
    if simulation is not None and hasattr(simulation, 'get_snapshot'):
        try:
            snapshot = simulation.get_snapshot()
            lane_data = snapshot.get('lanes', {}).get(lane, {})
            return generate_demo_frame(
                lane,
                lane_data.get('vehicle_count', 0),
                lane_data.get('phase', 'red'),
                lane_data.get('queue', 0),
            )
        except Exception:
            pass
    return generate_placeholder_frame(lane)


async def generate_mjpeg_stream(lane: str):
    """Generate MJPEG stream for a lane (live YOLO feed or synthetic fallback)."""
    import asyncio
    is_video = app_state.get('detector') is not None
    interval = 0.05 if is_video else 0.5  # ~20 FPS for real video, 2 FPS for synthetic
    while True:
        frame_bytes = _current_lane_frame(lane)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        await asyncio.sleep(interval)


@router.get("/{lane}")
async def video_stream(lane: str):
    """
    MJPEG video stream endpoint for a specific lane.

    Args:
        lane: Lane direction (N, S, E, W)

    Returns:
        MJPEG stream
    """
    # Validate lane
    if lane not in ['N', 'S', 'E', 'W']:
        raise HTTPException(status_code=400, detail="Invalid lane. Must be N, S, E, or W")

    return StreamingResponse(
        generate_mjpeg_stream(lane),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@router.get("/violation/stream")
async def violation_stream():
    """MJPEG stream of the violation camera (video mode only)."""
    vd = app_state.get('violation_detector')
    if vd is None:
        raise HTTPException(status_code=400, detail="Violation feed requires DETECTION_MODE=video")

    async def gen():
        import asyncio
        while True:
            frame = vd.get_latest_jpeg()
            if frame is not None:
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            await asyncio.sleep(0.05)

    return StreamingResponse(gen(), media_type="multipart/x-mixed-replace; boundary=frame")


@router.get("/{lane}/snapshot")
async def video_snapshot(lane: str):
    """
    Get a single frame snapshot for a lane.

    Args:
        lane: Lane direction (N, S, E, W)

    Returns:
        JPEG image
    """
    # Validate lane
    if lane not in ['N', 'S', 'E', 'W']:
        raise HTTPException(status_code=400, detail="Invalid lane. Must be N, S, E, or W")

    return StreamingResponse(io.BytesIO(_current_lane_frame(lane)), media_type="image/jpeg")
