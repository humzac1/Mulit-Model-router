"""OpenAI model integration."""

import asyncio
import time
from typing import Optional, AsyncGenerator, Dict, Any
import openai
from openai import AsyncOpenAI
import structlog

from .base_model import BaseModelInterface, ModelResponse, ModelError

logger = structlog.get_logger()


class OpenAIIntegration(BaseModelInterface):
    """Integration with OpenAI models."""
    
    # Model context and output limits
    MODEL_LIMITS = {
        "gpt-4-turbo": {"context": 128000, "output": 4096},
        "gpt-4-1106-preview": {"context": 128000, "output": 4096},
        "gpt-4": {"context": 8192, "output": 4096},
        "gpt-3.5-turbo": {"context": 16385, "output": 4096},
        "gpt-3.5-turbo-16k": {"context": 16385, "output": 4096},
    }
    
    # Cost per 1K tokens (input, output)
    MODEL_COSTS = {
        "gpt-4-turbo": (0.01, 0.03),
        "gpt-4-1106-preview": (0.01, 0.03),
        "gpt-4": (0.03, 0.06),
        "gpt-3.5-turbo": (0.0005, 0.0015),
        "gpt-3.5-turbo-16k": (0.003, 0.004),
    }
    
    def __init__(
        self,
        model_id: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3
    ):
        """Initialize OpenAI integration.
        
        Args:
            model_id: OpenAI model identifier
            api_key: OpenAI API key
            base_url: Custom base URL (optional)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
        """
        super().__init__(model_id, api_key, base_url, timeout, max_retries)
        self._client: Optional[AsyncOpenAI] = None
    
    @property
    def provider_name(self) -> str:
        return "openai"
    
    @property
    def client(self) -> AsyncOpenAI:
        """Lazy load OpenAI client."""
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout,
                max_retries=self.max_retries
            )
        return self._client
    
    async def generate_response(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ModelResponse:
        """Generate response from OpenAI model."""
        start_time = time.time()
        
        await self.validate_request(prompt, max_tokens)
        
        try:
            # Prepare request parameters
            request_params = {
                "model": self.model_id,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "stream": False,
                **kwargs
            }
            
            if max_tokens:
                request_params["max_tokens"] = max_tokens
            
            logger.debug(
                "Sending OpenAI request",
                model=self.model_id,
                prompt_length=len(prompt),
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Make API call
            response = await self.client.chat.completions.create(**request_params)
            
            # Calculate metrics
            latency_ms = (time.time() - start_time) * 1000
            
            # Extract response data
            content = response.choices[0].message.content or ""
            finish_reason = response.choices[0].finish_reason
            
            # Token usage
            usage = response.usage
            input_tokens = usage.prompt_tokens if usage else self.estimate_tokens(prompt)
            output_tokens = usage.completion_tokens if usage else self.estimate_tokens(content)
            total_tokens = usage.total_tokens if usage else input_tokens + output_tokens
            
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
                    "created": response.created,
                    "system_fingerprint": getattr(response, "system_fingerprint", None)
                }
            )
            
            logger.info(
                "OpenAI response generated",
                model=self.model_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
                cost_usd=cost,
                finish_reason=finish_reason
            )
            
            return model_response
            
        except openai.APITimeoutError as e:
            raise ModelError(
                f"OpenAI request timeout: {str(e)}",
                model_id=self.model_id,
                provider=self.provider_name,
                error_code="TIMEOUT",
                retryable=True
            )
        except openai.RateLimitError as e:
            raise ModelError(
                f"OpenAI rate limit exceeded: {str(e)}",
                model_id=self.model_id,
                provider=self.provider_name,
                error_code="RATE_LIMIT",
                retryable=True
            )
        except openai.APIError as e:
            raise ModelError(
                f"OpenAI API error: {str(e)}",
                model_id=self.model_id,
                provider=self.provider_name,
                error_code="API_ERROR",
                retryable=False
            )
        except Exception as e:
            logger.error(
                "Unexpected error in OpenAI integration",
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
        """Stream response from OpenAI model."""
        await self.validate_request(prompt, max_tokens)
        
        try:
            # Prepare request parameters
            request_params = {
                "model": self.model_id,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "stream": True,
                **kwargs
            }
            
            if max_tokens:
                request_params["max_tokens"] = max_tokens
            
            logger.debug(
                "Starting OpenAI stream",
                model=self.model_id,
                prompt_length=len(prompt)
            )
            
            # Make streaming API call
            stream = await self.client.chat.completions.create(**request_params)
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(
                "Error in OpenAI streaming",
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
        """Check OpenAI API health."""
        try:
            # Simple API call to check health
            response = await self.client.chat.completions.create(
                model=self.model_id,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1,
                temperature=0
            )
            
            logger.debug("OpenAI health check passed", model=self.model_id)
            return True
            
        except Exception as e:
            logger.warning(
                "OpenAI health check failed",
                model=self.model_id,
                error=str(e)
            )
            return False
    
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for OpenAI request."""
        if self.model_id not in self.MODEL_COSTS:
            # Default cost estimation
            logger.warning(
                "Unknown model for cost estimation",
                model=self.model_id
            )
            return (input_tokens * 0.001 + output_tokens * 0.003) / 1000
        
        input_cost_per_1k, output_cost_per_1k = self.MODEL_COSTS[self.model_id]
        
        input_cost = (input_tokens / 1000) * input_cost_per_1k
        output_cost = (output_tokens / 1000) * output_cost_per_1k
        
        return input_cost + output_cost
    
    def get_max_context_length(self) -> int:
        """Get maximum context length for the model."""
        return self.MODEL_LIMITS.get(self.model_id, {}).get("context", 4096)
    
    def get_max_output_length(self) -> int:
        """Get maximum output length for the model."""
        return self.MODEL_LIMITS.get(self.model_id, {}).get("output", 4096)
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count using OpenAI's approximation."""
        # OpenAI estimation: ~4 characters per token for English
        # More accurate estimation could use tiktoken library
        return max(1, len(text) // 4)
    
    async def close(self) -> None:
        """Close the client connection."""
        if self._client:
            await self._client.close()
            self._client = None
