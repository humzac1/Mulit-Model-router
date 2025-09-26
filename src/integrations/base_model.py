"""Base interface for all model integrations."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, AsyncGenerator
from dataclasses import dataclass
from datetime import datetime
import structlog

logger = structlog.get_logger()


@dataclass
class ModelResponse:
    """Standardized response from any model."""
    
    content: str
    model_id: str
    provider: str
    
    # Token usage
    input_tokens: int
    output_tokens: int
    total_tokens: int
    
    # Performance metrics
    latency_ms: float
    cost_usd: float
    
    # Metadata
    finish_reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class ModelError(Exception):
    """Base exception for model-related errors."""
    
    def __init__(
        self, 
        message: str, 
        model_id: str = None,
        provider: str = None,
        error_code: str = None,
        retryable: bool = False
    ):
        super().__init__(message)
        self.model_id = model_id
        self.provider = provider
        self.error_code = error_code
        self.retryable = retryable


class BaseModelInterface(ABC):
    """Abstract base class for all model integrations."""
    
    def __init__(
        self,
        model_id: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3
    ):
        """Initialize the model interface.
        
        Args:
            model_id: Identifier for the specific model
            api_key: API key for authentication
            base_url: Base URL for the API
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.model_id = model_id
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self._client = None
        
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of the provider (e.g., 'openai', 'anthropic')."""
        pass
    
    @abstractmethod
    async def generate_response(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ModelResponse:
        """Generate a response from the model.
        
        Args:
            prompt: Input prompt for the model
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional model-specific parameters
            
        Returns:
            ModelResponse object with the generated content
            
        Raises:
            ModelError: If the request fails
        """
        pass
    
    @abstractmethod
    async def stream_response(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream response from the model.
        
        Args:
            prompt: Input prompt for the model
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional model-specific parameters
            
        Yields:
            Chunks of generated text
            
        Raises:
            ModelError: If the request fails
        """
        pass
    
    @abstractmethod
    async def check_health(self) -> bool:
        """Check if the model is available and healthy.
        
        Returns:
            True if model is healthy, False otherwise
        """
        pass
    
    @abstractmethod
    def estimate_cost(
        self,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """Estimate cost for a request.
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            
        Returns:
            Estimated cost in USD
        """
        pass
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text.
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            Estimated token count
        """
        # Simple estimation: ~4 characters per token for English
        return max(1, len(text) // 4)
    
    async def validate_request(
        self,
        prompt: str,
        max_tokens: Optional[int] = None
    ) -> None:
        """Validate a request before sending.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            
        Raises:
            ModelError: If the request is invalid
        """
        if not prompt or not prompt.strip():
            raise ModelError(
                "Empty prompt provided",
                model_id=self.model_id,
                provider=self.provider_name,
                error_code="EMPTY_PROMPT"
            )
        
        # Check prompt length
        estimated_tokens = self.estimate_tokens(prompt)
        if estimated_tokens > self.get_max_context_length():
            raise ModelError(
                f"Prompt too long: {estimated_tokens} tokens exceeds maximum context length",
                model_id=self.model_id,
                provider=self.provider_name,
                error_code="CONTEXT_LENGTH_EXCEEDED"
            )
    
    @abstractmethod
    def get_max_context_length(self) -> int:
        """Get maximum context length for this model.
        
        Returns:
            Maximum context length in tokens
        """
        pass
    
    @abstractmethod
    def get_max_output_length(self) -> int:
        """Get maximum output length for this model.
        
        Returns:
            Maximum output length in tokens
        """
        pass
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about this model.
        
        Returns:
            Dictionary with model information
        """
        return {
            "model_id": self.model_id,
            "provider": self.provider_name,
            "max_context_length": self.get_max_context_length(),
            "max_output_length": self.get_max_output_length(),
            "base_url": self.base_url,
            "timeout": self.timeout,
            "max_retries": self.max_retries
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if hasattr(self, '_client') and self._client:
            if hasattr(self._client, 'close'):
                await self._client.close()
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model_id='{self.model_id}', provider='{self.provider_name}')"
