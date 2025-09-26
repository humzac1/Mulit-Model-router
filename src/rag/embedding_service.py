"""Embedding service for converting text to vector representations."""

import asyncio
from typing import List, Optional, Dict, Any
import numpy as np
from sentence_transformers import SentenceTransformer
import structlog
from functools import lru_cache

logger = structlog.get_logger()


class EmbeddingService:
    """Service for generating embeddings from text."""
    
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        device: Optional[str] = None,
        cache_size: int = 1000
    ):
        """Initialize the embedding service.
        
        Args:
            model_name: Name of the sentence transformer model
            device: Device to run model on (cpu, cuda, mps)
            cache_size: Size of the embedding cache
        """
        self.model_name = model_name
        self.device = device
        self.cache_size = cache_size
        self._model: Optional[SentenceTransformer] = None
        self._embedding_dim: Optional[int] = None
        
        # Cache for embeddings
        self._cache: Dict[str, np.ndarray] = {}
        
    @property
    def model(self) -> SentenceTransformer:
        """Lazy load the sentence transformer model."""
        if self._model is None:
            logger.info("Loading embedding model", model=self.model_name)
            self._model = SentenceTransformer(self.model_name, device=self.device)
            
            # Get embedding dimension
            test_embedding = self._model.encode(["test"])
            self._embedding_dim = len(test_embedding[0])
            logger.info("Embedding model loaded", dimension=self._embedding_dim)
            
        return self._model
    
    @property 
    def embedding_dimension(self) -> int:
        """Get the embedding dimension."""
        if self._embedding_dim is None:
            # Trigger model loading to get dimension
            _ = self.model
        return self._embedding_dim
    
    def _get_cache_key(self, text: str) -> str:
        """Generate a cache key for text."""
        return hash(text.strip().lower())
    
    def _manage_cache_size(self) -> None:
        """Ensure cache doesn't exceed maximum size."""
        if len(self._cache) > self.cache_size:
            # Remove oldest 20% of entries
            items_to_remove = len(self._cache) - int(self.cache_size * 0.8)
            keys_to_remove = list(self._cache.keys())[:items_to_remove]
            for key in keys_to_remove:
                del self._cache[key]
    
    async def embed_text(self, text: str) -> np.ndarray:
        """Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            Numpy array containing the embedding
        """
        if not text.strip():
            logger.warning("Empty text provided for embedding")
            return np.zeros(self.embedding_dimension)
            
        cache_key = self._get_cache_key(text)
        
        # Check cache first
        if cache_key in self._cache:
            logger.debug("Using cached embedding", text_length=len(text))
            return self._cache[cache_key]
        
        # Generate embedding
        logger.debug("Generating new embedding", text_length=len(text))
        
        # Run embedding in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(
            None, 
            lambda: self.model.encode([text])[0]
        )
        
        # Cache the result
        self._cache[cache_key] = embedding
        self._manage_cache_size()
        
        return embedding
    
    async def embed_texts(self, texts: List[str]) -> List[np.ndarray]:
        """Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of numpy arrays containing embeddings
        """
        if not texts:
            return []
        
        # Filter out empty texts
        processed_texts = []
        text_indices = []
        
        for i, text in enumerate(texts):
            if text.strip():
                processed_texts.append(text)
                text_indices.append(i)
        
        if not processed_texts:
            logger.warning("No valid texts provided for embedding")
            return [np.zeros(self.embedding_dimension) for _ in texts]
        
        # Check cache for existing embeddings
        cached_embeddings = {}
        texts_to_embed = []
        embed_indices = []
        
        for i, text in enumerate(processed_texts):
            cache_key = self._get_cache_key(text)
            if cache_key in self._cache:
                cached_embeddings[i] = self._cache[cache_key]
            else:
                texts_to_embed.append(text)
                embed_indices.append(i)
        
        # Generate embeddings for uncached texts
        if texts_to_embed:
            logger.debug(
                "Generating embeddings", 
                total_texts=len(texts),
                cached=len(cached_embeddings),
                to_embed=len(texts_to_embed)
            )
            
            # Run embedding in thread pool
            loop = asyncio.get_event_loop()
            new_embeddings = await loop.run_in_executor(
                None,
                lambda: self.model.encode(texts_to_embed)
            )
            
            # Cache new embeddings
            for i, embedding in enumerate(new_embeddings):
                text_idx = embed_indices[i]
                text = processed_texts[text_idx]
                cache_key = self._get_cache_key(text)
                self._cache[cache_key] = embedding
                cached_embeddings[text_idx] = embedding
            
            self._manage_cache_size()
        
        # Reconstruct full results list
        results = []
        for i, original_text in enumerate(texts):
            if i in text_indices:
                processed_idx = text_indices.index(i)
                if processed_idx in cached_embeddings:
                    results.append(cached_embeddings[processed_idx])
                else:
                    results.append(np.zeros(self.embedding_dimension))
            else:
                results.append(np.zeros(self.embedding_dimension))
        
        return results
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        return {
            "cache_size": len(self._cache),
            "max_cache_size": self.cache_size,
            "model_name": self.model_name,
            "embedding_dimension": self.embedding_dimension,
            "device": self.device
        }
    
    def clear_cache(self) -> None:
        """Clear the embedding cache."""
        self._cache.clear()
        logger.info("Embedding cache cleared")
    
    def preload_model(self) -> None:
        """Preload the embedding model (useful for startup)."""
        logger.info("Preloading embedding model")
        _ = self.model
        logger.info("Embedding model preloaded successfully")
