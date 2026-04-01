"""
Run baseline evaluation with fixed timer (30s per phase)
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulation import demo_sim
from database import db_manager


async def run_baseline(duration_minutes: int = 30):
    """
    Run simulation with fixed 30-second timer for all lanes.

    Args:
        duration_minutes: How long to run the simulation
    """
    print("=" * 60)
    print("BASELINE EVALUATION - Fixed Timer (30s)")
    print("=" * 60 + "\n")

    # Initialize
    await db_manager.initialize()
    intersection_id = await db_manager.setup_default_intersection()

    demo_sim.start()

    # Fixed timer configuration
    FIXED_GREEN_TIME = 30
    YELLOW_TIME = 4

    # Phase sequence: N-S green, N-S yellow, E-W green, E-W yellow
    phases = [
        ({'N': 'green', 'S': 'green', 'E': 'red', 'W': 'red'}, FIXED_GREEN_TIME),
        ({'N': 'yellow', 'S': 'yellow', 'E': 'red', 'W': 'red'}, YELLOW_TIME),
        ({'N': 'red', 'S': 'red', 'E': 'green', 'W': 'green'}, FIXED_GREEN_TIME),
        ({'N': 'red', 'S': 'red', 'E': 'yellow', 'W': 'yellow'}, YELLOW_TIME)
    ]

    current_phase = 0
    phase_remaining = phases[0][1]

    # Metrics collection
    total_wait_times = []
    total_vehicles = 0
    start_time = datetime.now()
    end_time = start_time + timedelta(minutes=duration_minutes)

    print(f"Running for {duration_minutes} minutes...\n")

    cycle = 0
    while datetime.now() < end_time:
        cycle += 1

        # Get simulation data
        lane_data = demo_sim.step()

        # Apply current phase
        phase_config, _ = phases[current_phase]
        for lane, phase in phase_config.items():
            await db_manager.update_signal_state(
                intersection_id=intersection_id,
                lane=lane,
                phase=phase,
                duration=phases[current_phase][1],
                remaining=phase_remaining
            )

        # Collect metrics
        for lane, data in lane_data.items():
            total_wait_times.append(data.get('waiting_time', 0))
            total_vehicles += data.get('vehicle_count', 0)

            # Log to database every 10 cycles
            if cycle % 10 == 0:
                await db_manager.log_traffic_data(
                    intersection_id=intersection_id,
                    lane=lane,
                    counts=data.get('counts', {}),
                    metrics={
                        'density': data.get('density', 0.0),
                        'speed': data.get('speed', 0.0),
                        'queue': data.get('queue', 0),
                        'waiting_time': data.get('waiting_time', 0.0)
                    },
                    green_time=FIXED_GREEN_TIME
                )

        # Progress indicator
        if cycle % 60 == 0:
            elapsed = (datetime.now() - start_time).total_seconds() / 60
            print(f"  {elapsed:.1f} min | Avg wait: {sum(total_wait_times) / len(total_wait_times):.1f}s | "
                  f"Vehicles: {total_vehicles}")

        # Advance phase timer
        phase_remaining -= 1
        if phase_remaining <= 0:
            current_phase = (current_phase + 1) % len(phases)
            phase_remaining = phases[current_phase][1]

        await asyncio.sleep(1.0)

    # Calculate final metrics
    avg_wait_time = sum(total_wait_times) / len(total_wait_times) if total_wait_times else 0

    print("\n" + "=" * 60)
    print("BASELINE RESULTS")
    print("=" * 60)
    print(f"Total Duration:        {duration_minutes} minutes")
    print(f"Total Vehicles:        {total_vehicles}")
    print(f"Average Wait Time:     {avg_wait_time:.2f} seconds")
    print(f"Throughput:            {total_vehicles / duration_minutes:.1f} vehicles/min")
    print("=" * 60 + "\n")

    # Save results
    results = {
        'mode': 'baseline',
        'duration_minutes': duration_minutes,
        'avg_wait_time': avg_wait_time,
        'total_vehicles': total_vehicles,
        'throughput': total_vehicles / duration_minutes
    }

    import json
    with open('evaluation/baseline_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    print("✓ Results saved to evaluation/baseline_results.json\n")

    # Cleanup
    demo_sim.stop()
    await db_manager.close()


if __name__ == "__main__":
    asyncio.run(run_baseline(duration_minutes=30))
