"""FastAPI server and endpoints for the multi-model router."""

from .server import create_app, get_router_instance
from .routes import router_routes, health_routes, analysis_routes

__all__ = [
    "create_app",
    "get_router_instance",
    "router_routes",
    "health_routes", 
    "analysis_routes",
]
