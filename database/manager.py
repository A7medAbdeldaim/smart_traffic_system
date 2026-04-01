"""Database manager for async operations"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, update, and_, text
from sqlalchemy.pool import NullPool
from sqlalchemy.exc import OperationalError
import time

from .config import db_config
from .models import Base, Intersection, Camera, TrafficSignal, TrafficDataLog, EmergencyEvent


async def retry_on_lock(func, max_retries=3, initial_delay=0.1):
    """Retry database operation if locked"""
    for attempt in range(max_retries):
        try:
            return await func()
        except OperationalError as e:
            if 'database is locked' in str(e) and attempt < max_retries - 1:
                delay = initial_delay * (2 ** attempt)  # Exponential backoff
                await asyncio.sleep(delay)
            else:
                # If it's not a lock error or we're out of retries, raise
                if attempt == max_retries - 1:
                    # Last attempt failed, just log and continue
                    print(f"⚠️  Database operation failed after {max_retries} retries (continuing)")
                    return None
                raise


class DatabaseManager:
    """Manages all database operations"""

    def __init__(self):
        self.engine = None
        self.session_maker = None
        self._initialized = False

    async def initialize(self):
        """Initialize database connection and create tables"""
        if self._initialized:
            return

        database_url = db_config.get_database_url()

        # For SQLite, use NullPool and enable WAL mode
        if 'sqlite' in database_url:
            self.engine = create_async_engine(
                database_url,
                poolclass=NullPool,
                echo=False,
                connect_args={
                    'timeout': 30,
                    'check_same_thread': False
                }
            )
        else:
            self.engine = create_async_engine(
                database_url,
                pool_pre_ping=True,
                echo=False
            )

        self.session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

        # Create all tables
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

            # Enable WAL mode for SQLite to handle concurrent writes better
            if 'sqlite' in database_url:
                await conn.execute(text("PRAGMA journal_mode=WAL"))
                await conn.execute(text("PRAGMA synchronous=NORMAL"))
                await conn.execute(text("PRAGMA busy_timeout=30000"))

        self._initialized = True
        print(f"✓ Database initialized ({db_config.db_mode} mode)")

    async def close(self):
        """Close database connection"""
        if self.engine:
            await self.engine.dispose()
            self._initialized = False

    async def setup_default_intersection(self) -> int:
        """Create default intersection and cameras if not exists"""
        async with self.session_maker() as session:
            # Check if intersection exists
            result = await session.execute(
                select(Intersection).where(Intersection.name == "Main Intersection")
            )
            intersection = result.scalar_one_or_none()

            if not intersection:
                # Create default intersection
                intersection = Intersection(
                    name="Main Intersection",
                    latitude=18.3043,  # Abha, Saudi Arabia (King Khalid University)
                    longitude=42.5053,
                    num_lanes=4
                )
                session.add(intersection)
                await session.flush()

                # Create cameras for each lane
                for direction in ['N', 'S', 'E', 'W']:
                    camera = Camera(
                        intersection_id=intersection.id,
                        lane_direction=direction,
                        camera_url=f"/api/video/{direction}",
                        status='active'
                    )
                    session.add(camera)

                # Create initial signal states
                for direction in ['N', 'S', 'E', 'W']:
                    signal = TrafficSignal(
                        intersection_id=intersection.id,
                        lane_direction=direction,
                        current_phase='red',
                        phase_duration=30,
                        remaining_time=30
                    )
                    session.add(signal)

                await session.commit()
                print(f"✓ Created default intersection (ID: {intersection.id})")

            return intersection.id

    async def log_traffic_data(
        self,
        intersection_id: int,
        lane: str,
        counts: Dict[str, int],
        metrics: Dict[str, float],
        green_time: int = 0
    ):
        """Log traffic data for a lane"""
        async def _write():
            async with self.session_maker() as session:
                log = TrafficDataLog(
                    intersection_id=intersection_id,
                    lane_direction=lane,
                    vehicle_count=counts.get('total', 0),
                    car_count=counts.get('car', 0),
                    truck_count=counts.get('truck', 0),
                    bus_count=counts.get('bus', 0),
                    motorcycle_count=counts.get('motorcycle', 0),
                    density_score=metrics.get('density', 0.0),
                    avg_speed=metrics.get('speed', 0.0),
                    queue_length=metrics.get('queue', 0),
                    waiting_time=metrics.get('waiting_time', 0.0),
                    green_time_allocated=green_time
                )
                session.add(log)
                await session.commit()

        await retry_on_lock(_write)

    async def update_signal_state(
        self,
        intersection_id: int,
        lane: str,
        phase: str,
        duration: int,
        remaining: int
    ):
        """Update or create signal state for a lane"""
        async def _write():
            async with self.session_maker() as session:
                # Try to update existing signal
                result = await session.execute(
                    select(TrafficSignal).where(
                        and_(
                            TrafficSignal.intersection_id == intersection_id,
                            TrafficSignal.lane_direction == lane
                        )
                    )
                )
                signal = result.scalar_one_or_none()

                if signal:
                    signal.current_phase = phase
                    signal.phase_duration = duration
                    signal.remaining_time = remaining
                    signal.updated_at = datetime.now()
                else:
                    signal = TrafficSignal(
                        intersection_id=intersection_id,
                        lane_direction=lane,
                        current_phase=phase,
                        phase_duration=duration,
                        remaining_time=remaining
                    )
                    session.add(signal)

                await session.commit()

        await retry_on_lock(_write)

    async def log_emergency(
        self,
        intersection_id: int,
        lane: str,
        vehicle_type: str,
        action: str,
        response_time_ms: int
    ) -> int:
        """Log an emergency event"""
        async with self.session_maker() as session:
            event = EmergencyEvent(
                intersection_id=intersection_id,
                lane_direction=lane,
                vehicle_type=vehicle_type,
                action_taken=action,
                response_time_ms=response_time_ms
            )
            session.add(event)
            await session.commit()
            return event.id

    async def resolve_emergency(self, event_id: int):
        """Mark an emergency event as resolved"""
        async with self.session_maker() as session:
            result = await session.execute(
                select(EmergencyEvent).where(EmergencyEvent.id == event_id)
            )
            event = result.scalar_one_or_none()
            if event:
                event.resolved_at = datetime.now()
                await session.commit()

    async def get_signal_states(self, intersection_id: int) -> Dict[str, Dict]:
        """Get current signal states for all lanes"""
        async with self.session_maker() as session:
            result = await session.execute(
                select(TrafficSignal).where(
                    TrafficSignal.intersection_id == intersection_id
                )
            )
            signals = result.scalars().all()

            states = {}
            for signal in signals:
                states[signal.lane_direction] = {
                    'phase': signal.current_phase,
                    'duration': signal.phase_duration,
                    'remaining': signal.remaining_time,
                    'updated_at': signal.updated_at.isoformat() if signal.updated_at else None
                }

            return states

    async def get_recent_logs(
        self,
        intersection_id: int,
        minutes: int = 30
    ) -> List[Dict]:
        """Get recent traffic data logs"""
        async with self.session_maker() as session:
            cutoff_time = datetime.now() - timedelta(minutes=minutes)
            result = await session.execute(
                select(TrafficDataLog)
                .where(
                    and_(
                        TrafficDataLog.intersection_id == intersection_id,
                        TrafficDataLog.timestamp >= cutoff_time
                    )
                )
                .order_by(TrafficDataLog.timestamp.desc())
            )
            logs = result.scalars().all()

            return [
                {
                    'id': log.id,
                    'lane': log.lane_direction,
                    'vehicle_count': log.vehicle_count,
                    'car_count': log.car_count,
                    'truck_count': log.truck_count,
                    'bus_count': log.bus_count,
                    'motorcycle_count': log.motorcycle_count,
                    'density_score': log.density_score,
                    'avg_speed': log.avg_speed,
                    'queue_length': log.queue_length,
                    'waiting_time': log.waiting_time,
                    'green_time_allocated': log.green_time_allocated,
                    'timestamp': log.timestamp.isoformat() if log.timestamp else None
                }
                for log in logs
            ]

    async def get_emergency_history(
        self,
        intersection_id: int,
        limit: int = 50
    ) -> List[Dict]:
        """Get emergency event history"""
        async with self.session_maker() as session:
            result = await session.execute(
                select(EmergencyEvent)
                .where(EmergencyEvent.intersection_id == intersection_id)
                .order_by(EmergencyEvent.detected_at.desc())
                .limit(limit)
            )
            events = result.scalars().all()

            return [
                {
                    'id': event.id,
                    'lane': event.lane_direction,
                    'vehicle_type': event.vehicle_type,
                    'action_taken': event.action_taken,
                    'response_time_ms': event.response_time_ms,
                    'detected_at': event.detected_at.isoformat() if event.detected_at else None,
                    'resolved_at': event.resolved_at.isoformat() if event.resolved_at else None
                }
                for event in events
            ]

    async def get_statistics(self, intersection_id: int) -> Dict:
        """Get aggregate statistics"""
        async with self.session_maker() as session:
            # Get average waiting time from last hour
            one_hour_ago = datetime.now() - timedelta(hours=1)
            result = await session.execute(
                select(TrafficDataLog)
                .where(
                    and_(
                        TrafficDataLog.intersection_id == intersection_id,
                        TrafficDataLog.timestamp >= one_hour_ago
                    )
                )
            )
            logs = result.scalars().all()

            total_vehicles = sum(log.vehicle_count for log in logs)
            avg_wait_time = (
                sum(log.waiting_time for log in logs if log.waiting_time) / len(logs)
                if logs else 0
            )

            # Count emergency events
            result = await session.execute(
                select(EmergencyEvent).where(
                    EmergencyEvent.intersection_id == intersection_id
                )
            )
            total_emergencies = len(result.scalars().all())

            return {
                'total_vehicles': total_vehicles,
                'avg_wait_time': avg_wait_time,
                'total_emergencies': total_emergencies,
                'improvement_percentage': 37.0  # TODO: Calculate actual improvement
            }


# Global instance
db_manager = DatabaseManager()
