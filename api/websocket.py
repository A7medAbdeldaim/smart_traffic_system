"""WebSocket endpoint for real-time updates"""
import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from datetime import datetime
from typing import Set

from .app import app_state

router = APIRouter(tags=["websocket"])

# Active WebSocket connections
active_connections: Set[WebSocket] = set()


class ConnectionManager:
    """Manages WebSocket connections"""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        """Accept and register a new connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        print(f"✓ WebSocket connected (total: {len(self.active_connections)})")

    def disconnect(self, websocket: WebSocket):
        """Remove a connection"""
        self.active_connections.discard(websocket)
        print(f"✓ WebSocket disconnected (total: {len(self.active_connections)})")

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            return

        # Convert to JSON
        message_json = json.dumps(message)

        # Send to all connections
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except Exception:
                # Mark for removal if send fails
                disconnected.add(connection)

        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    """
    WebSocket endpoint for live traffic data.
    Streams real-time updates every second.
    """
    await manager.connect(websocket)

    try:
        # Keep connection alive and send periodic updates
        while True:
            # Wait for next update cycle (handled by broadcast from main loop)
            # Just keep the connection alive
            try:
                # Receive ping/pong to keep connection alive
                await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
            except asyncio.TimeoutError:
                # Timeout is expected - continue
                pass

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)


async def broadcast_traffic_update():
    """
    Broadcast current traffic state to all connected clients.
    Called from main loop.
    """
    simulation = app_state['simulation']
    emergency_handler = app_state['emergency_handler']

    if not simulation:
        print("⚠️  No simulation available for broadcast")
        return

    # Get current simulation snapshot (use simulation data directly, not DB)
    snapshot = simulation.get_snapshot()
    lane_data = snapshot.get('lanes', {})

    if not lane_data:
        print("⚠️  No lane data in snapshot")
        return

    # Build update message using simulation data directly
    lanes = {}
    for direction in ['N', 'S', 'E', 'W']:
        data = lane_data.get(direction, {})

        lanes[direction] = {
            'phase': data.get('phase', 'red'),
            'remaining': data.get('remaining', 0),
            'vehicles': data.get('vehicle_count', 0),
            'density': data.get('density', 0.0),
            'queue': data.get('queue', 0),
            'speed': data.get('speed', 0.0),
            'car_count': data.get('counts', {}).get('car', 0),
            'truck_count': data.get('counts', {}).get('truck', 0),
            'bus_count': data.get('counts', {}).get('bus', 0),
            'motorcycle_count': data.get('counts', {}).get('motorcycle', 0)
        }

    message = {
        'timestamp': datetime.now().isoformat(),
        'lanes': lanes,
        'emergency_active': emergency_handler.is_emergency_active() if emergency_handler else False,
        'emergency_lane': emergency_handler.get_active_emergency_lane() if emergency_handler else None,
        'mode': app_state['mode'],
        'cycle_number': app_state.get('cycle_count', 0)
    }

    # Debug: print broadcast info
    total_vehicles = sum(lanes[d]['vehicles'] for d in ['N', 'S', 'E', 'W'])
    if app_state.get('cycle_count', 0) % 10 == 0:
        print(f"📡 Broadcasting: {total_vehicles} total vehicles, {len(manager.active_connections)} clients")

    # Broadcast to all connected clients
    await manager.broadcast(message)


# Export manager for use in main.py
__all__ = ['router', 'manager', 'broadcast_traffic_update']
