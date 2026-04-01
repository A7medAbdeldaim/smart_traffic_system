"""Emergency vehicle preemption handler"""
from typing import Optional, Dict
from datetime import datetime
from .config import opt_config


class EmergencyHandler:
    """Handles emergency vehicle detection and signal preemption"""

    def __init__(self):
        self.override_duration = opt_config.emergency_override_duration
        self.response_threshold = opt_config.emergency_response_time_threshold

        self.active_emergency = None  # {'lane': 'N', 'start_time': datetime, 'event_id': int}
        self.emergency_start_time = None

        print("✓ Emergency handler initialized")

    def trigger_emergency(self, lane: str, vehicle_type: str = 'ambulance') -> Dict:
        """
        Trigger emergency preemption for a lane.

        Args:
            lane: Lane direction (N, S, E, W)
            vehicle_type: Type of emergency vehicle

        Returns:
            Emergency response details
        """
        if self.active_emergency:
            # Already handling an emergency
            return {
                'success': False,
                'reason': f'Emergency already active on lane {self.active_emergency["lane"]}',
                'lane': lane
            }

        self.emergency_start_time = datetime.now()
        self.active_emergency = {
            'lane': lane,
            'vehicle_type': vehicle_type,
            'start_time': self.emergency_start_time,
            'event_id': None  # Will be set when logged to database
        }

        print(f"🚨 Emergency activated: {vehicle_type} on lane {lane}")

        return {
            'success': True,
            'lane': lane,
            'vehicle_type': vehicle_type,
            'action': f'green_override_{lane}',
            'duration': self.override_duration
        }

    def get_emergency_signal_override(self) -> Optional[Dict]:
        """
        Get signal override instructions during emergency.

        Returns:
            Dictionary with lanes and their forced phases, or None if no active emergency
        """
        if not self.active_emergency:
            return None

        emergency_lane = self.active_emergency['lane']

        # Set emergency lane to green, all others to red
        override = {}
        for lane in ['N', 'S', 'E', 'W']:
            if lane == emergency_lane:
                override[lane] = {
                    'phase': 'green',
                    'duration': self.override_duration,
                    'emergency': True
                }
            else:
                override[lane] = {
                    'phase': 'red',
                    'duration': self.override_duration,
                    'emergency': False
                }

        return override

    def check_emergency_timeout(self) -> bool:
        """
        Check if emergency override should end.

        Returns:
            True if emergency should be cleared
        """
        if not self.active_emergency:
            return False

        elapsed = (datetime.now() - self.active_emergency['start_time']).total_seconds()
        return elapsed >= self.override_duration

    def clear_emergency(self) -> Optional[Dict]:
        """
        Clear active emergency and return summary.

        Returns:
            Emergency summary or None if no active emergency
        """
        if not self.active_emergency:
            return None

        summary = {
            'lane': self.active_emergency['lane'],
            'vehicle_type': self.active_emergency['vehicle_type'],
            'duration': (datetime.now() - self.active_emergency['start_time']).total_seconds(),
            'event_id': self.active_emergency.get('event_id')
        }

        print(f"✓ Emergency cleared: lane {summary['lane']}")

        self.active_emergency = None
        self.emergency_start_time = None

        return summary

    def is_emergency_active(self) -> bool:
        """Check if emergency is currently active"""
        return self.active_emergency is not None

    def get_active_emergency_lane(self) -> Optional[str]:
        """Get the lane with active emergency, or None"""
        if self.active_emergency:
            return self.active_emergency['lane']
        return None

    def set_event_id(self, event_id: int):
        """Set database event ID for active emergency"""
        if self.active_emergency:
            self.active_emergency['event_id'] = event_id

    def get_response_time_ms(self) -> int:
        """Get response time in milliseconds since emergency detection"""
        if not self.emergency_start_time:
            return 0

        elapsed = (datetime.now() - self.emergency_start_time).total_seconds()
        return int(elapsed * 1000)


# Global instance
emergency_handler = EmergencyHandler()
