"""Model configuration and capabilities models."""

from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field


class ModelProvider(str, Enum):
    """Supported model providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    HUGGINGFACE = "huggingface"


class ModelType(str, Enum):
    """Types of models."""
    CHAT = "chat"
    COMPLETION = "completion"
    EMBEDDING = "embedding"
    CODE = "code"
    REASONING = "reasoning"


class ModelCapabilities(BaseModel):
    """Detailed capabilities of a model."""
    
    # Core capabilities (0.0 to 1.0 scoring)
    reasoning_ability: float = Field(0.0, ge=0.0, le=1.0)
    creative_ability: float = Field(0.0, ge=0.0, le=1.0)
    code_ability: float = Field(0.0, ge=0.0, le=1.0)
    analysis_ability: float = Field(0.0, ge=0.0, le=1.0)
    factual_accuracy: float = Field(0.0, ge=0.0, le=1.0)
    instruction_following: float = Field(0.0, ge=0.0, le=1.0)
    
    # Context and output capabilities
    max_context_length: int = Field(..., description="Maximum context window")
    max_output_length: int = Field(..., description="Maximum output tokens")
    
    # Supported task types
    supported_tasks: List[str] = Field(
        default_factory=list,
        description="List of supported task types"
    )
    
    # Domain expertise
    domain_expertise: Dict[str, float] = Field(
        default_factory=dict,
        description="Domain expertise scores (0.0 to 1.0)"
    )
    
    # Language support
    supported_languages: List[str] = Field(
        default_factory=list,
        description="Supported languages"
    )
    
    # Special features
    supports_function_calling: bool = Field(False)
    supports_json_mode: bool = Field(False)
    supports_vision: bool = Field(False)
    supports_code_execution: bool = Field(False)


class ModelConstraints(BaseModel):
    """Performance and cost constraints for a model."""
    
    # Cost (per token in USD)
    input_cost_per_1k_tokens: float = Field(..., ge=0.0)
    output_cost_per_1k_tokens: float = Field(..., ge=0.0)
    
    # Performance
    avg_latency_ms: float = Field(..., ge=0.0, description="Average latency")
    p95_latency_ms: float = Field(..., ge=0.0, description="95th percentile latency")
    availability: float = Field(1.0, ge=0.0, le=1.0, description="Availability rate")
    
    # Rate limits
    requests_per_minute: Optional[int] = Field(None, description="RPM limit")
    tokens_per_minute: Optional[int] = Field(None, description="TPM limit")
    
    # Quality metrics
    avg_quality_score: float = Field(0.0, ge=0.0, le=1.0)
    user_satisfaction: float = Field(0.0, ge=0.0, le=1.0)


class ModelConfig(BaseModel):
    """Complete configuration for a model."""
    
    # Basic identification
    model_id: str = Field(..., description="Unique model identifier")
    name: str = Field(..., description="Human-readable model name")
    provider: ModelProvider = Field(..., description="Model provider")
    model_type: ModelType = Field(..., description="Type of model")
    version: str = Field("latest", description="Model version")
    
    # Configuration
    endpoint_url: Optional[str] = Field(None, description="Custom endpoint URL")
    api_key_env: Optional[str] = Field(None, description="Environment variable for API key")
    
    # Model details
    capabilities: ModelCapabilities = Field(..., description="Model capabilities")
    constraints: ModelConstraints = Field(..., description="Performance constraints")
    
    # Routing preferences
    preferred_for_tasks: List[str] = Field(
        default_factory=list,
        description="Tasks this model is preferred for"
    )
    avoid_for_tasks: List[str] = Field(
        default_factory=list,
        description="Tasks to avoid using this model for"
    )
    
    # Status and health
    is_enabled: bool = Field(True, description="Whether model is enabled")
    health_check_url: Optional[str] = Field(None, description="Health check endpoint")
    last_health_check: Optional[str] = Field(None, description="Last health check timestamp")
    
    # Additional configuration
    default_parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Default parameters for this model"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    
    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "model_id": "gpt-4-turbo",
                "name": "GPT-4 Turbo",
                "provider": "openai",
                "model_type": "chat",
                "capabilities": {
                    "reasoning_ability": 0.95,
                    "creative_ability": 0.9,
                    "code_ability": 0.85,
                    "analysis_ability": 0.95,
                    "max_context_length": 128000,
                    "max_output_length": 4096
                },
                "constraints": {
                    "input_cost_per_1k_tokens": 0.01,
                    "output_cost_per_1k_tokens": 0.03,
                    "avg_latency_ms": 2000,
                    "p95_latency_ms": 5000
                }
            }
        }
