"""SQLAlchemy ORM models for the traffic control system"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, ForeignKey, DateTime, Enum, DECIMAL
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Intersection(Base):
    """Intersection configuration table"""
    __tablename__ = 'intersections'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    latitude = Column(DECIMAL(10, 8))
    longitude = Column(DECIMAL(11, 8))
    num_lanes = Column(Integer, default=4)
    created_at = Column(DateTime, default=func.now())


class Camera(Base):
    """Camera configuration per lane"""
    __tablename__ = 'cameras'

    id = Column(Integer, primary_key=True, autoincrement=True)
    intersection_id = Column(Integer, ForeignKey('intersections.id'))
    lane_direction = Column(
        Enum('N', 'S', 'E', 'W', name='lane_direction_enum'),
        nullable=False
    )
    camera_url = Column(String(255))
    status = Column(
        Enum('active', 'inactive', 'error', name='camera_status_enum'),
        default='active'
    )


class TrafficSignal(Base):
    """Current signal state"""
    __tablename__ = 'traffic_signals'

    id = Column(Integer, primary_key=True, autoincrement=True)
    intersection_id = Column(Integer, ForeignKey('intersections.id'))
    lane_direction = Column(
        Enum('N', 'S', 'E', 'W', name='signal_lane_direction_enum'),
        nullable=False
    )
    current_phase = Column(
        Enum('red', 'yellow', 'green', name='signal_phase_enum'),
        nullable=False
    )
    phase_duration = Column(Integer, nullable=False)
    remaining_time = Column(Integer)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class TrafficDataLog(Base):
    """Historical traffic data logs"""
    __tablename__ = 'traffic_data_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    intersection_id = Column(Integer, ForeignKey('intersections.id'))
    lane_direction = Column(
        Enum('N', 'S', 'E', 'W', name='log_lane_direction_enum'),
        nullable=False
    )
    vehicle_count = Column(Integer, nullable=False)
    car_count = Column(Integer, default=0)
    truck_count = Column(Integer, default=0)
    bus_count = Column(Integer, default=0)
    motorcycle_count = Column(Integer, default=0)
    density_score = Column(Float)
    avg_speed = Column(Float)
    queue_length = Column(Integer)
    waiting_time = Column(Float)
    green_time_allocated = Column(Integer)
    timestamp = Column(DateTime, default=func.now())


class EmergencyEvent(Base):
    """Emergency vehicle events"""
    __tablename__ = 'emergency_events'

    id = Column(Integer, primary_key=True, autoincrement=True)
    intersection_id = Column(Integer, ForeignKey('intersections.id'))
    lane_direction = Column(
        Enum('N', 'S', 'E', 'W', name='emergency_lane_direction_enum'),
        nullable=False
    )
    vehicle_type = Column(String(50))
    action_taken = Column(String(100))
    response_time_ms = Column(Integer)
    detected_at = Column(DateTime, default=func.now())
    resolved_at = Column(DateTime, nullable=True)
