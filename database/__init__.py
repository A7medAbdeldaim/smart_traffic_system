"""Database module for Smart Traffic Control System"""
from .manager import DatabaseManager, db_manager
from .models import (
    Base,
    Intersection,
    Camera,
    TrafficSignal,
    TrafficDataLog,
    EmergencyEvent
)
from .config import db_config

__all__ = [
    'DatabaseManager',
    'db_manager',
    'Base',
    'Intersection',
    'Camera',
    'TrafficSignal',
    'TrafficDataLog',
    'EmergencyEvent',
    'db_config'
]
