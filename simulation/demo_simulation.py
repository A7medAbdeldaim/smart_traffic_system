"""Demo simulation module for generating realistic fake traffic data"""
import random
import math
from datetime import datetime
from typing import Dict, List
from .config import sim_config


class DemoSimulation:
    """Generates realistic traffic simulation data without SUMO"""

    def __init__(self):
        self.step_count = 0
        self.current_phase = 0  # 0=N/S green, 1=N/S yellow, 2=E/W green, 3=E/W yellow
        self.phase_remaining = sim_config.min_green
        self.lanes = ['N', 'S', 'E', 'W']

        # Lane-specific multipliers (some lanes naturally busier)
        self.lane_multipliers = {
            'N': 1.2,
            'S': 1.1,
            'E': 0.9,
            'W': 0.8
        }

        # Vehicle type distribution (percentages)
        self.vehicle_dist = {
            'car': 0.70,
            'truck': 0.15,
            'bus': 0.10,
            'motorcycle': 0.05
        }

        # Simple count tracking - vehicles in each lane
        self.vehicle_counts = {
            'N': random.randint(8, 15),
            'S': random.randint(8, 15),
            'E': random.randint(8, 15),
            'W': random.randint(8, 15)
        }

        # Green time allocations (set by optimizer)
        self.green_times = {
            'N': sim_config.min_green,
            'S': sim_config.min_green,
            'E': sim_config.min_green,
            'W': sim_config.min_green
        }

        print("✓ Demo simulation initialized")

    def start(self):
        """Start the demo simulation"""
        self.step_count = 0
        print("✓ Demo simulation started")

    def step(self) -> Dict[str, Dict]:
        """Advance simulation by one step and return lane metrics"""
        self.step_count += 1

        # Decrement phase timer
        self.phase_remaining -= 1
        if self.phase_remaining <= 0:
            self._next_phase()

        # Update vehicle counts for each lane
        for lane in self.lanes:
            self._update_lane_count(lane)

        # Generate traffic data for each lane
        lane_data = {}
        for lane in self.lanes:
            lane_data[lane] = self._generate_lane_data(lane)

        return lane_data

    def _get_arrival_rate(self, lane: str) -> float:
        """Calculate vehicle arrival rate (vehicles per second)"""
        # Time-based traffic pattern (sinusoidal - simulates rush hour)
        time_factor = math.sin(self.step_count / 120.0) * 0.5 + 0.5

        # Faster arrival: 0.3 to 1.2 vehicles/second
        base_rate = 0.3 + (0.9 * time_factor)

        # Apply lane multiplier
        lane_rate = base_rate * self.lane_multipliers[lane]

        return lane_rate

    def _update_lane_count(self, lane: str):
        """Update vehicle count: arrivals and departures"""
        is_green = self._is_green_for_lane(lane)
        before = self.vehicle_counts[lane]

        # Arrivals (always happening) - slower rate
        arrival_rate = self._get_arrival_rate(lane)
        if random.random() < arrival_rate:
            self.vehicle_counts[lane] += 1

        # Departures: FIXED 5 cars per second when green
        if is_green and self.vehicle_counts[lane] > 0:
            # Remove exactly 5 vehicles per second (guaranteed)
            to_remove = min(5, self.vehicle_counts[lane])
            self.vehicle_counts[lane] -= to_remove

            # Debug log every 60 steps
            if self.step_count % 60 == 0:
                print(f"  Lane {lane}: {before} → {self.vehicle_counts[lane]} (removed {to_remove}, green)")

        # Keep count reasonable (max 100 per lane)
        self.vehicle_counts[lane] = min(100, self.vehicle_counts[lane])

    def _generate_random_vehicle(self) -> str:
        """Generate random vehicle type"""
        rand = random.random()
        if rand < self.vehicle_dist['car']:
            return 'car'
        elif rand < self.vehicle_dist['car'] + self.vehicle_dist['truck']:
            return 'truck'
        elif rand < self.vehicle_dist['car'] + self.vehicle_dist['truck'] + self.vehicle_dist['bus']:
            return 'bus'
        else:
            return 'motorcycle'

    def _generate_lane_data(self, lane: str) -> Dict:
        """Generate realistic traffic data for a lane"""
        vehicle_count = self.vehicle_counts[lane]

        # Generate vehicle type breakdown
        counts = {
            'car': 0,
            'truck': 0,
            'bus': 0,
            'motorcycle': 0,
            'total': vehicle_count
        }

        # Distribute vehicles by type
        for _ in range(vehicle_count):
            vehicle_type = self._generate_random_vehicle()
            counts[vehicle_type] += 1

        # Calculate density score (weighted by vehicle type)
        density = (
            counts['car'] * 1.0 +
            counts['truck'] * 2.5 +
            counts['bus'] * 3.0 +
            counts['motorcycle'] * 0.5
        )

        # Determine current phase for this lane
        is_green = self._is_green_for_lane(lane)

        # Speed depends on signal phase and congestion
        if is_green:
            # Speed decreases with density
            max_speed = 50.0  # km/h
            congestion_factor = min(1.0, vehicle_count / 40.0)
            avg_speed = max_speed * (1.0 - congestion_factor * 0.6)
            avg_speed += random.uniform(-5, 5)
            avg_speed = max(0, min(max_speed, avg_speed))
        else:
            # Red light - vehicles are stopped or slow
            avg_speed = random.uniform(0, 5)

        # Queue length (vehicles waiting at stop line)
        if is_green:
            # Some vehicles still queued, rest are moving
            queue = int(vehicle_count * 0.3 * random.uniform(0.5, 1.0))
        else:
            # Most/all vehicles are queued when red
            queue = int(vehicle_count * 0.9 * random.uniform(0.9, 1.0))
        queue = max(0, min(vehicle_count, queue))

        # Waiting time (higher when red or congested)
        if is_green:
            waiting_time = queue * random.uniform(2, 5)
        else:
            waiting_time = vehicle_count * random.uniform(8, 15)

        return {
            'vehicle_count': vehicle_count,
            'counts': counts,
            'density': density,
            'speed': avg_speed,
            'queue': queue,
            'waiting_time': waiting_time,
            'phase': 'green' if is_green else ('yellow' if self.current_phase in [1, 3] else 'red'),
            'remaining': self.phase_remaining
        }

    def _is_green_for_lane(self, lane: str) -> bool:
        """Check if a lane has green light"""
        if self.current_phase == 0:  # N/S green
            return lane in ['N', 'S']
        elif self.current_phase == 2:  # E/W green
            return lane in ['E', 'W']
        else:  # Yellow phases
            return False

    def _next_phase(self):
        """Move to next traffic light phase"""
        self.current_phase = (self.current_phase + 1) % 4

        if self.current_phase in [1, 3]:  # Yellow phases
            self.phase_remaining = sim_config.yellow_time
        else:  # Green phases
            # Use optimized green times
            if self.current_phase == 0:  # N/S green
                self.phase_remaining = max(self.green_times['N'], self.green_times['S'])
            elif self.current_phase == 2:  # E/W green
                self.phase_remaining = max(self.green_times['E'], self.green_times['W'])

    def set_green_times(self, green_times: Dict[str, int]):
        """Update green time allocations from optimizer"""
        self.green_times.update(green_times)

    def set_phase(self, phase_index: int):
        """Set traffic light phase (0-3)"""
        self.current_phase = phase_index % 4

    def set_phase_duration(self, seconds: int):
        """Set duration for current phase"""
        self.phase_remaining = seconds

    def get_snapshot(self) -> Dict:
        """Get current simulation state"""
        lane_data = {}
        for lane in self.lanes:
            lane_data[lane] = self._generate_lane_data(lane)

        return {
            'timestamp': datetime.now().isoformat(),
            'step': self.step_count,
            'phase': self.current_phase,
            'lanes': lane_data
        }

    def stop(self):
        """Stop the simulation"""
        print("✓ Demo simulation stopped")

    def inject_emergency(self, lane: str) -> bool:
        """Simulate an emergency vehicle on a lane"""
        print(f"⚠️  Emergency vehicle injected on lane {lane}")
        return True


# Global instance for demo mode
demo_sim = DemoSimulation()
