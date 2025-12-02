"""FastAPI server and endpoints for the multi-model router."""

from .routes import router_routes, health_routes, analysis_routes

__all__ = [
    "router_routes",
    "health_routes", 
    "analysis_routes",
]
