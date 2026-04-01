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
    # Startup
    print("✓ FastAPI application starting...")
    yield
    # Shutdown
    print("✓ FastAPI application shutting down...")


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
