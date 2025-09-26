"""Main routing engine that coordinates all components."""

import asyncio
import time
from typing import Dict, List, Optional, Any
import structlog

from ..models.prompt import PromptRequest, PromptAnalysis, PromptResponse
from ..models.routing import (
    RoutingDecision, RoutingScore, RoutingContext, 
    RoutingStrategy, RoutingReason
)
from ..models.model_config import ModelConfig
from ..rag.knowledge_base import ModelKnowledgeBase
from ..integrations.model_factory import ModelFactory
from ..integrations.base_model import BaseModelInterface, ModelError
from .prompt_analyzer import PromptAnalyzer
from .model_selector import ModelSelector

logger = structlog.get_logger()


class RoutingEngine:
    """Main routing engine that coordinates all components."""
    
    def __init__(
        self,
        models: List[ModelConfig],
        knowledge_base: ModelKnowledgeBase,
        model_factory: ModelFactory = None
    ):
        """Initialize the routing engine.
        
        Args:
            models: List of available model configurations
            knowledge_base: RAG knowledge base for model selection
            model_factory: Factory for creating model integrations
        """
        self.models = {model.model_id: model for model in models}
        self.knowledge_base = knowledge_base
        self.model_factory = model_factory or ModelFactory()
        
        # Initialize components
        self.prompt_analyzer = PromptAnalyzer()
        self.model_selector = ModelSelector(models)
        
        # Cache for model integrations
        self._model_cache: Dict[str, BaseModelInterface] = {}
        
    async def route_and_execute(
        self,
        request: PromptRequest,
        routing_context: Optional[RoutingContext] = None
    ) -> PromptResponse:
        """Route request to appropriate model and execute.
        
        Args:
            request: Incoming prompt request
            routing_context: Optional routing context with constraints
            
        Returns:
            Response from the selected model
        """
        start_time = time.time()
        request_id = f"req_{int(time.time() * 1000)}"
        
        try:
            # Step 1: Analyze the prompt
            logger.info(
                "Starting request routing",
                request_id=request_id,
                prompt_length=len(request.prompt),
                user_id=request.user_id
            )
            
            analysis = await self.prompt_analyzer.analyze_prompt(request.prompt)
            
            # Step 2: Make routing decision
            routing_decision = await self.make_routing_decision(
                request, analysis, routing_context
            )
            
            logger.info(
                "Routing decision made",
                request_id=request_id,
                selected_model=routing_decision.selected_model,
                strategy=routing_decision.strategy_used.value,
                confidence=routing_decision.confidence
            )
            
            # Step 3: Execute request with selected model
            response = await self._execute_with_model(
                request, routing_decision, analysis
            )
            
            # Step 4: Add routing metadata to response
            response.request_id = request_id
            response.routing_confidence = routing_decision.confidence
            
            total_time = (time.time() - start_time) * 1000
            logger.info(
                "Request completed successfully",
                request_id=request_id,
                model=response.selected_model,
                total_time_ms=total_time,
                model_latency_ms=response.model_latency_ms,
                cost=response.total_cost
            )
            
            return response
            
        except Exception as e:
            logger.error(
                "Request failed",
                request_id=request_id,
                error=str(e),
                exc_info=True
            )
            raise
    
    async def make_routing_decision(
        self,
        request: PromptRequest,
        analysis: PromptAnalysis,
        routing_context: Optional[RoutingContext] = None
    ) -> RoutingDecision:
        """Make routing decision without executing the request.
        
        Args:
            request: Prompt request
            analysis: Prompt analysis results
            routing_context: Optional routing context
            
        Returns:
            Routing decision with selected model and reasoning
        """
        start_time = time.time()
        
        # Create default routing context if not provided
        if routing_context is None:
            routing_context = RoutingContext(
                max_cost=request.constraints.get("max_cost"),
                max_latency_ms=request.constraints.get("max_latency_ms"),
                min_quality=request.constraints.get("min_quality"),
                preferred_models=request.preferred_models,
                user_id=request.user_id,
                session_id=request.session_id
            )
        
        # Query knowledge base for relevant model information
        rag_start = time.time()
        rag_results = await self._query_knowledge_base(analysis, routing_context)
        rag_time = (time.time() - rag_start) * 1000
        
        # Score all available models
        scores = await self.model_selector.score_models(
            analysis, routing_context, rag_results
        )
        
        if not scores:
            raise ValueError("No models available for routing")
        
        # Select the best model
        selected_score = scores[0]
        selected_model = selected_score.model_id
        
        # Determine strategy used
        strategy = self._determine_strategy(routing_context, selected_score, rag_results)
        
        # Determine primary reason for selection
        primary_reason = self._determine_primary_reason(
            selected_score, analysis, routing_context
        )
        
        # Get fallback models
        fallback_models = self.model_selector.get_fallback_models(
            selected_model, scores, max_fallbacks=3
        )
        
        # Calculate decision confidence
        confidence = self._calculate_decision_confidence(scores, analysis)
        
        decision_time = (time.time() - start_time) * 1000
        
        decision = RoutingDecision(
            selected_model=selected_model,
            fallback_models=fallback_models,
            strategy_used=strategy,
            primary_reason=primary_reason,
            secondary_reasons=self._get_secondary_reasons(selected_score),
            candidate_scores=scores,
            confidence=confidence,
            expected_quality=selected_score.quality_score,
            expected_cost=selected_score.estimated_cost,
            expected_latency_ms=selected_score.estimated_latency_ms,
            rag_query_used=self._build_rag_query(analysis, routing_context),
            rag_results_count=len(rag_results) if rag_results else 0,
            rag_total_time_ms=rag_time,
            decision_time_ms=decision_time
        )
        
        logger.debug(
            "Routing decision details",
            selected_model=selected_model,
            confidence=confidence,
            expected_cost=selected_score.estimated_cost,
            expected_latency_ms=selected_score.estimated_latency_ms,
            candidates_evaluated=len(scores),
            rag_results=len(rag_results) if rag_results else 0
        )
        
        return decision
    
    async def _query_knowledge_base(
        self,
        analysis: PromptAnalysis,
        context: RoutingContext
    ) -> List[Dict[str, Any]]:
        """Query the knowledge base for relevant model information."""
        try:
            results = await self.knowledge_base.query_for_model_selection(
                task_description=f"Task type: {analysis.task_type.value}, "
                                f"complexity: {analysis.complexity.value}, "
                                f"domain: {analysis.domain.value}",
                task_type=analysis.task_type.value,
                complexity=analysis.complexity.value,
                constraints={
                    "max_cost": context.max_cost,
                    "max_latency_ms": context.max_latency_ms,
                    "min_quality": context.min_quality
                }
            )
            
            logger.debug(
                "Knowledge base query completed",
                results_count=len(results),
                task_type=analysis.task_type.value,
                complexity=analysis.complexity.value
            )
            
            return results
            
        except Exception as e:
            logger.warning(
                "Knowledge base query failed",
                error=str(e)
            )
            return []
    
    def _build_rag_query(self, analysis: PromptAnalysis, context: RoutingContext) -> str:
        """Build the RAG query string used for model selection."""
        query_parts = [
            f"task: {analysis.task_type.value}",
            f"complexity: {analysis.complexity.value}",
            f"domain: {analysis.domain.value}"
        ]
        
        if context.max_cost:
            query_parts.append(f"cost under ${context.max_cost}")
        if context.max_latency_ms:
            query_parts.append(f"latency under {context.max_latency_ms}ms")
        if context.min_quality:
            query_parts.append(f"quality above {context.min_quality}")
        
        return " ".join(query_parts)
    
    def _determine_strategy(
        self,
        context: RoutingContext,
        selected_score: RoutingScore,
        rag_results: List[Dict[str, Any]]
    ) -> RoutingStrategy:
        """Determine which strategy was primarily used."""
        if rag_results and selected_score.rag_similarity and selected_score.rag_similarity > 0.7:
            return RoutingStrategy.RAG_BASED
        elif context.max_cost and selected_score.cost_score > 0.8:
            return RoutingStrategy.COST_OPTIMIZED
        elif context.max_latency_ms and selected_score.latency_score > 0.8:
            return RoutingStrategy.LATENCY_OPTIMIZED
        elif context.min_quality and selected_score.quality_score > 0.8:
            return RoutingStrategy.QUALITY_OPTIMIZED
        else:
            return RoutingStrategy.HYBRID
    
    def _determine_primary_reason(
        self,
        selected_score: RoutingScore,
        analysis: PromptAnalysis,
        context: RoutingContext
    ) -> RoutingReason:
        """Determine the primary reason for model selection."""
        if context.preferred_models and selected_score.model_id in context.preferred_models:
            return RoutingReason.USER_PREFERENCE
        elif selected_score.capability_score > 0.9:
            return RoutingReason.BEST_CAPABILITIES
        elif context.max_cost and selected_score.cost_score > 0.8:
            return RoutingReason.COST_CONSTRAINT
        elif context.max_latency_ms and selected_score.latency_score > 0.8:
            return RoutingReason.LATENCY_CONSTRAINT
        else:
            return RoutingReason.BEST_CAPABILITIES
    
    def _get_secondary_reasons(self, selected_score: RoutingScore) -> List[RoutingReason]:
        """Get secondary reasons for the selection."""
        reasons = []
        
        if selected_score.cost_score > 0.7:
            reasons.append(RoutingReason.COST_CONSTRAINT)
        if selected_score.latency_score > 0.7:
            reasons.append(RoutingReason.LATENCY_CONSTRAINT)
        if selected_score.availability_score > 0.95:
            # High availability could be a factor
            pass
        
        return reasons[:2]  # Limit to top 2 secondary reasons
    
    def _calculate_decision_confidence(
        self,
        scores: List[RoutingScore],
        analysis: PromptAnalysis
    ) -> float:
        """Calculate confidence in the routing decision."""
        if len(scores) < 2:
            return 0.8  # Moderate confidence with only one option
        
        # Check score separation between top models
        top_score = scores[0].final_score
        second_score = scores[1].final_score
        
        score_gap = top_score - second_score
        
        # Higher gap = higher confidence
        if score_gap > 0.3:
            confidence = 0.95
        elif score_gap > 0.2:
            confidence = 0.85
        elif score_gap > 0.1:
            confidence = 0.75
        else:
            confidence = 0.65
        
        # Adjust based on analysis confidence
        confidence = confidence * 0.8 + analysis.confidence * 0.2
        
        return min(1.0, max(0.1, confidence))
    
    async def _execute_with_model(
        self,
        request: PromptRequest,
        decision: RoutingDecision,
        analysis: PromptAnalysis
    ) -> PromptResponse:
        """Execute the request with the selected model."""
        selected_model_id = decision.selected_model
        
        # Try the selected model first
        try:
            model_integration = await self._get_model_integration(selected_model_id)
            response = await self._call_model(
                model_integration, request, analysis
            )
            response.fallback_used = False
            return response
            
        except ModelError as e:
            logger.warning(
                "Selected model failed, trying fallbacks",
                selected_model=selected_model_id,
                error=str(e),
                retryable=e.retryable
            )
            
            # Try fallback models
            for fallback_model_id in decision.fallback_models:
                try:
                    model_integration = await self._get_model_integration(fallback_model_id)
                    response = await self._call_model(
                        model_integration, request, analysis
                    )
                    response.fallback_used = True
                    response.selected_model = fallback_model_id
                    
                    logger.info(
                        "Fallback model succeeded",
                        original_model=selected_model_id,
                        fallback_model=fallback_model_id
                    )
                    
                    return response
                    
                except ModelError as fallback_error:
                    logger.warning(
                        "Fallback model also failed",
                        fallback_model=fallback_model_id,
                        error=str(fallback_error)
                    )
                    continue
            
            # All models failed
            raise ModelError(
                f"All models failed. Original error: {str(e)}",
                model_id=selected_model_id,
                provider="routing_engine",
                error_code="ALL_MODELS_FAILED"
            )
    
    async def _get_model_integration(self, model_id: str) -> BaseModelInterface:
        """Get or create model integration instance."""
        if model_id in self._model_cache:
            return self._model_cache[model_id]
        
        if model_id not in self.models:
            raise ValueError(f"Unknown model: {model_id}")
        
        model_config = self.models[model_id]
        
        # Create integration using factory
        integration = self.model_factory.create_from_config(
            model_config.dict()
        )
        
        # Cache the integration
        self._model_cache[model_id] = integration
        
        return integration
    
    async def _call_model(
        self,
        model: BaseModelInterface,
        request: PromptRequest,
        analysis: PromptAnalysis
    ) -> PromptResponse:
        """Call the model and create a standardized response."""
        start_time = time.time()
        
        # Prepare model parameters
        temperature = request.metadata.get("temperature", 0.7)
        max_tokens = request.metadata.get("max_tokens")
        
        # Call the model
        model_response = await model.generate_response(
            prompt=request.prompt,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Create standardized response
        total_latency = (time.time() - start_time) * 1000
        
        response = PromptResponse(
            request_id="",  # Will be set by caller
            selected_model=model_response.model_id,
            response_text=model_response.content,
            total_latency_ms=total_latency,
            model_latency_ms=model_response.latency_ms,
            total_cost=model_response.cost_usd,
            input_tokens=model_response.input_tokens,
            output_tokens=model_response.output_tokens,
            quality_score=None,  # Could be calculated by a quality evaluator
            fallback_used=False,
            routing_confidence=0.0,  # Will be set by caller
            metadata={
                "model_provider": model_response.provider,
                "finish_reason": model_response.finish_reason,
                "model_metadata": model_response.metadata
            }
        )
        
        return response
    
    async def get_model_health(self) -> Dict[str, bool]:
        """Check health of all models.
        
        Returns:
            Dictionary mapping model IDs to health status
        """
        health_status = {}
        
        tasks = []
        for model_id in self.models:
            if self.models[model_id].is_enabled:
                task = self._check_single_model_health(model_id)
                tasks.append((model_id, task))
        
        # Run health checks concurrently
        results = await asyncio.gather(
            *[task for _, task in tasks],
            return_exceptions=True
        )
        
        for (model_id, _), result in zip(tasks, results):
            if isinstance(result, Exception):
                health_status[model_id] = False
                logger.warning(
                    "Health check failed",
                    model_id=model_id,
                    error=str(result)
                )
            else:
                health_status[model_id] = result
        
        return health_status
    
    async def _check_single_model_health(self, model_id: str) -> bool:
        """Check health of a single model."""
        try:
            integration = await self._get_model_integration(model_id)
            return await integration.check_health()
        except Exception as e:
            logger.warning(
                "Model health check failed",
                model_id=model_id,
                error=str(e)
            )
            return False
    
    async def close(self) -> None:
        """Clean up resources."""
        # Close all cached model integrations
        for integration in self._model_cache.values():
            try:
                if hasattr(integration, 'close'):
                    await integration.close()
            except Exception as e:
                logger.warning(
                    "Error closing model integration",
                    error=str(e)
                )
        
        self._model_cache.clear()
        logger.info("Routing engine closed")
