"""Ollama model integration for local models."""

import asyncio
import time
import json
from typing import Optional, AsyncGenerator, Dict, Any
import httpx
import structlog

from .base_model import BaseModelInterface, ModelResponse, ModelError

logger = structlog.get_logger()


class OllamaIntegration(BaseModelInterface):
    """Integration with Ollama for local models."""
    
    # Model context and output limits (estimates for common models)
    MODEL_LIMITS = {
        "llama3:8b": {"context": 8192, "output": 2048},
        "llama3:13b": {"context": 8192, "output": 2048},
        "llama3:70b": {"context": 8192, "output": 2048},
        "codellama:7b": {"context": 16384, "output": 4096},
        "codellama:13b": {"context": 16384, "output": 4096},
        "codellama:34b": {"context": 16384, "output": 4096},
        "mistral:7b": {"context": 8192, "output": 2048},
        "mixtral:8x7b": {"context": 32768, "output": 4096},
    }
    
    def __init__(
        self,
        model_id: str,
        api_key: Optional[str] = None,
        base_url: str = "http://localhost:11434",
        timeout: int = 60,  # Longer timeout for local models
        max_retries: int = 3
    ):
        """Initialize Ollama integration.
        
        Args:
            model_id: Ollama model identifier (e.g., 'llama3:8b')
            api_key: Not used for Ollama (local)
            base_url: Ollama server URL
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
        """
        super().__init__(model_id, api_key, base_url, timeout, max_retries)
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def provider_name(self) -> str:
        return "ollama"
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Lazy load HTTP client for Ollama."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                follow_redirects=True
            )
        return self._client
    
    async def generate_response(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ModelResponse:
        """Generate response from Ollama model."""
        start_time = time.time()
        
        await self.validate_request(prompt, max_tokens)
        
        try:
            # Prepare request payload
            payload = {
                "model": self.model_id,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    **kwargs
                }
            }
            
            if max_tokens:
                payload["options"]["num_predict"] = max_tokens
            
            logger.debug(
                "Sending Ollama request",
                model=self.model_id,
                prompt_length=len(prompt),
                temperature=temperature,
                max_tokens=max_tokens,
                base_url=self.base_url
            )
            
            # Make API call
            response = await self.client.post(
                "/api/generate",
                json=payload
            )
            
            # Check for HTTP errors
            response.raise_for_status()
            
            # Parse response
            result = response.json()
            
            # Calculate metrics
            latency_ms = (time.time() - start_time) * 1000
            
            # Extract response data
            content = result.get("response", "")
            
            # Estimate token usage (Ollama doesn't provide exact counts)
            input_tokens = self.estimate_tokens(prompt)
            output_tokens = self.estimate_tokens(content)
            total_tokens = input_tokens + output_tokens
            
            # Local models have zero API cost
            cost = 0.0
            
            # Extract additional metadata
            metadata = {
                "model": result.get("model", self.model_id),
                "created_at": result.get("created_at"),
                "done": result.get("done", True),
                "context": result.get("context", []),
                "total_duration": result.get("total_duration"),
                "load_duration": result.get("load_duration"),
                "prompt_eval_count": result.get("prompt_eval_count"),
                "prompt_eval_duration": result.get("prompt_eval_duration"),
                "eval_count": result.get("eval_count"),
                "eval_duration": result.get("eval_duration")
            }
            
            # Use eval_count for more accurate output token count if available
            if metadata.get("eval_count"):
                output_tokens = metadata["eval_count"]
                total_tokens = input_tokens + output_tokens
            
            model_response = ModelResponse(
                content=content,
                model_id=self.model_id,
                provider=self.provider_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                latency_ms=latency_ms,
                cost_usd=cost,
                finish_reason="stop" if result.get("done") else "length",
                metadata=metadata
            )
            
            logger.info(
                "Ollama response generated",
                model=self.model_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
                eval_duration_ms=metadata.get("eval_duration", 0) / 1_000_000 if metadata.get("eval_duration") else None
            )
            
            return model_response
            
        except httpx.TimeoutException as e:
            raise ModelError(
                f"Ollama request timeout: {str(e)}",
                model_id=self.model_id,
                provider=self.provider_name,
                error_code="TIMEOUT",
                retryable=True
            )
        except httpx.ConnectError as e:
            raise ModelError(
                f"Cannot connect to Ollama server: {str(e)}",
                model_id=self.model_id,
                provider=self.provider_name,
                error_code="CONNECTION_ERROR",
                retryable=True
            )
        except httpx.HTTPStatusError as e:
            error_detail = "Unknown error"
            try:
                error_data = e.response.json()
                error_detail = error_data.get("error", str(e))
            except Exception:
                error_detail = str(e)
                
            raise ModelError(
                f"Ollama HTTP error: {error_detail}",
                model_id=self.model_id,
                provider=self.provider_name,
                error_code="HTTP_ERROR",
                retryable=e.response.status_code >= 500
            )
        except Exception as e:
            logger.error(
                "Unexpected error in Ollama integration",
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
        """Stream response from Ollama model."""
        await self.validate_request(prompt, max_tokens)
        
        try:
            # Prepare request payload
            payload = {
                "model": self.model_id,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": temperature,
                    **kwargs
                }
            }
            
            if max_tokens:
                payload["options"]["num_predict"] = max_tokens
            
            logger.debug(
                "Starting Ollama stream",
                model=self.model_id,
                prompt_length=len(prompt)
            )
            
            # Make streaming API call
            async with self.client.stream(
                "POST",
                "/api/generate",
                json=payload
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            chunk = json.loads(line)
                            if "response" in chunk:
                                yield chunk["response"]
                                
                            # Check if done
                            if chunk.get("done", False):
                                break
                                
                        except json.JSONDecodeError:
                            logger.warning(
                                "Invalid JSON in stream response",
                                line=line
                            )
                            continue
                            
        except Exception as e:
            logger.error(
                "Error in Ollama streaming",
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
        """Check Ollama server health."""
        try:
            # Check if server is running
            response = await self.client.get("/api/version")
            if response.status_code == 200:
                
                # Check if model is available
                model_response = await self.client.post(
                    "/api/show",
                    json={"name": self.model_id}
                )
                
                if model_response.status_code == 200:
                    logger.debug("Ollama health check passed", model=self.model_id)
                    return True
                else:
                    logger.warning(
                        "Ollama model not found",
                        model=self.model_id,
                        status=model_response.status_code
                    )
                    return False
            
            return False
            
        except Exception as e:
            logger.warning(
                "Ollama health check failed",
                model=self.model_id,
                error=str(e)
            )
            return False
    
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for Ollama request (always 0 for local models)."""
        return 0.0
    
    def get_max_context_length(self) -> int:
        """Get maximum context length for the model."""
        return self.MODEL_LIMITS.get(self.model_id, {}).get("context", 4096)
    
    def get_max_output_length(self) -> int:
        """Get maximum output length for the model."""
        return self.MODEL_LIMITS.get(self.model_id, {}).get("output", 2048)
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for local models."""
        # Conservative estimation for local models
        return max(1, len(text) // 3)
    
    async def list_available_models(self) -> list[Dict[str, Any]]:
        """List available models on the Ollama server."""
        try:
            response = await self.client.get("/api/tags")
            response.raise_for_status()
            
            data = response.json()
            return data.get("models", [])
            
        except Exception as e:
            logger.error("Failed to list Ollama models", error=str(e))
            return []
    
    async def pull_model(self, model_name: str) -> bool:
        """Pull a model to the Ollama server."""
        try:
            logger.info("Pulling Ollama model", model=model_name)
            
            # Start model pull
            async with self.client.stream(
                "POST",
                "/api/pull",
                json={"name": model_name}
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            status = json.loads(line)
                            logger.debug(
                                "Model pull progress",
                                model=model_name,
                                status=status.get("status"),
                                completed=status.get("completed"),
                                total=status.get("total")
                            )
                            
                            if status.get("status") == "success":
                                logger.info("Model pull completed", model=model_name)
                                return True
                                
                        except json.JSONDecodeError:
                            continue
            
            return False
            
        except Exception as e:
            logger.error(
                "Failed to pull model",
                model=model_name,
                error=str(e)
            )
            return False
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
