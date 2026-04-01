"""
Run AI-optimized evaluation
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulation import demo_sim
from optimizer import signal_optimizer
from database import db_manager


async def run_ai_optimized(duration_minutes: int = 30):
    """
    Run simulation with AI-optimized signal timing.

    Args:
        duration_minutes: How long to run the simulation
    """
    print("=" * 60)
    print("AI EVALUATION - Optimized Timing")
    print("=" * 60 + "\n")

    # Initialize
    await db_manager.initialize()
    intersection_id = await db_manager.setup_default_intersection()

    demo_sim.start()

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

        # Calculate optimal green times
        green_times = signal_optimizer.optimize_green_times(lane_data)

        # Apply optimized timings (simplified - just update states)
        for lane, data in lane_data.items():
            phase = data.get('phase', 'red')
            remaining = data.get('remaining', 0)

            await db_manager.update_signal_state(
                intersection_id=intersection_id,
                lane=lane,
                phase=phase,
                duration=green_times.get(lane, 30),
                remaining=remaining
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
                    green_time=green_times.get(lane, 0)
                )

        # Progress indicator
        if cycle % 60 == 0:
            elapsed = (datetime.now() - start_time).total_seconds() / 60
            avg_wait = sum(total_wait_times) / len(total_wait_times) if total_wait_times else 0
            print(f"  {elapsed:.1f} min | Avg wait: {avg_wait:.1f}s | Vehicles: {total_vehicles}")

        await asyncio.sleep(1.0)

    # Calculate final metrics
    avg_wait_time = sum(total_wait_times) / len(total_wait_times) if total_wait_times else 0

    print("\n" + "=" * 60)
    print("AI-OPTIMIZED RESULTS")
    print("=" * 60)
    print(f"Total Duration:        {duration_minutes} minutes")
    print(f"Total Vehicles:        {total_vehicles}")
    print(f"Average Wait Time:     {avg_wait_time:.2f} seconds")
    print(f"Throughput:            {total_vehicles / duration_minutes:.1f} vehicles/min")
    print("=" * 60 + "\n")

    # Save results
    results = {
        'mode': 'ai_optimized',
        'duration_minutes': duration_minutes,
        'avg_wait_time': avg_wait_time,
        'total_vehicles': total_vehicles,
        'throughput': total_vehicles / duration_minutes
    }

    import json
    with open('evaluation/ai_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    print("✓ Results saved to evaluation/ai_results.json\n")

    # Cleanup
    demo_sim.stop()
    await db_manager.close()


if __name__ == "__main__":
    asyncio.run(run_ai_optimized(duration_minutes=30))
