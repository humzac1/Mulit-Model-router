"""Anthropic model integration."""

import asyncio
import time
from typing import Optional, AsyncGenerator, Dict, Any
import anthropic
from anthropic import AsyncAnthropic
import structlog

from .base_model import BaseModelInterface, ModelResponse, ModelError

logger = structlog.get_logger()


class AnthropicIntegration(BaseModelInterface):
    """Integration with Anthropic Claude models."""
    
    # Model context and output limits
    MODEL_LIMITS = {
        "claude-3-sonnet-20240229": {"context": 200000, "output": 4096},
        "claude-3-haiku-20240307": {"context": 200000, "output": 4096},
        "claude-3-opus-20240229": {"context": 200000, "output": 4096},
        "claude-instant-1.2": {"context": 100000, "output": 4096},
    }
    
    # Cost per 1K tokens (input, output)
    MODEL_COSTS = {
        "claude-3-sonnet-20240229": (0.003, 0.015),
        "claude-3-haiku-20240307": (0.00025, 0.00125),
        "claude-3-opus-20240229": (0.015, 0.075),
        "claude-instant-1.2": (0.0008, 0.0024),
    }
    
    def __init__(
        self,
        model_id: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3
    ):
        """Initialize Anthropic integration.
        
        Args:
            model_id: Anthropic model identifier
            api_key: Anthropic API key
            base_url: Custom base URL (optional)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
        """
        super().__init__(model_id, api_key, base_url, timeout, max_retries)
        self._client: Optional[AsyncAnthropic] = None
    
    @property
    def provider_name(self) -> str:
        return "anthropic"
    
    @property
    def client(self) -> AsyncAnthropic:
        """Lazy load Anthropic client."""
        if self._client is None:
            client_kwargs = {
                "api_key": self.api_key,
                "timeout": self.timeout,
                "max_retries": self.max_retries
            }
            
            if self.base_url:
                client_kwargs["base_url"] = self.base_url
                
            self._client = AsyncAnthropic(**client_kwargs)
        return self._client
    
    async def generate_response(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ModelResponse:
        """Generate response from Anthropic model."""
        start_time = time.time()
        
        await self.validate_request(prompt, max_tokens)
        
        try:
            # Prepare request parameters
            request_params = {
                "model": self.model_id,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens or 4096,
                **kwargs
            }
            
            logger.debug(
                "Sending Anthropic request",
                model=self.model_id,
                prompt_length=len(prompt),
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Make API call
            response = await self.client.messages.create(**request_params)
            
            # Calculate metrics
            latency_ms = (time.time() - start_time) * 1000
            
            # Extract response data
            content = ""
            if response.content and len(response.content) > 0:
                # Claude returns content as a list of content blocks
                content = response.content[0].text if hasattr(response.content[0], 'text') else str(response.content[0])
            
            finish_reason = response.stop_reason
            
            # Token usage
            input_tokens = response.usage.input_tokens if response.usage else self.estimate_tokens(prompt)
            output_tokens = response.usage.output_tokens if response.usage else self.estimate_tokens(content)
            total_tokens = input_tokens + output_tokens
            
            # Calculate cost
            cost = self.estimate_cost(input_tokens, output_tokens)
            
            model_response = ModelResponse(
                content=content,
                model_id=self.model_id,
                provider=self.provider_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                latency_ms=latency_ms,
                cost_usd=cost,
                finish_reason=finish_reason,
                metadata={
                    "response_id": response.id,
                    "model": response.model,
                    "role": response.role,
                    "stop_sequence": response.stop_sequence
                }
            )
            
            logger.info(
                "Anthropic response generated",
                model=self.model_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
                cost_usd=cost,
                finish_reason=finish_reason
            )
            
            return model_response
            
        except anthropic.APITimeoutError as e:
            raise ModelError(
                f"Anthropic request timeout: {str(e)}",
                model_id=self.model_id,
                provider=self.provider_name,
                error_code="TIMEOUT",
                retryable=True
            )
        except anthropic.RateLimitError as e:
            raise ModelError(
                f"Anthropic rate limit exceeded: {str(e)}",
                model_id=self.model_id,
                provider=self.provider_name,
                error_code="RATE_LIMIT",
                retryable=True
            )
        except anthropic.APIError as e:
            raise ModelError(
                f"Anthropic API error: {str(e)}",
                model_id=self.model_id,
                provider=self.provider_name,
                error_code="API_ERROR",
                retryable=False
            )
        except Exception as e:
            logger.error(
                "Unexpected error in Anthropic integration",
                model=self.model_id,
                error=str(e),
                exc_info=True
            )
            raise ModelError(
                f"Unexpected error: {str(e)}",
                model_id=self.model_id,
                provider=self.provider_name,
                error_code="UNKNOWN",
                retryable=False
            )
    
    async def stream_response(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream response from Anthropic model."""
        await self.validate_request(prompt, max_tokens)
        
        try:
            # Prepare request parameters
            request_params = {
                "model": self.model_id,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens or 4096,
                "stream": True,
                **kwargs
            }
            
            logger.debug(
                "Starting Anthropic stream",
                model=self.model_id,
                prompt_length=len(prompt)
            )
            
            # Make streaming API call
            async with self.client.messages.stream(**request_params) as stream:
                async for text in stream.text_stream:
                    yield text
                    
        except Exception as e:
            logger.error(
                "Error in Anthropic streaming",
                model=self.model_id,
                error=str(e)
            )
            raise ModelError(
                f"Streaming error: {str(e)}",
                model_id=self.model_id,
                provider=self.provider_name,
                error_code="STREAM_ERROR",
                retryable=False
            )
    
    async def check_health(self) -> bool:
        """Check Anthropic API health."""
        try:
            # Simple API call to check health
            response = await self.client.messages.create(
                model=self.model_id,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1,
                temperature=0
            )
            
            logger.debug("Anthropic health check passed", model=self.model_id)
            return True
            
        except Exception as e:
            logger.warning(
                "Anthropic health check failed",
                model=self.model_id,
                error=str(e)
            )
            return False
    
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for Anthropic request."""
        if self.model_id not in self.MODEL_COSTS:
            # Default cost estimation (using Claude-3 Sonnet pricing)
            logger.warning(
                "Unknown model for cost estimation",
                model=self.model_id
            )
            return (input_tokens * 0.003 + output_tokens * 0.015) / 1000
        
        input_cost_per_1k, output_cost_per_1k = self.MODEL_COSTS[self.model_id]
        
        input_cost = (input_tokens / 1000) * input_cost_per_1k
        output_cost = (output_tokens / 1000) * output_cost_per_1k
        
        return input_cost + output_cost
    
    def get_max_context_length(self) -> int:
        """Get maximum context length for the model."""
        return self.MODEL_LIMITS.get(self.model_id, {}).get("context", 100000)
    
    def get_max_output_length(self) -> int:
        """Get maximum output length for the model."""
        return self.MODEL_LIMITS.get(self.model_id, {}).get("output", 4096)
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for Anthropic models."""
        # Anthropic estimation: ~4 characters per token for English
        return max(1, len(text) // 4)
    
    async def close(self) -> None:
        """Close the client connection."""
        if self._client:
            await self._client.close()
            self._client = None
