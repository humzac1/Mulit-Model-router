"""Routing decision and scoring models."""

from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class RoutingStrategy(str, Enum):
    """Routing strategies available."""
    RAG_BASED = "rag_based"
    RULE_BASED = "rule_based"
    COST_OPTIMIZED = "cost_optimized"
    LATENCY_OPTIMIZED = "latency_optimized"
    QUALITY_OPTIMIZED = "quality_optimized"
    HYBRID = "hybrid"


class RoutingReason(str, Enum):
    """Reasons for routing decisions."""
    BEST_CAPABILITIES = "best_capabilities"
    COST_CONSTRAINT = "cost_constraint"
    LATENCY_CONSTRAINT = "latency_constraint"
    USER_PREFERENCE = "user_preference"
    FALLBACK = "fallback"
    MODEL_UNAVAILABLE = "model_unavailable"
    LOAD_BALANCING = "load_balancing"


class RoutingScore(BaseModel):
    """Scoring for a model candidate."""

    model_config = ConfigDict(protected_namespaces=())

    model_id: str = Field(..., description="Model identifier")
    
    # Core scores (0.0 to 1.0)
    capability_score: float = Field(0.0, ge=0.0, le=1.0)
    cost_score: float = Field(0.0, ge=0.0, le=1.0)
    latency_score: float = Field(0.0, ge=0.0, le=1.0)
    availability_score: float = Field(0.0, ge=0.0, le=1.0)
    quality_score: float = Field(0.0, ge=0.0, le=1.0)
    
    # Composite scores
    weighted_score: float = Field(0.0, ge=0.0, le=1.0)
    final_score: float = Field(0.0, ge=0.0, le=1.0)
    
    # Supporting data
    estimated_cost: float = Field(0.0, description="Estimated cost in USD")
    estimated_latency_ms: float = Field(0.0, description="Estimated latency")
    meets_constraints: bool = Field(True, description="Whether constraints are met")
    
    # RAG-based scoring
    rag_similarity: Optional[float] = Field(
        None, ge=0.0, le=1.0,
        description="Similarity score from RAG query"
    )
    rag_evidence: Optional[List[str]] = Field(
        None,
        description="Evidence from RAG supporting this model"
    )


class RoutingContext(BaseModel):
    """Context used for routing decisions."""

    model_config = ConfigDict(protected_namespaces=())

    # User constraints
    max_cost: Optional[float] = Field(None, description="Maximum cost constraint")
    max_latency_ms: Optional[int] = Field(None, description="Maximum latency constraint")
    min_quality: Optional[float] = Field(None, description="Minimum quality constraint")
    
    # Preferences
    preferred_models: List[str] = Field(default_factory=list)
    excluded_models: List[str] = Field(default_factory=list)
    strategy: RoutingStrategy = Field(RoutingStrategy.HYBRID)
    
    # Context
    user_id: Optional[str] = Field(None)
    session_id: Optional[str] = Field(None)
    
    # Weights for scoring (should sum to 1.0)
    capability_weight: float = Field(0.4, ge=0.0, le=1.0)
    cost_weight: float = Field(0.2, ge=0.0, le=1.0)
    latency_weight: float = Field(0.2, ge=0.0, le=1.0)
    quality_weight: float = Field(0.2, ge=0.0, le=1.0)


class RoutingDecision(BaseModel):
    """Final routing decision with full details."""

    model_config = ConfigDict(protected_namespaces=())

    # Decision
    selected_model: str = Field(..., description="Selected model ID")
    fallback_models: List[str] = Field(
        default_factory=list,
        description="Ordered list of fallback models"
    )
    
    # Reasoning
    strategy_used: RoutingStrategy = Field(..., description="Strategy used for routing")
    primary_reason: RoutingReason = Field(..., description="Primary reason for selection")
    secondary_reasons: List[RoutingReason] = Field(
        default_factory=list,
        description="Additional reasons"
    )
    
    # Scoring details
    candidate_scores: List[RoutingScore] = Field(
        default_factory=list,
        description="Scores for all evaluated models"
    )
    
    # Confidence and quality
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Decision confidence")
    expected_quality: float = Field(0.0, ge=0.0, le=1.0, description="Expected quality")
    expected_cost: float = Field(0.0, description="Expected cost in USD")
    expected_latency_ms: float = Field(0.0, description="Expected latency")
    
    # RAG information
    rag_query_used: Optional[str] = Field(None, description="RAG query used")
    rag_results_count: int = Field(0, description="Number of RAG results")
    rag_total_time_ms: float = Field(0.0, description="Time spent on RAG queries")
    
    # Metadata
    decision_time_ms: float = Field(..., description="Time taken for routing decision")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional decision metadata"
    )
    
    # Debug information
    debug_info: Optional[Dict[str, Any]] = Field(
        None,
        description="Debug information for development"
    )
