"""REST API routes"""
from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime

from .schemas import (
    IntersectionStatus,
    LaneStatus,
    TrafficLog,
    EmergencyEvent,
    Statistics,
    EmergencyOverrideRequest,
    EmergencyOverrideResponse,
    SimulationControlResponse
)
from .app import app_state

router = APIRouter(prefix="/api", tags=["traffic"])


@router.get("/status", response_model=IntersectionStatus)
async def get_status():
    """Get current intersection status"""
    db_manager = app_state['db_manager']
    emergency_handler = app_state['emergency_handler']
    intersection_id = app_state['intersection_id']

    if not db_manager:
        raise HTTPException(status_code=503, detail="Database not initialized")

    # Get signal states from database
    signal_states = await db_manager.get_signal_states(intersection_id)

    # Get latest traffic data (use simulation snapshot or cached data)
    simulation = app_state['simulation']
    if simulation:
        snapshot = simulation.get_snapshot()
        lane_data = snapshot.get('lanes', {})
    else:
        lane_data = {}

    # Build lane status for each direction
    lanes = {}
    for direction in ['N', 'S', 'E', 'W']:
        signal = signal_states.get(direction, {})
        data = lane_data.get(direction, {})

        counts = data.get('counts', {})
        lanes[direction] = LaneStatus(
            phase=signal.get('phase', 'red'),
            remaining=signal.get('remaining', 0),
            vehicles=data.get('vehicle_count', 0),
            density=data.get('density', 0.0),
            queue=data.get('queue', 0),
            speed=data.get('speed', 0.0),
            car_count=counts.get('car', 0),
            truck_count=counts.get('truck', 0),
            bus_count=counts.get('bus', 0),
            motorcycle_count=counts.get('motorcycle', 0)
        )

    return IntersectionStatus(
        timestamp=datetime.now().isoformat(),
        lanes=lanes,
        emergency_active=emergency_handler.is_emergency_active() if emergency_handler else False,
        emergency_lane=emergency_handler.get_active_emergency_lane() if emergency_handler else None,
        mode=app_state['mode'],
        cycle_number=app_state['cycle_count']
    )


@router.get("/logs", response_model=List[TrafficLog])
async def get_logs(minutes: int = 30):
    """Get recent traffic data logs"""
    db_manager = app_state['db_manager']
    intersection_id = app_state['intersection_id']

    if not db_manager:
        raise HTTPException(status_code=503, detail="Database not initialized")

    logs = await db_manager.get_recent_logs(intersection_id, minutes)

    return [
        TrafficLog(
            id=log['id'],
            lane=log['lane'],
            vehicle_count=log['vehicle_count'],
            car_count=log['car_count'],
            truck_count=log['truck_count'],
            bus_count=log['bus_count'],
            motorcycle_count=log['motorcycle_count'],
            density_score=log['density_score'] or 0.0,
            avg_speed=log['avg_speed'] or 0.0,
            queue_length=log['queue_length'] or 0,
            waiting_time=log['waiting_time'] or 0.0,
            green_time_allocated=log['green_time_allocated'] or 0,
            timestamp=log['timestamp']
        )
        for log in logs
    ]


@router.get("/emergency/history", response_model=List[EmergencyEvent])
async def get_emergency_history(limit: int = 50):
    """Get emergency event history"""
    db_manager = app_state['db_manager']
    intersection_id = app_state['intersection_id']

    if not db_manager:
        raise HTTPException(status_code=503, detail="Database not initialized")

    events = await db_manager.get_emergency_history(intersection_id, limit)

    return [
        EmergencyEvent(
            id=event['id'],
            lane=event['lane'],
            vehicle_type=event['vehicle_type'] or 'unknown',
            action_taken=event['action_taken'] or '',
            response_time_ms=event['response_time_ms'] or 0,
            detected_at=event['detected_at'],
            resolved_at=event['resolved_at']
        )
        for event in events
    ]


@router.post("/emergency/override", response_model=EmergencyOverrideResponse)
async def emergency_override(request: EmergencyOverrideRequest):
    """Manually trigger emergency override for a lane"""
    emergency_handler = app_state['emergency_handler']
    db_manager = app_state['db_manager']
    intersection_id = app_state['intersection_id']

    if not emergency_handler:
        raise HTTPException(status_code=503, detail="Emergency handler not initialized")

    # Validate lane
    if request.lane not in ['N', 'S', 'E', 'W']:
        raise HTTPException(status_code=400, detail="Invalid lane. Must be N, S, E, or W")

    # Trigger emergency
    result = emergency_handler.trigger_emergency(request.lane, 'manual_override')

    if result['success']:
        # Log to database
        if db_manager:
            event_id = await db_manager.log_emergency(
                intersection_id=intersection_id,
                lane=request.lane,
                vehicle_type='manual_override',
                action=result['action'],
                response_time_ms=0
            )
            emergency_handler.set_event_id(event_id)

        return EmergencyOverrideResponse(
            success=True,
            lane=request.lane,
            message=f"Emergency override activated for lane {request.lane}"
        )
    else:
        return EmergencyOverrideResponse(
            success=False,
            lane=request.lane,
            message=result.get('reason', 'Failed to activate emergency override')
        )


@router.get("/stats", response_model=Statistics)
async def get_statistics():
    """Get aggregate statistics"""
    db_manager = app_state['db_manager']
    intersection_id = app_state['intersection_id']

    if not db_manager:
        raise HTTPException(status_code=503, detail="Database not initialized")

    stats = await db_manager.get_statistics(intersection_id)

    return Statistics(
        avg_wait_time=stats['avg_wait_time'],
        total_vehicles=stats['total_vehicles'],
        improvement_percentage=stats['improvement_percentage'],
        total_emergencies=stats['total_emergencies']
    )


@router.post("/simulation/start", response_model=SimulationControlResponse)
async def start_simulation():
    """Start the simulation"""
    simulation = app_state['simulation']

    if not simulation:
        raise HTTPException(status_code=503, detail="Simulation not available")

    try:
        simulation.start()
        return SimulationControlResponse(
            success=True,
            message="Simulation started"
        )
    except Exception as e:
        return SimulationControlResponse(
            success=False,
            message=f"Failed to start simulation: {str(e)}"
        )


@router.post("/simulation/stop", response_model=SimulationControlResponse)
async def stop_simulation():
    """Stop the simulation"""
    simulation = app_state['simulation']

    if not simulation:
        raise HTTPException(status_code=503, detail="Simulation not available")

    try:
        simulation.stop()
        return SimulationControlResponse(
            success=True,
            message="Simulation stopped"
        )
    except Exception as e:
        return SimulationControlResponse(
            success=False,
            message=f"Failed to stop simulation: {str(e)}"
        )


@router.post("/mode/toggle")
async def toggle_mode():
    """Toggle between AI optimized and fixed timer mode"""
    current_mode = app_state['mode']
    new_mode = 'fixed_timer' if current_mode == 'ai_optimized' else 'ai_optimized'
    app_state['mode'] = new_mode

    # Log the mode change
    mode_label = "FIXED" if new_mode == 'fixed_timer' else "AI"
    print(f"\n🔄 MODE CHANGED: {current_mode} → {new_mode} ({mode_label})\n")

    return {
        "success": True,
        "mode": new_mode,
        "message": f"Switched to {new_mode} mode"
    }


@router.post("/violation_detection/{action}")
async def toggle_violation_detection(action: str):
    """Enable or disable red-light violation capture (video mode only)."""
    vd = app_state.get('violation_detector')
    if vd is None:
        raise HTTPException(status_code=400, detail="Violation detection requires DETECTION_MODE=video")
    if action not in ('start', 'stop'):
        raise HTTPException(status_code=400, detail="action must be 'start' or 'stop'")
    vd.enabled = (action == 'start')
    print(f"🚨 Violation detection {'ENABLED' if vd.enabled else 'DISABLED'}")
    return {"success": True, "enabled": vd.enabled}


@router.get("/violations")
async def list_violations(limit: int = 50):
    """Recent red-light violations, newest first."""
    db = app_state.get('db_manager')
    if db is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    return {"violations": await db.get_violations(limit=limit)}


@router.post("/violations/{vid}/pay")
async def assign_fine(vid: int):
    db = app_state.get('db_manager')
    if db is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    ok = await db.mark_violation_paid(vid)
    if not ok:
        raise HTTPException(status_code=404, detail="Violation not found")
    return {"success": True, "id": vid, "status": "Paid"}


@router.post("/ambulance_detection/{action}")
async def toggle_ambulance_detection(action: str):
    """Enable or disable ambulance preemption (video mode only).

    Off by default — the bundled YOLO ambulance model has a high false-positive
    rate on ordinary traffic, so it must be explicitly turned on.
    """
    detector = app_state.get('detector')
    if detector is None:
        raise HTTPException(status_code=400, detail="Ambulance detection requires DETECTION_MODE=video")
    if action not in ('start', 'stop'):
        raise HTTPException(status_code=400, detail="action must be 'start' or 'stop'")
    detector.ambulance_detection_enabled = (action == 'start')
    print(f"🚑 Ambulance detection {'ENABLED' if detector.ambulance_detection_enabled else 'DISABLED'}")
    return {"success": True, "enabled": detector.ambulance_detection_enabled}
