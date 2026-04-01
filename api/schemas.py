"""Pydantic schemas for API requests and responses"""
from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime


class LaneStatus(BaseModel):
    """Status of a single lane"""
    phase: str  # 'red', 'yellow', 'green'
    remaining: int  # seconds
    vehicles: int
    density: float
    queue: int
    speed: float
    car_count: int = 0
    truck_count: int = 0
    bus_count: int = 0
    motorcycle_count: int = 0


class IntersectionStatus(BaseModel):
    """Complete intersection status"""
    timestamp: str
    lanes: Dict[str, LaneStatus]
    emergency_active: bool
    emergency_lane: Optional[str] = None
    mode: str  # 'ai_optimized' or 'fixed_timer'
    cycle_number: int


class TrafficLog(BaseModel):
    """Traffic data log entry"""
    id: int
    lane: str
    vehicle_count: int
    car_count: int
    truck_count: int
    bus_count: int
    motorcycle_count: int
    density_score: float
    avg_speed: float
    queue_length: int
    waiting_time: float
    green_time_allocated: int
    timestamp: str


class EmergencyEvent(BaseModel):
    """Emergency event record"""
    id: int
    lane: str
    vehicle_type: str
    action_taken: str
    response_time_ms: int
    detected_at: str
    resolved_at: Optional[str] = None


class Statistics(BaseModel):
    """Aggregate statistics"""
    avg_wait_time: float
    total_vehicles: int
    improvement_percentage: float
    total_emergencies: int


class EmergencyOverrideRequest(BaseModel):
    """Request to trigger emergency override"""
    lane: str  # 'N', 'S', 'E', 'W'


class EmergencyOverrideResponse(BaseModel):
    """Response from emergency override"""
    success: bool
    lane: str
    message: str


class SimulationControlResponse(BaseModel):
    """Response from simulation control"""
    success: bool
    message: str
