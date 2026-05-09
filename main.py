"""
Smart Traffic Control System - Main Entry Point
King Khalid University Graduation Project

This system uses AI-based vehicle detection and optimization algorithms to
dynamically control traffic signals at a 4-way intersection.
"""

import asyncio
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import modules
from database import db_manager
from simulation import demo_sim
from optimizer import signal_optimizer, emergency_handler
from api import app, app_state, broadcast_traffic_update


def _select_traffic_source():
    """Pick the traffic data source: real video (YOLO) or synthetic demo.

    Defaults to 'video' for deployments. Override with DETECTION_MODE=demo
    only for local CPU-constrained dev or the evaluation scripts.
    """
    mode = os.getenv('DETECTION_MODE', 'video').lower()
    if mode == 'video':
        from detection import feed_manager
        print("🎥 Detection mode: VIDEO (YOLOv11 on .mp4 feeds)")
        return feed_manager, 'video'
    print("🎮 Detection mode: DEMO (synthetic generator)")
    return demo_sim, 'demo'


class TrafficControlSystem:
    """Main system coordinator"""

    def __init__(self):
        self.running = False
        self.intersection_id = None
        self.cycle_count = 0
        self.mode = os.getenv('DEMO_MODE', 'true').lower() == 'true'

        # Components
        self.db_manager = db_manager
        self.simulation, self.detection_mode = _select_traffic_source()
        self.optimizer = signal_optimizer
        self.emergency_handler = emergency_handler

    async def initialize(self):
        """Initialize all system components"""
        print("\n" + "=" * 60)
        print("🚦 SMART TRAFFIC CONTROL SYSTEM")
        print("   King Khalid University - Graduation Project")
        print("=" * 60 + "\n")

        # Initialize database
        print("📊 Initializing database...")
        await self.db_manager.initialize()

        # Setup default intersection
        print("🚥 Setting up intersection configuration...")
        self.intersection_id = await self.db_manager.setup_default_intersection()

        # Start simulation
        print(f"🎮 Starting simulation ({'DEMO' if self.mode else 'SUMO'} mode)...")
        self.simulation.start()

        # Inject app state
        app_state['db_manager'] = self.db_manager
        app_state['simulation'] = self.simulation
        app_state['optimizer'] = self.optimizer
        app_state['emergency_handler'] = self.emergency_handler
        app_state['intersection_id'] = self.intersection_id
        app_state['mode'] = 'ai_optimized'
        app_state['detection_mode'] = self.detection_mode
        # Expose detector + enable ambulance detection in video mode
        if self.detection_mode == 'video':
            app_state['detector'] = self.simulation
            from detection import enable_ambulance_detection
            enable_ambulance_detection(self.emergency_handler)

        print("\n" + "=" * 60)
        print("✅ System initialization complete!")
        print("=" * 60 + "\n")

    async def run_control_loop(self):
        """Main control loop - runs continuously"""
        self.running = True

        print("🔄 Starting traffic control loop...\n")

        while self.running:
            try:
                # Advance simulation
                lane_data = self.simulation.step()

                # Check for emergency timeout
                if self.emergency_handler.check_emergency_timeout():
                    summary = self.emergency_handler.clear_emergency()
                    if hasattr(self.simulation, 'clear_emergency_override'):
                        self.simulation.clear_emergency_override()
                    if summary and summary.get('event_id'):
                        await self.db_manager.resolve_emergency(summary['event_id'])

                # Determine signal timings (calculate but don't write to DB every cycle)
                if self.emergency_handler.is_emergency_active():
                    # Force the traffic source into the override (so MJPEG overlay
                    # and WebSocket broadcast both reflect the emergency state).
                    em_lane = self.emergency_handler.get_active_emergency_lane()
                    if em_lane and hasattr(self.simulation, 'apply_emergency_override'):
                        self.simulation.apply_emergency_override(
                            em_lane, self.emergency_handler.override_duration
                        )

                    # Emergency override
                    signal_override = self.emergency_handler.get_emergency_signal_override()
                    # Only update DB on emergency state changes, not every cycle
                    if self.cycle_count % 5 == 0 and signal_override:
                        for lane, config in signal_override.items():
                            await self.db_manager.update_signal_state(
                                intersection_id=self.intersection_id,
                                lane=lane,
                                phase=config['phase'],
                                duration=config['duration'],
                                remaining=config['duration']
                            )
                else:
                    # Normal optimization
                    if app_state['mode'] == 'ai_optimized':
                        # AI-optimized timing based on traffic density
                        green_times = self.optimizer.optimize_green_times(lane_data)
                        mode_label = "AI"
                    else:
                        # Fixed timer mode (30s for all lanes)
                        green_times = {lane: 30 for lane in lane_data.keys()}
                        mode_label = "FIXED"

                    # Update simulation with calculated green times
                    self.simulation.set_green_times(green_times)

                    # Log green time allocation every 30 cycles for visibility
                    if self.cycle_count % 30 == 0:
                        times_str = ' '.join([f"{lane}:{green_times.get(lane, 0)}s" for lane in ['N', 'S', 'E', 'W']])
                        print(f"🎛️  [{mode_label}] Green times: {times_str}")

                    # Apply signal timings only every 5 seconds to reduce DB load
                    if self.cycle_count % 5 == 0:
                        for lane, data in lane_data.items():
                            phase = data.get('phase', 'red')
                            remaining = data.get('remaining', 0)
                            duration = green_times.get(lane, 30)

                            await self.db_manager.update_signal_state(
                                intersection_id=self.intersection_id,
                                lane=lane,
                                phase=phase,
                                duration=duration,
                                remaining=remaining
                            )

                # Log traffic data every 10 cycles
                if self.cycle_count % 10 == 0:
                    for lane, data in lane_data.items():
                        await self.db_manager.log_traffic_data(
                            intersection_id=self.intersection_id,
                            lane=lane,
                            counts=data.get('counts', {}),
                            metrics={
                                'density': data.get('density', 0.0),
                                'speed': data.get('speed', 0.0),
                                'queue': data.get('queue', 0),
                                'waiting_time': data.get('waiting_time', 0.0)
                            },
                            green_time=green_times.get(lane, 0) if 'green_times' in locals() else 0
                        )

                # Broadcast update to WebSocket clients
                await broadcast_traffic_update()

                # Increment cycle count
                self.cycle_count += 1
                app_state['cycle_count'] = self.cycle_count

                # Print status every 30 cycles (~30 seconds)
                if self.cycle_count % 30 == 0:
                    print(f"⏱️  Cycle {self.cycle_count:4d} | ", end='')
                    for lane in ['N', 'S', 'E', 'W']:
                        data = lane_data.get(lane, {})
                        vehicles = data.get('vehicle_count', 0)
                        phase = data.get('phase', 'red')[0].upper()
                        print(f"{lane}:{vehicles:2d}[{phase}] ", end='')
                    print()

                # Wait 1 second before next cycle
                await asyncio.sleep(1.0)

            except Exception as e:
                print(f"❌ Error in control loop: {e}")
                import traceback
                traceback.print_exc()
                await asyncio.sleep(1.0)

    async def shutdown(self):
        """Graceful shutdown"""
        print("\n\n🛑 Shutting down system...")
        self.running = False

        # Stop simulation
        self.simulation.stop()

        # Close database
        await self.db_manager.close()

        print("✅ Shutdown complete")

    async def start_api_server(self):
        """Start FastAPI server"""
        config = uvicorn.Config(
            app,
            host=os.getenv('API_HOST', '0.0.0.0'),
            port=int(os.getenv('API_PORT', 8000)),
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()


async def main():
    """Main entry point"""
    system = TrafficControlSystem()

    try:
        # Initialize system
        await system.initialize()

        # Print access information
        port = int(os.getenv('API_PORT', 8000))
        print(f"🌐 Dashboard running at:")
        print(f"   • http://localhost:{port}")
        print(f"   • http://127.0.0.1:{port}")
        print(f"\n💡 Press Ctrl+C to stop\n")

        # Run control loop and API server concurrently
        await asyncio.gather(
            system.run_control_loop(),
            system.start_api_server()
        )

    except KeyboardInterrupt:
        print("\n\n⚠️  Received shutdown signal...")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await system.shutdown()


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
