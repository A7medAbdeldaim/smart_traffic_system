"""FastAPI application for Smart Traffic Control System"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import os


# Global state will be injected from main.py
app_state = {
    'db_manager': None,
    'simulation': None,
    'optimizer': None,
    'emergency_handler': None,
    'intersection_id': 1,
    'cycle_count': 0,
    'mode': 'ai_optimized'  # or 'fixed_timer'
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    import asyncio
    from dotenv import load_dotenv

    # Load environment variables
    load_dotenv()

    # Startup
    print("✓ FastAPI application starting...")

    # Import and initialize system components
    try:
        from database import db_manager
        from simulation import demo_sim
        from optimizer import signal_optimizer, emergency_handler
        from api.websocket import broadcast_traffic_update

        print("\n" + "=" * 60)
        print("🚦 SMART TRAFFIC CONTROL SYSTEM")
        print("   King Khalid University - Graduation Project")
        print("=" * 60 + "\n")

        # Initialize database
        print("📊 Initializing database...")
        await db_manager.initialize()

        # Setup default intersection
        print("🚥 Setting up intersection configuration...")
        intersection_id = await db_manager.setup_default_intersection()

        # Start simulation
        print("🎮 Starting simulation (DEMO mode)...")
        demo_sim.start()

        # Inject app state
        app_state['db_manager'] = db_manager
        app_state['simulation'] = demo_sim
        app_state['optimizer'] = signal_optimizer
        app_state['emergency_handler'] = emergency_handler
        app_state['intersection_id'] = intersection_id
        app_state['mode'] = 'ai_optimized'
        app_state['running'] = True

        print("\n" + "=" * 60)
        print("✅ System initialization complete!")
        print("=" * 60 + "\n")

        # Start control loop in background
        async def control_loop():
            cycle_count = 0
            print("🔄 Starting traffic control loop...\n")

            while app_state.get('running', False):
                try:
                    # Advance simulation
                    lane_data = demo_sim.step()

                    # Handle emergency timeouts
                    if emergency_handler.check_emergency_timeout():
                        summary = emergency_handler.clear_emergency()
                        if summary and summary.get('event_id'):
                            await db_manager.resolve_emergency(summary['event_id'])

                    # Calculate signal timings
                    if emergency_handler.is_emergency_active():
                        signal_override = emergency_handler.get_emergency_signal_override()
                        if cycle_count % 5 == 0 and signal_override:
                            for lane, config in signal_override.items():
                                await db_manager.update_signal_state(
                                    intersection_id, lane,
                                    config['phase'], config['remaining']
                                )
                    else:
                        # Normal optimization
                        if app_state['mode'] == 'ai_optimized':
                            green_times = signal_optimizer.optimize_green_times(lane_data)
                        else:
                            green_times = {lane: 30 for lane in lane_data.keys()}

                        # Update simulation with calculated green times
                        demo_sim.set_green_times(green_times)

                        # Log green time allocation every 30 cycles
                        if cycle_count % 30 == 0:
                            mode_label = "FIXED" if app_state['mode'] == 'fixed_timer' else "AI"
                            times_str = ' '.join([f"{lane}:{green_times.get(lane, 0)}s" for lane in ['N', 'S', 'E', 'W']])
                            print(f"🎛️  [{mode_label}] Green times: {times_str}")

                        # Apply signal timings to database every 5 seconds
                        if cycle_count % 5 == 0:
                            for lane, data in lane_data.items():
                                await db_manager.update_signal_state(
                                    intersection_id, lane,
                                    data.get('phase', 'red'),
                                    data.get('remaining', 0)
                                )

                    # Log traffic data every 10 cycles
                    if cycle_count % 10 == 0:
                        for lane, data in lane_data.items():
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
                                green_time=green_times.get(lane, 0) if 'green_times' in locals() else 0
                            )

                    # Broadcast update to WebSocket clients
                    await broadcast_traffic_update()

                    # Print status every 30 cycles
                    if cycle_count % 30 == 0:
                        print(f"⏱️  Cycle {cycle_count:4d} | ", end='')
                        for lane in ['N', 'S', 'E', 'W']:
                            data = lane_data.get(lane, {})
                            vehicles = data.get('vehicle_count', 0)
                            phase = data.get('phase', 'red')[0].upper()
                            print(f"{lane}:{vehicles:2d}[{phase}] ", end='')
                        print()

                    cycle_count += 1
                    app_state['cycle_count'] = cycle_count

                    # Wait 1 second before next cycle
                    await asyncio.sleep(1.0)

                except Exception as e:
                    print(f"❌ Error in control loop: {e}")
                    import traceback
                    traceback.print_exc()
                    await asyncio.sleep(1.0)

        # Run control loop in background task
        control_task = asyncio.create_task(control_loop())

    except Exception as e:
        print(f"❌ Failed to initialize system: {e}")
        import traceback
        traceback.print_exc()
        raise

    yield

    # Shutdown
    print("\n\n🛑 Shutting down system...")
    app_state['running'] = False
    if 'control_task' in locals():
        control_task.cancel()
    if app_state.get('simulation'):
        app_state['simulation'].stop()
    if app_state.get('db_manager'):
        await app_state['db_manager'].close()
    print("✓ FastAPI application shutting down...")
    print("✅ Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Smart Traffic Control System API",
    description="AI-based traffic signal optimization API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (frontend)
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend')
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")


@app.get("/")
async def root():
    """Serve the main dashboard"""
    index_path = os.path.join(frontend_path, 'index.html')
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Smart Traffic Control System API", "status": "running"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "mode": app_state['mode'],
        "cycle_count": app_state['cycle_count']
    }


# Import routes after app creation to avoid circular imports
from . import routes, websocket, video_stream

# Include routers
app.include_router(routes.router)
app.include_router(websocket.router)
app.include_router(video_stream.router)
