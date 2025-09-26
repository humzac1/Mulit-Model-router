"""Factory for creating model integrations."""

import os
from typing import Dict, Type, Optional, Any
import structlog

from .base_model import BaseModelInterface
from .openai_integration import OpenAIIntegration
from .anthropic_integration import AnthropicIntegration
from .ollama_integration import OllamaIntegration
from ..models.model_config import ModelProvider

logger = structlog.get_logger()


class ModelFactory:
    """Factory class for creating model integrations."""
    
    # Registry of available integrations
    _integrations: Dict[ModelProvider, Type[BaseModelInterface]] = {
        ModelProvider.OPENAI: OpenAIIntegration,
        ModelProvider.ANTHROPIC: AnthropicIntegration,
        ModelProvider.OLLAMA: OllamaIntegration,
    }
    
    @classmethod
    def create_model(
        self,
        provider: ModelProvider,
        model_id: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        **kwargs
    ) -> BaseModelInterface:
        """Create a model integration instance.
        
        Args:
            provider: Model provider (openai, anthropic, ollama)
            model_id: Specific model identifier
            api_key: API key for authentication (if required)
            base_url: Custom base URL (optional)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Model integration instance
            
        Raises:
            ValueError: If provider is not supported
            EnvironmentError: If required API key is missing
        """
        if provider not in self._integrations:
            supported = list(self._integrations.keys())
            raise ValueError(
                f"Unsupported provider: {provider}. "
                f"Supported providers: {supported}"
            )
        
        integration_class = self._integrations[provider]
        
        # Handle API key resolution
        resolved_api_key = self._resolve_api_key(provider, api_key)
        
        # Handle provider-specific defaults
        provider_kwargs = self._get_provider_defaults(provider, **kwargs)
        
        try:
            integration = integration_class(
                model_id=model_id,
                api_key=resolved_api_key,
                base_url=base_url,
                timeout=timeout,
                max_retries=max_retries,
                **provider_kwargs
            )
            
            logger.info(
                "Created model integration",
                provider=provider.value,
                model_id=model_id,
                has_api_key=bool(resolved_api_key),
                base_url=base_url
            )
            
            return integration
            
        except Exception as e:
            logger.error(
                "Failed to create model integration",
                provider=provider.value,
                model_id=model_id,
                error=str(e)
            )
            raise
    
    @classmethod
    def create_from_config(self, config: Dict[str, Any]) -> BaseModelInterface:
        """Create model integration from configuration.
        
        Args:
            config: Model configuration dictionary
            
        Returns:
            Model integration instance
        """
        # Extract required fields
        provider_str = config.get("provider")
        model_id = config.get("model_id")
        
        if not provider_str:
            raise ValueError("Missing 'provider' in config")
        if not model_id:
            raise ValueError("Missing 'model_id' in config")
        
        # Convert provider string to enum
        try:
            provider = ModelProvider(provider_str)
        except ValueError:
            raise ValueError(f"Invalid provider: {provider_str}")
        
        # Extract optional fields
        api_key_env = config.get("api_key_env")
        api_key = None
        if api_key_env:
            api_key = os.getenv(api_key_env)
        
        base_url = config.get("endpoint_url")
        timeout = config.get("timeout", 30)
        max_retries = config.get("max_retries", 3)
        
        # Extract additional parameters
        default_params = config.get("default_parameters", {})
        
        return self.create_model(
            provider=provider,
            model_id=model_id,
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            **default_params
        )
    
    @classmethod
    def _resolve_api_key(
        self, 
        provider: ModelProvider, 
        api_key: Optional[str]
    ) -> Optional[str]:
        """Resolve API key from parameter or environment."""
        if api_key:
            return api_key
        
        # Try common environment variable names
        env_var_map = {
            ModelProvider.OPENAI: "OPENAI_API_KEY",
            ModelProvider.ANTHROPIC: "ANTHROPIC_API_KEY",
            ModelProvider.OLLAMA: None,  # Ollama doesn't need API key
        }
        
        env_var = env_var_map.get(provider)
        if env_var:
            api_key = os.getenv(env_var)
            if not api_key:
                logger.warning(
                    f"No API key found for {provider.value}. "
                    f"Set {env_var} environment variable."
                )
            return api_key
        
        return None
    
    @classmethod
    def _get_provider_defaults(
        self, 
        provider: ModelProvider, 
        **kwargs
    ) -> Dict[str, Any]:
        """Get provider-specific default parameters."""
        defaults = {}
        
        if provider == ModelProvider.OLLAMA:
            # Ollama-specific defaults
            defaults.update({
                "base_url": kwargs.get("base_url", "http://localhost:11434"),
                "timeout": kwargs.get("timeout", 60)  # Longer timeout for local models
            })
        
        # Add any additional kwargs
        for key, value in kwargs.items():
            if key not in defaults:
                defaults[key] = value
        
        return defaults
    
    @classmethod
    def get_supported_providers(self) -> list[ModelProvider]:
        """Get list of supported providers.
        
        Returns:
            List of supported model providers
        """
        return list(self._integrations.keys())
    
    @classmethod
    def register_integration(
        self,
        provider: ModelProvider,
        integration_class: Type[BaseModelInterface]
    ) -> None:
        """Register a new model integration.
        
        Args:
            provider: Model provider enum
            integration_class: Integration class that extends BaseModelInterface
        """
        if not issubclass(integration_class, BaseModelInterface):
            raise ValueError(
                "Integration class must extend BaseModelInterface"
            )
        
        self._integrations[provider] = integration_class
        
        logger.info(
            "Registered new model integration",
            provider=provider.value,
            class_name=integration_class.__name__
        )
    
    @classmethod
    async def test_integration(
        self,
        provider: ModelProvider,
        model_id: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None
    ) -> bool:
        """Test if a model integration is working.
        
        Args:
            provider: Model provider
            model_id: Model identifier
            api_key: API key (optional)
            base_url: Base URL (optional)
            
        Returns:
            True if integration is working, False otherwise
        """
        try:
            integration = self.create_model(
                provider=provider,
                model_id=model_id,
                api_key=api_key,
                base_url=base_url
            )
            
            # Test health check
            is_healthy = await integration.check_health()
            
            # Clean up
            if hasattr(integration, 'close'):
                await integration.close()
            
            logger.info(
                "Integration test completed",
                provider=provider.value,
                model_id=model_id,
                healthy=is_healthy
            )
            
            return is_healthy
            
        except Exception as e:
            logger.error(
                "Integration test failed",
                provider=provider.value,
                model_id=model_id,
                error=str(e)
            )
            return False
