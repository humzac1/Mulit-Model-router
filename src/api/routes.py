"""API routes for the multi-model router."""

from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
import structlog

from ..models.prompt import PromptRequest, PromptResponse, PromptAnalysis
from ..models.routing import RoutingDecision, RoutingContext, RoutingStrategy
from .server import get_router_instance
from ..routing.routing_engine import RoutingEngine

logger = structlog.get_logger()

# Router instances
router_routes = APIRouter()
health_routes = APIRouter()
analysis_routes = APIRouter()


# Pydantic models for API
class GenerateRequest(BaseModel):
    """Request model for text generation."""
    
    prompt: str = Field(..., description="Input prompt for generation")
    user_id: Optional[str] = Field(None, description="Optional user identifier")
    session_id: Optional[str] = Field(None, description="Optional session identifier")
    
    # Constraints
    max_cost: Optional[float] = Field(None, ge=0, description="Maximum cost in USD")
    max_latency_ms: Optional[int] = Field(None, ge=0, description="Maximum latency in milliseconds")
    min_quality: Optional[float] = Field(None, ge=0, le=1, description="Minimum quality score")
    
    # Preferences
    preferred_models: Optional[List[str]] = Field(default_factory=list, description="Preferred model IDs")
    excluded_models: Optional[List[str]] = Field(default_factory=list, description="Models to exclude")
    strategy: Optional[RoutingStrategy] = Field(RoutingStrategy.HYBRID, description="Routing strategy")
    
    # Model parameters
    temperature: Optional[float] = Field(0.7, ge=0, le=2, description="Sampling temperature")
    max_tokens: Optional[int] = Field(None, ge=1, description="Maximum tokens to generate")
    
    # Weights for routing decision
    capability_weight: Optional[float] = Field(0.4, ge=0, le=1, description="Weight for capability scoring")
    cost_weight: Optional[float] = Field(0.2, ge=0, le=1, description="Weight for cost scoring")
    latency_weight: Optional[float] = Field(0.2, ge=0, le=1, description="Weight for latency scoring")
    quality_weight: Optional[float] = Field(0.2, ge=0, le=1, description="Weight for quality scoring")


class RouteRequest(BaseModel):
    """Request model for routing decision only."""
    
    prompt: str = Field(..., description="Input prompt for routing")
    user_id: Optional[str] = Field(None, description="Optional user identifier")
    session_id: Optional[str] = Field(None, description="Optional session identifier")
    
    # Constraints
    max_cost: Optional[float] = Field(None, ge=0, description="Maximum cost in USD")
    max_latency_ms: Optional[int] = Field(None, ge=0, description="Maximum latency in milliseconds")
    min_quality: Optional[float] = Field(None, ge=0, le=1, description="Minimum quality score")
    
    # Preferences
    preferred_models: Optional[List[str]] = Field(default_factory=list, description="Preferred model IDs")
    excluded_models: Optional[List[str]] = Field(default_factory=list, description="Models to exclude")
    strategy: Optional[RoutingStrategy] = Field(RoutingStrategy.HYBRID, description="Routing strategy")
    
    # Weights for routing decision
    capability_weight: Optional[float] = Field(0.4, ge=0, le=1, description="Weight for capability scoring")
    cost_weight: Optional[float] = Field(0.2, ge=0, le=1, description="Weight for cost scoring")
    latency_weight: Optional[float] = Field(0.2, ge=0, le=1, description="Weight for latency scoring")
    quality_weight: Optional[float] = Field(0.2, ge=0, le=1, description="Weight for quality scoring")


class AnalyzeRequest(BaseModel):
    """Request model for prompt analysis."""
    
    prompt: str = Field(..., description="Prompt to analyze")


# Route handlers
@router_routes.post(
    "/generate",
    response_model=PromptResponse,
    summary="Generate text using optimal model",
    description="Analyze prompt, route to best model, and generate response"
)
async def generate_text(
    request: GenerateRequest,
    router: RoutingEngine = Depends(get_router_instance)
) -> PromptResponse:
    """Generate text using the optimal model based on intelligent routing."""
    try:
        # Convert to internal request format
        prompt_request = PromptRequest(
            prompt=request.prompt,
            user_id=request.user_id,
            session_id=request.session_id,
            constraints={
                "max_cost": request.max_cost,
                "max_latency_ms": request.max_latency_ms,
                "min_quality": request.min_quality
            },
            preferred_models=request.preferred_models or [],
            metadata={
                "temperature": request.temperature,
                "max_tokens": request.max_tokens
            }
        )
        
        # Create routing context
        routing_context = RoutingContext(
            max_cost=request.max_cost,
            max_latency_ms=request.max_latency_ms,
            min_quality=request.min_quality,
            preferred_models=request.preferred_models or [],
            excluded_models=request.excluded_models or [],
            strategy=request.strategy,
            user_id=request.user_id,
            session_id=request.session_id,
            capability_weight=request.capability_weight,
            cost_weight=request.cost_weight,
            latency_weight=request.latency_weight,
            quality_weight=request.quality_weight
        )
        
        # Route and execute
        response = await router.route_and_execute(prompt_request, routing_context)
        
        logger.info(
            "Generation request completed",
            user_id=request.user_id,
            selected_model=response.selected_model,
            cost=response.total_cost,
            latency_ms=response.total_latency_ms
        )
        
        return response
        
    except Exception as e:
        logger.error(
            "Generation request failed",
            error=str(e),
            user_id=request.user_id,
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Generation failed: {str(e)}"
        )


@router_routes.post(
    "/route",
    response_model=RoutingDecision,
    summary="Get routing decision",
    description="Analyze prompt and return routing decision without executing"
)
async def route_request(
    request: RouteRequest,
    router: RoutingEngine = Depends(get_router_instance)
) -> RoutingDecision:
    """Get routing decision for a prompt without executing it."""
    try:
        # Convert to internal request format
        prompt_request = PromptRequest(
            prompt=request.prompt,
            user_id=request.user_id,
            session_id=request.session_id,
            constraints={
                "max_cost": request.max_cost,
                "max_latency_ms": request.max_latency_ms,
                "min_quality": request.min_quality
            },
            preferred_models=request.preferred_models or []
        )
        
        # Create routing context
        routing_context = RoutingContext(
            max_cost=request.max_cost,
            max_latency_ms=request.max_latency_ms,
            min_quality=request.min_quality,
            preferred_models=request.preferred_models or [],
            excluded_models=request.excluded_models or [],
            strategy=request.strategy,
            user_id=request.user_id,
            session_id=request.session_id,
            capability_weight=request.capability_weight,
            cost_weight=request.cost_weight,
            latency_weight=request.latency_weight,
            quality_weight=request.quality_weight
        )
        
        # Analyze prompt
        analysis = await router.prompt_analyzer.analyze_prompt(request.prompt)
        
        # Make routing decision
        decision = await router.make_routing_decision(
            prompt_request, analysis, routing_context
        )
        
        logger.info(
            "Routing request completed",
            user_id=request.user_id,
            selected_model=decision.selected_model,
            confidence=decision.confidence
        )
        
        return decision
        
    except Exception as e:
        logger.error(
            "Routing request failed",
            error=str(e),
            user_id=request.user_id,
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Routing failed: {str(e)}"
        )


@analysis_routes.post(
    "/analyze",
    response_model=PromptAnalysis,
    summary="Analyze prompt",
    description="Analyze prompt for task type, complexity, and other characteristics"
)
async def analyze_prompt(
    request: AnalyzeRequest,
    router: RoutingEngine = Depends(get_router_instance)
) -> PromptAnalysis:
    """Analyze a prompt to determine its characteristics."""
    try:
        analysis = await router.prompt_analyzer.analyze_prompt(request.prompt)
        
        logger.debug(
            "Prompt analysis completed",
            task_type=analysis.task_type.value,
            complexity=analysis.complexity.value,
            domain=analysis.domain.value,
            confidence=analysis.confidence
        )
        
        return analysis
        
    except Exception as e:
        logger.error(
            "Prompt analysis failed",
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


@health_routes.get(
    "",
    summary="Health check",
    description="Basic health check endpoint"
)
async def health_check() -> Dict[str, Any]:
    """Basic health check."""
    return {
        "status": "healthy",
        "service": "multi-model-router",
        "version": "0.1.0"
    }


@health_routes.get(
    "/models",
    summary="Model health status",
    description="Check health status of all configured models"
)
async def model_health(
    router: RoutingEngine = Depends(get_router_instance)
) -> Dict[str, Any]:
    """Check health status of all models."""
    try:
        health_status = await router.get_model_health()
        
        healthy_count = sum(1 for status in health_status.values() if status)
        total_count = len(health_status)
        
        return {
            "status": "healthy" if healthy_count > 0 else "unhealthy",
            "models": health_status,
            "summary": {
                "total": total_count,
                "healthy": healthy_count,
                "unhealthy": total_count - healthy_count
            }
        }
        
    except Exception as e:
        logger.error(
            "Model health check failed",
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Health check failed: {str(e)}"
        )


@health_routes.get(
    "/knowledge-base",
    summary="Knowledge base status",
    description="Check status of the RAG knowledge base"
)
async def knowledge_base_status(
    router: RoutingEngine = Depends(get_router_instance)
) -> Dict[str, Any]:
    """Check knowledge base status."""
    try:
        stats = router.knowledge_base.get_stats()
        
        return {
            "status": "healthy" if stats.get("total_documents", 0) > 0 else "empty",
            "stats": stats
        }
        
    except Exception as e:
        logger.error(
            "Knowledge base status check failed",
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Knowledge base check failed: {str(e)}"
        )


@router_routes.get(
    "/models",
    summary="List available models",
    description="Get list of all configured models and their capabilities"
)
async def list_models(
    router: RoutingEngine = Depends(get_router_instance)
) -> Dict[str, Any]:
    """List all available models and their configurations."""
    try:
        models_info = []
        
        for model_id, model_config in router.models.items():
            model_info = {
                "model_id": model_config.model_id,
                "name": model_config.name,
                "provider": model_config.provider.value,
                "model_type": model_config.model_type.value,
                "is_enabled": model_config.is_enabled,
                "capabilities": {
                    "reasoning_ability": model_config.capabilities.reasoning_ability,
                    "creative_ability": model_config.capabilities.creative_ability,
                    "code_ability": model_config.capabilities.code_ability,
                    "analysis_ability": model_config.capabilities.analysis_ability,
                    "max_context_length": model_config.capabilities.max_context_length,
                    "max_output_length": model_config.capabilities.max_output_length,
                    "supported_tasks": model_config.capabilities.supported_tasks
                },
                "constraints": {
                    "input_cost_per_1k_tokens": model_config.constraints.input_cost_per_1k_tokens,
                    "output_cost_per_1k_tokens": model_config.constraints.output_cost_per_1k_tokens,
                    "avg_latency_ms": model_config.constraints.avg_latency_ms,
                    "availability": model_config.constraints.availability
                },
                "preferred_for_tasks": model_config.preferred_for_tasks,
                "avoid_for_tasks": model_config.avoid_for_tasks
            }
            models_info.append(model_info)
        
        return {
            "models": models_info,
            "total_count": len(models_info),
            "enabled_count": sum(1 for m in models_info if m["is_enabled"])
        }
        
    except Exception as e:
        logger.error(
            "List models failed",
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list models: {str(e)}"
        )
