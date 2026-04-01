"""Signal timing optimizer using density-weighted proportional allocation"""
from typing import Dict, List, Tuple
from .config import opt_config


class SignalOptimizer:
    """Optimizes traffic signal timing based on vehicle density"""

    def __init__(self):
        self.min_green = opt_config.min_green
        self.max_green = opt_config.max_green
        self.yellow_time = opt_config.yellow_time
        self.cycle_time = opt_config.cycle_time

        self.vehicle_weights = {
            'car': opt_config.car_weight,
            'truck': opt_config.truck_weight,
            'bus': opt_config.bus_weight,
            'motorcycle': opt_config.motorcycle_weight
        }

        print("✓ Signal optimizer initialized")

    def calculate_density_score(self, counts: Dict[str, int]) -> float:
        """
        Calculate weighted density score for a lane.

        Args:
            counts: Dictionary with vehicle counts by type
                   e.g., {'car': 12, 'truck': 3, 'bus': 1, 'motorcycle': 2}

        Returns:
            Weighted density score
        """
        score = 0.0
        for vehicle_type, weight in self.vehicle_weights.items():
            count = counts.get(vehicle_type, 0)
            score += count * weight

        return score

    def optimize_green_times(self, lane_data: Dict[str, Dict]) -> Dict[str, int]:
        """
        Calculate optimal green time for each lane based on density.

        Algorithm:
        1. Calculate density score for each lane
        2. Calculate total density across all lanes
        3. Allocate green time proportionally to density
        4. Clamp to min/max green time constraints

        Args:
            lane_data: Dictionary mapping lane to data
                      e.g., {'N': {'counts': {...}, 'density': 24.5}, ...}

        Returns:
            Dictionary mapping lane to green time in seconds
        """
        # Calculate density scores
        density_scores = {}
        for lane, data in lane_data.items():
            # Use pre-calculated density if available
            if 'density' in data:
                density_scores[lane] = data['density']
            else:
                # Calculate from counts
                counts = data.get('counts', {})
                density_scores[lane] = self.calculate_density_score(counts)

        total_density = sum(density_scores.values())

        # If no traffic, use equal distribution
        if total_density == 0:
            equal_time = self.min_green
            return {lane: equal_time for lane in lane_data.keys()}

        # Calculate available time for distribution
        # Total cycle minus minimum greens and yellow times
        num_lanes = len(lane_data)
        reserved_time = (num_lanes * self.min_green) + (num_lanes * self.yellow_time)
        available_time = self.cycle_time - reserved_time

        # Allocate green time proportionally
        green_times = {}
        for lane, density in density_scores.items():
            # Proportional allocation
            proportion = density / total_density
            allocated_time = self.min_green + (available_time * proportion)

            # Clamp to constraints
            green_time = max(self.min_green, min(self.max_green, int(allocated_time)))
            green_times[lane] = green_time

        return green_times

    def optimize_paired_lanes(self, lane_data: Dict[str, Dict]) -> List[Tuple[List[str], int]]:
        """
        Optimize green times for paired lanes (N-S and E-W).

        Args:
            lane_data: Lane traffic data

        Returns:
            List of (lane_group, green_time) tuples
            e.g., [(['N', 'S'], 45), (['E', 'W'], 35)]
        """
        # Calculate green times for individual lanes
        individual_times = self.optimize_green_times(lane_data)

        # Pair opposite lanes (N-S and E-W)
        ns_time = max(individual_times.get('N', self.min_green),
                     individual_times.get('S', self.min_green))
        ew_time = max(individual_times.get('E', self.min_green),
                     individual_times.get('W', self.min_green))

        # Ensure cycle time constraint
        total_green = ns_time + ew_time
        total_yellow = 2 * self.yellow_time  # Two yellow phases
        total_time = total_green + total_yellow

        # If exceeds cycle time, scale down proportionally
        if total_time > self.cycle_time:
            available_green = self.cycle_time - total_yellow
            scale_factor = available_green / total_green
            ns_time = int(ns_time * scale_factor)
            ew_time = int(ew_time * scale_factor)

        return [
            (['N', 'S'], ns_time),
            (['E', 'W'], ew_time)
        ]

    def calculate_phase_sequence(self, lane_data: Dict[str, Dict]) -> List[Dict]:
        """
        Generate complete phase sequence for a cycle.

        Returns:
            List of phase dictionaries with lanes, duration, and phase type
        """
        paired_times = self.optimize_paired_lanes(lane_data)
        phases = []

        for lane_group, green_time in paired_times:
            # Green phase
            phases.append({
                'lanes': lane_group,
                'phase': 'green',
                'duration': green_time
            })

            # Yellow phase
            phases.append({
                'lanes': lane_group,
                'phase': 'yellow',
                'duration': self.yellow_time
            })

        return phases

    def get_improvement_estimate(
        self,
        optimized_wait: float,
        baseline_wait: float = 45.0
    ) -> float:
        """
        Calculate percentage improvement over baseline (fixed timer).

        Args:
            optimized_wait: Average wait time with AI optimization
            baseline_wait: Average wait time with fixed 30s cycles

        Returns:
            Improvement percentage
        """
        if baseline_wait == 0:
            return 0.0

        improvement = ((baseline_wait - optimized_wait) / baseline_wait) * 100
        return max(0, improvement)  # Don't show negative improvement


# Global instance
signal_optimizer = SignalOptimizer()
