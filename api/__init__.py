"""FastAPI backend for Smart Traffic Control System"""
from .app import app, app_state
from .websocket import broadcast_traffic_update

__all__ = ['app', 'app_state', 'broadcast_traffic_update']
