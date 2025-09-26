"""Model knowledge base using ChromaDB for RAG queries."""

import os
import asyncio
from typing import List, Dict, Any, Optional, Tuple
import chromadb
from chromadb.config import Settings
import structlog
from dataclasses import asdict

from .document_loader import DocumentLoader, DocumentChunk
from .embedding_service import EmbeddingService

logger = structlog.get_logger()


class ModelKnowledgeBase:
    """RAG-powered knowledge base for model information."""
    
    def __init__(
        self,
        persist_directory: str = "./data/chroma_db",
        collection_name: str = "model_knowledge",
        embedding_service: Optional[EmbeddingService] = None
    ):
        """Initialize the knowledge base.
        
        Args:
            persist_directory: Directory to persist ChromaDB data
            collection_name: Name of the ChromaDB collection
            embedding_service: Optional embedding service instance
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        
        # Initialize embedding service
        self.embedding_service = embedding_service or EmbeddingService()
        
        # Initialize ChromaDB
        self._client: Optional[chromadb.Client] = None
        self._collection: Optional[chromadb.Collection] = None
        
    @property
    def client(self) -> chromadb.Client:
        """Lazy load ChromaDB client."""
        if self._client is None:
            # Ensure persist directory exists
            os.makedirs(self.persist_directory, exist_ok=True)
            
            self._client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(allow_reset=True, anonymized_telemetry=False)
            )
            logger.info("ChromaDB client initialized", path=self.persist_directory)
            
        return self._client
    
    @property
    def collection(self) -> chromadb.Collection:
        """Get or create the ChromaDB collection."""
        if self._collection is None:
            try:
                self._collection = self.client.get_collection(
                    name=self.collection_name
                )
                logger.info("Retrieved existing collection", name=self.collection_name)
            except Exception:
                # Collection doesn't exist, create it
                self._collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"description": "Model knowledge base for routing decisions"}
                )
                logger.info("Created new collection", name=self.collection_name)
                
        return self._collection
    
    async def initialize_from_documents(
        self, 
        docs_directory: str,
        force_reload: bool = False
    ) -> None:
        """Initialize the knowledge base from model documentation.
        
        Args:
            docs_directory: Directory containing model documentation
            force_reload: Whether to force reload even if data exists
        """
        # Check if collection already has data
        if not force_reload:
            try:
                count = self.collection.count()
                if count > 0:
                    logger.info(
                        "Knowledge base already initialized",
                        documents=count
                    )
                    return
            except Exception as e:
                logger.warning("Error checking collection count", error=str(e))
        
        logger.info("Initializing knowledge base from documents", path=docs_directory)
        
        # Load documents
        doc_loader = DocumentLoader()
        chunks = doc_loader.load_documents(docs_directory)
        
        if not chunks:
            logger.warning("No documents found to load")
            return
        
        # Clear existing data if force reload
        if force_reload:
            try:
                self.client.delete_collection(self.collection_name)
                self._collection = None  # Reset collection reference
                logger.info("Cleared existing collection for reload")
            except Exception as e:
                logger.warning("Error clearing collection", error=str(e))
        
        # Add chunks to knowledge base
        await self._add_chunks(chunks)
        
        logger.info(
            "Knowledge base initialization complete",
            total_chunks=len(chunks)
        )
    
    async def _add_chunks(self, chunks: List[DocumentChunk]) -> None:
        """Add document chunks to the knowledge base.
        
        Args:
            chunks: List of document chunks to add
        """
        if not chunks:
            return
        
        # Generate embeddings for all chunks
        texts = [chunk.content for chunk in chunks]
        logger.info("Generating embeddings for chunks", count=len(texts))
        
        embeddings = await self.embedding_service.embed_texts(texts)
        
        # Prepare data for ChromaDB
        ids = [chunk.id for chunk in chunks]
        documents = [chunk.content for chunk in chunks]
        metadatas = []
        
        for chunk in chunks:
            # Convert metadata to strings (ChromaDB requirement)
            metadata = {}
            for key, value in chunk.metadata.items():
                if isinstance(value, (list, dict)):
                    metadata[key] = str(value)
                else:
                    metadata[key] = str(value)
            
            # Add chunk-specific metadata
            metadata.update({
                "source_file": chunk.source_file,
                "chunk_index": str(chunk.chunk_index),
                "start_char": str(chunk.start_char),
                "end_char": str(chunk.end_char)
            })
            
            metadatas.append(metadata)
        
        # Convert embeddings to list format
        embeddings_list = [embedding.tolist() for embedding in embeddings]
        
        # Add to ChromaDB
        try:
            self.collection.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings_list,
                metadatas=metadatas
            )
            logger.info("Successfully added chunks to knowledge base", count=len(chunks))
        except Exception as e:
            logger.error("Failed to add chunks to knowledge base", error=str(e))
            raise
    
    async def query(
        self,
        query_text: str,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
        similarity_threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        """Query the knowledge base for relevant information.
        
        Args:
            query_text: Text to search for
            n_results: Number of results to return
            where: Optional metadata filters
            similarity_threshold: Minimum similarity score (0.0 to 1.0)
            
        Returns:
            List of relevant documents with metadata
        """
        if not query_text.strip():
            logger.warning("Empty query text provided")
            return []
        
        # Generate embedding for query
        query_embedding = await self.embedding_service.embed_text(query_text)
        
        try:
            # Query ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=n_results,
                where=where
            )
            
            # Process results
            formatted_results = []
            
            if results["documents"] and results["documents"][0]:
                for i in range(len(results["documents"][0])):
                    # Calculate similarity score (ChromaDB returns distances)
                    distance = results["distances"][0][i] if results["distances"] else 0
                    similarity = 1 - distance  # Convert distance to similarity
                    
                    if similarity >= similarity_threshold:
                        result = {
                            "id": results["ids"][0][i],
                            "content": results["documents"][0][i],
                            "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                            "similarity": similarity,
                            "distance": distance
                        }
                        formatted_results.append(result)
            
            logger.debug(
                "Knowledge base query completed",
                query_length=len(query_text),
                results_found=len(formatted_results),
                filtered_by_threshold=n_results - len(formatted_results)
            )
            
            return formatted_results
            
        except Exception as e:
            logger.error("Error querying knowledge base", error=str(e))
            return []
    
    async def query_for_model_selection(
        self,
        task_description: str,
        task_type: str,
        complexity: str,
        constraints: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Specialized query for model selection.
        
        Args:
            task_description: Description of the task
            task_type: Type of task (e.g., 'reasoning', 'creative', 'code')
            complexity: Complexity level ('simple', 'medium', 'complex', 'expert')
            constraints: Optional constraints (cost, latency, quality)
            
        Returns:
            List of relevant model information
        """
        # Build comprehensive query
        query_parts = [
            task_description,
            f"task type: {task_type}",
            f"complexity: {complexity}"
        ]
        
        if constraints:
            if constraints.get("max_cost"):
                query_parts.append(f"cost under ${constraints['max_cost']}")
            if constraints.get("max_latency_ms"):
                query_parts.append(f"fast response under {constraints['max_latency_ms']}ms")
            if constraints.get("min_quality"):
                query_parts.append(f"high quality score above {constraints['min_quality']}")
        
        query_text = " ".join(query_parts)
        
        # Query with model-specific filters
        where_filter = {"doc_type": "model_documentation"}
        
        results = await self.query(
            query_text=query_text,
            n_results=10,  # Get more results for model selection
            where=where_filter,
            similarity_threshold=0.3  # Lower threshold for model selection
        )
        
        # Group results by model and aggregate information
        model_results = {}
        
        for result in results:
            model_id = result["metadata"].get("model_id", "unknown")
            
            if model_id not in model_results:
                model_results[model_id] = {
                    "model_id": model_id,
                    "relevance_score": 0.0,
                    "relevant_chunks": [],
                    "evidence": []
                }
            
            model_results[model_id]["relevant_chunks"].append(result)
            model_results[model_id]["relevance_score"] += result["similarity"]
            
            # Extract key evidence from content
            content = result["content"][:200] + "..." if len(result["content"]) > 200 else result["content"]
            model_results[model_id]["evidence"].append(content)
        
        # Calculate average relevance and sort
        for model_info in model_results.values():
            chunk_count = len(model_info["relevant_chunks"])
            if chunk_count > 0:
                model_info["relevance_score"] = model_info["relevance_score"] / chunk_count
        
        # Convert to sorted list
        sorted_results = sorted(
            model_results.values(),
            key=lambda x: x["relevance_score"],
            reverse=True
        )
        
        logger.info(
            "Model selection query completed",
            task_type=task_type,
            complexity=complexity,
            models_found=len(sorted_results)
        )
        
        return sorted_results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics.
        
        Returns:
            Dictionary with statistics
        """
        try:
            count = self.collection.count()
            
            # Get sample of metadata to understand content
            sample_results = self.collection.peek(limit=10)
            
            model_ids = set()
            doc_types = set()
            
            if sample_results["metadatas"]:
                for metadata in sample_results["metadatas"]:
                    if "model_id" in metadata:
                        model_ids.add(metadata["model_id"])
                    if "doc_type" in metadata:
                        doc_types.add(metadata["doc_type"])
            
            return {
                "total_documents": count,
                "collection_name": self.collection_name,
                "unique_models": len(model_ids),
                "model_ids": sorted(list(model_ids)),
                "document_types": sorted(list(doc_types)),
                "embedding_stats": self.embedding_service.get_cache_stats()
            }
            
        except Exception as e:
            logger.error("Error getting knowledge base stats", error=str(e))
            return {"error": str(e)}
    
    async def add_model_documentation(
        self,
        model_id: str,
        documentation: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add documentation for a specific model.
        
        Args:
            model_id: Identifier for the model
            documentation: Documentation text
            metadata: Optional additional metadata
        """
        # Create a temporary document chunk
        chunk_metadata = {
            "model_id": model_id,
            "doc_type": "model_documentation",
            "added_programmatically": True,
            **(metadata or {})
        }
        
        chunk = DocumentChunk(
            id=f"{model_id}_manual_doc",
            content=documentation,
            metadata=chunk_metadata,
            source_file="manual_addition",
            chunk_index=0,
            start_char=0,
            end_char=len(documentation)
        )
        
        await self._add_chunks([chunk])
        
        logger.info("Added manual documentation", model_id=model_id)
    
    def reset(self) -> None:
        """Reset the knowledge base (delete all data)."""
        try:
            self.client.delete_collection(self.collection_name)
            self._collection = None
            logger.info("Knowledge base reset successfully")
        except Exception as e:
            logger.error("Error resetting knowledge base", error=str(e))
