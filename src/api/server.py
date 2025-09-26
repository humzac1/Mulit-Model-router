"""FastAPI server configuration and setup."""

import os
import asyncio
from typing import Optional
from pathlib import Path
import yaml
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import structlog

from ..models.model_config import ModelConfig
from ..rag.knowledge_base import ModelKnowledgeBase
from ..routing.routing_engine import RoutingEngine
from .routes import router_routes, health_routes, analysis_routes

logger = structlog.get_logger()

# Global router instance
_router_instance: Optional[RoutingEngine] = None


async def initialize_router() -> RoutingEngine:
    """Initialize the routing engine with models and knowledge base."""
    global _router_instance
    
    if _router_instance is not None:
        return _router_instance
    
    logger.info("Initializing multi-model router")
    
    # Load model configurations
    config_path = Path(__file__).parent.parent.parent / "data" / "configs" / "models.yaml"
    docs_path = Path(__file__).parent.parent.parent / "data" / "model_docs"
    
    try:
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        
        # Parse model configurations
        models = []
        for model_data in config_data.get("models", {}).values():
            try:
                model_config = ModelConfig(**model_data)
                models.append(model_config)
                logger.debug(
                    "Loaded model configuration",
                    model_id=model_config.model_id,
                    provider=model_config.provider.value
                )
            except Exception as e:
                logger.error(
                    "Failed to parse model config",
                    model_data=model_data,
                    error=str(e)
                )
                continue
        
        if not models:
            raise ValueError("No valid model configurations found")
        
        logger.info(f"Loaded {len(models)} model configurations")
        
        # Initialize knowledge base
        persist_dir = os.getenv(
            "CHROMA_PERSIST_DIRECTORY",
            str(Path(__file__).parent.parent.parent / "data" / "chroma_db")
        )
        
        knowledge_base = ModelKnowledgeBase(persist_directory=persist_dir)
        
        # Initialize knowledge base from documents
        if docs_path.exists():
            await knowledge_base.initialize_from_documents(str(docs_path))
            logger.info("Knowledge base initialized from documents")
        else:
            logger.warning(
                "Model documentation directory not found",
                path=str(docs_path)
            )
        
        # Create routing engine
        _router_instance = RoutingEngine(
            models=models,
            knowledge_base=knowledge_base
        )
        
        logger.info("Multi-model router initialized successfully")
        return _router_instance
        
    except Exception as e:
        logger.error(
            "Failed to initialize router",
            error=str(e),
            exc_info=True
        )
        raise


def get_router_instance() -> RoutingEngine:
    """Get the global router instance."""
    if _router_instance is None:
        raise RuntimeError("Router not initialized. Call initialize_router() first.")
    return _router_instance


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting multi-model router API")
    
    try:
        await initialize_router()
        logger.info("Router initialization completed")
    except Exception as e:
        logger.error(
            "Failed to initialize router during startup",
            error=str(e)
        )
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down multi-model router API")
    global _router_instance
    if _router_instance:
        try:
            await _router_instance.close()
            logger.info("Router closed successfully")
        except Exception as e:
            logger.error(
                "Error during router shutdown",
                error=str(e)
            )
        finally:
            _router_instance = None


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    # Configure structured logging
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Create FastAPI app
    app = FastAPI(
        title="Multi-Model Content Pipeline System",
        description="Intelligent multi-model routing system with RAG-powered model selection",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )
    
    # Add middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Include routers
    app.include_router(health_routes, prefix="/health", tags=["Health"])
    app.include_router(analysis_routes, prefix="/analysis", tags=["Analysis"])
    app.include_router(router_routes, prefix="/api/v1", tags=["Routing"])
    
    # Root endpoint
    @app.get("/", tags=["Root"])
    async def root():
        """Root endpoint with API information."""
        return {
            "name": "Multi-Model Content Pipeline System",
            "version": "0.1.0",
            "description": "Intelligent multi-model routing system with RAG-powered model selection",
            "docs": "/docs",
            "health": "/health",
            "endpoints": {
                "generate": "/api/v1/generate",
                "route": "/api/v1/route",
                "analyze": "/analysis/analyze",
                "models": "/health/models"
            }
        }
    
    return app


# For development server
if __name__ == "__main__":
    import uvicorn
    
    app = create_app()
    
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )
