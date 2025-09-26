"""Prompt-related Pydantic models."""

from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime


class TaskType(str, Enum):
    """Types of tasks that can be performed."""
    REASONING = "reasoning"
    CREATIVE = "creative"  
    CODE = "code"
    QA = "qa"
    ANALYSIS = "analysis"
    TRANSLATION = "translation"
    SUMMARIZATION = "summarization"
    CONVERSATION = "conversation"
    UNKNOWN = "unknown"


class ComplexityLevel(str, Enum):
    """Complexity levels for prompts."""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"
    EXPERT = "expert"


class Domain(str, Enum):
    """Domain areas for specialized knowledge."""
    GENERAL = "general"
    TECHNICAL = "technical"
    SCIENTIFIC = "scientific"
    CREATIVE = "creative"
    BUSINESS = "business"
    LEGAL = "legal"
    MEDICAL = "medical"
    EDUCATIONAL = "educational"


class PromptRequest(BaseModel):
    """Incoming prompt request."""
    
    prompt: str = Field(..., description="The user's prompt/query")
    user_id: Optional[str] = Field(None, description="Optional user identifier")
    session_id: Optional[str] = Field(None, description="Optional session identifier")
    constraints: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="User constraints (max_cost, max_latency_ms, min_quality)"
    )
    preferred_models: Optional[List[str]] = Field(
        default_factory=list,
        description="User's preferred models if any"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PromptAnalysis(BaseModel):
    """Analysis results for a prompt."""
    
    task_type: TaskType = Field(..., description="Detected task type")
    complexity: ComplexityLevel = Field(..., description="Complexity assessment")
    domain: Domain = Field(..., description="Domain classification")
    
    # Scoring dimensions (0.0 to 1.0)
    reasoning_required: float = Field(
        0.0, ge=0.0, le=1.0, 
        description="How much reasoning is required"
    )
    creativity_required: float = Field(
        0.0, ge=0.0, le=1.0,
        description="How much creativity is required"
    )
    domain_expertise: float = Field(
        0.0, ge=0.0, le=1.0,
        description="How much domain expertise is required"
    )
    context_length: int = Field(..., ge=0, description="Input token count estimate")
    expected_output_length: int = Field(
        0, ge=0, 
        description="Expected output token count"
    )
    
    # Analysis metadata
    confidence: float = Field(
        0.0, ge=0.0, le=1.0,
        description="Confidence in the analysis"
    )
    analysis_time_ms: float = Field(..., description="Time taken for analysis")
    keywords: List[str] = Field(
        default_factory=list,
        description="Key terms extracted from prompt"
    )


class PromptResponse(BaseModel):
    """Response from the selected model."""
    
    request_id: str = Field(..., description="Unique request identifier")
    selected_model: str = Field(..., description="Model that was used")
    response_text: str = Field(..., description="Generated response")
    
    # Performance metrics
    total_latency_ms: float = Field(..., description="Total response time")
    model_latency_ms: float = Field(..., description="Model inference time")
    total_cost: float = Field(..., description="Total cost in USD")
    
    # Token usage
    input_tokens: int = Field(..., description="Input tokens used")
    output_tokens: int = Field(..., description="Output tokens generated")
    
    # Quality and metadata
    quality_score: Optional[float] = Field(
        None, ge=0.0, le=1.0,
        description="Estimated quality score"
    )
    fallback_used: bool = Field(False, description="Whether fallback was used")
    routing_confidence: float = Field(
        0.0, ge=0.0, le=1.0,
        description="Confidence in routing decision"
    )
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional response metadata"
    )
