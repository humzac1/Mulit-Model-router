"""Model selection logic based on analysis and constraints."""

import asyncio
from typing import List, Dict, Any, Optional
import structlog

from ..models.prompt import PromptAnalysis
from ..models.routing import RoutingScore, RoutingContext, RoutingStrategy, RoutingReason
from ..models.model_config import ModelConfig

logger = structlog.get_logger()


class ModelSelector:
    """Selects the best model based on analysis and constraints."""
    
    def __init__(self, models: List[ModelConfig]):
        """Initialize the model selector.
        
        Args:
            models: List of available model configurations
        """
        self.models = {model.model_id: model for model in models}
        self.enabled_models = {
            model_id: model for model_id, model in self.models.items()
            if model.is_enabled
        }
        
    async def score_models(
        self,
        analysis: PromptAnalysis,
        context: RoutingContext,
        rag_results: Optional[List[Dict[str, Any]]] = None
    ) -> List[RoutingScore]:
        """Score all available models for the given prompt.
        
        Args:
            analysis: Prompt analysis results
            context: Routing context with constraints and preferences
            rag_results: Optional RAG query results for additional scoring
            
        Returns:
            List of routing scores for each model
        """
        scores = []
        
        # Filter models based on preferences and constraints
        candidate_models = self._filter_candidates(context)
        
        for model_id, model in candidate_models.items():
            try:
                score = await self._score_model(
                    model, analysis, context, rag_results
                )
                scores.append(score)
                
            except Exception as e:
                logger.warning(
                    "Failed to score model",
                    model_id=model_id,
                    error=str(e)
                )
                # Continue with other models
                continue
        
        # Sort by final score (descending)
        scores.sort(key=lambda x: x.final_score, reverse=True)
        
        logger.debug(
            "Model scoring completed",
            candidates=len(candidate_models),
            scored=len(scores),
            top_model=scores[0].model_id if scores else None
        )
        
        return scores
    
    def _filter_candidates(self, context: RoutingContext) -> Dict[str, ModelConfig]:
        """Filter models based on preferences and exclusions.
        
        Args:
            context: Routing context
            
        Returns:
            Dictionary of candidate models
        """
        candidates = self.enabled_models.copy()
        
        # Remove excluded models
        for excluded_model in context.excluded_models:
            candidates.pop(excluded_model, None)
        
        # If preferred models are specified, prioritize them
        if context.preferred_models:
            preferred_candidates = {}
            for preferred_model in context.preferred_models:
                if preferred_model in candidates:
                    preferred_candidates[preferred_model] = candidates[preferred_model]
            
            # If we have preferred models available, use only those
            if preferred_candidates:
                candidates = preferred_candidates
        
        return candidates
    
    async def _score_model(
        self,
        model: ModelConfig,
        analysis: PromptAnalysis,
        context: RoutingContext,
        rag_results: Optional[List[Dict[str, Any]]] = None
    ) -> RoutingScore:
        """Score a single model.
        
        Args:
            model: Model configuration
            analysis: Prompt analysis
            context: Routing context
            rag_results: RAG query results
            
        Returns:
            Routing score for the model
        """
        # Calculate capability score
        capability_score = self._calculate_capability_score(model, analysis)
        
        # Calculate cost score
        cost_score, estimated_cost = self._calculate_cost_score(
            model, analysis, context
        )
        
        # Calculate latency score
        latency_score, estimated_latency = self._calculate_latency_score(
            model, analysis, context
        )
        
        # Calculate availability score
        availability_score = self._calculate_availability_score(model)
        
        # Calculate quality score
        quality_score = self._calculate_quality_score(model, analysis)
        
        # Calculate RAG-based score
        rag_similarity, rag_evidence = self._calculate_rag_score(
            model, rag_results
        )
        
        # Calculate weighted score
        weighted_score = (
            capability_score * context.capability_weight +
            cost_score * context.cost_weight +
            latency_score * context.latency_weight +
            quality_score * (1 - context.capability_weight - context.cost_weight - context.latency_weight)
        )
        
        # Apply RAG boost if available
        if rag_similarity is not None:
            weighted_score = weighted_score * 0.8 + rag_similarity * 0.2
        
        # Check constraints
        meets_constraints = self._check_constraints(
            model, estimated_cost, estimated_latency, context
        )
        
        # Final score adjustment
        final_score = weighted_score
        if not meets_constraints:
            final_score *= 0.1  # Heavily penalize constraint violations
        
        return RoutingScore(
            model_id=model.model_id,
            capability_score=capability_score,
            cost_score=cost_score,
            latency_score=latency_score,
            availability_score=availability_score,
            quality_score=quality_score,
            weighted_score=weighted_score,
            final_score=final_score,
            estimated_cost=estimated_cost,
            estimated_latency_ms=estimated_latency,
            meets_constraints=meets_constraints,
            rag_similarity=rag_similarity,
            rag_evidence=rag_evidence
        )
    
    def _calculate_capability_score(
        self, 
        model: ModelConfig, 
        analysis: PromptAnalysis
    ) -> float:
        """Calculate how well model capabilities match the task."""
        capabilities = model.capabilities
        
        # Base capability matching
        task_type = analysis.task_type.value
        capability_scores = []
        
        # Task-specific capability mapping
        if task_type in ["reasoning", "analysis"]:
            capability_scores.append(capabilities.reasoning_ability)
        elif task_type == "creative":
            capability_scores.append(capabilities.creative_ability)
        elif task_type == "code":
            capability_scores.append(capabilities.code_ability)
        elif task_type == "analysis":
            capability_scores.append(capabilities.analysis_ability)
        else:
            # For general tasks, use average of relevant capabilities
            capability_scores.extend([
                capabilities.reasoning_ability,
                capabilities.instruction_following,
                capabilities.factual_accuracy
            ])
        
        # Domain expertise
        domain = analysis.domain.value
        if domain in capabilities.domain_expertise:
            capability_scores.append(capabilities.domain_expertise[domain])
        
        # Task type preference
        if task_type in model.preferred_for_tasks:
            capability_scores.append(0.9)  # Boost for preferred tasks
        elif task_type in model.avoid_for_tasks:
            capability_scores.append(0.1)  # Penalty for avoided tasks
        
        # Context length requirement
        if analysis.context_length > capabilities.max_context_length:
            capability_scores.append(0.0)  # Cannot handle the context
        else:
            context_utilization = analysis.context_length / capabilities.max_context_length
            if context_utilization < 0.8:
                capability_scores.append(1.0)  # Good context headroom
            else:
                capability_scores.append(0.7)  # Tight on context
        
        # Output length requirement
        if analysis.expected_output_length > capabilities.max_output_length:
            capability_scores.append(0.3)  # May truncate output
        
        return sum(capability_scores) / len(capability_scores) if capability_scores else 0.0
    
    def _calculate_cost_score(
        self, 
        model: ModelConfig, 
        analysis: PromptAnalysis,
        context: RoutingContext
    ) -> tuple[float, float]:
        """Calculate cost score and estimated cost."""
        constraints = model.constraints
        
        # Estimate cost
        input_cost = (analysis.context_length / 1000) * constraints.input_cost_per_1k_tokens
        output_cost = (analysis.expected_output_length / 1000) * constraints.output_cost_per_1k_tokens
        estimated_cost = input_cost + output_cost
        
        # Score based on cost (lower cost = higher score)
        if estimated_cost == 0:
            cost_score = 1.0  # Free models get perfect score
        else:
            # Normalize against typical costs ($0.01 to $0.10)
            normalized_cost = min(estimated_cost / 0.05, 2.0)
            cost_score = max(0.0, 1.0 - normalized_cost / 2.0)
        
        return cost_score, estimated_cost
    
    def _calculate_latency_score(
        self, 
        model: ModelConfig, 
        analysis: PromptAnalysis,
        context: RoutingContext
    ) -> tuple[float, float]:
        """Calculate latency score and estimated latency."""
        constraints = model.constraints
        
        # Base latency
        estimated_latency = constraints.avg_latency_ms
        
        # Adjust for output length (longer outputs take more time)
        output_factor = max(1.0, analysis.expected_output_length / 1000)
        estimated_latency *= output_factor
        
        # Score based on latency (lower latency = higher score)
        # Normalize against typical latencies (100ms to 5000ms)
        normalized_latency = min(estimated_latency / 2500, 2.0)
        latency_score = max(0.0, 1.0 - normalized_latency / 2.0)
        
        return latency_score, estimated_latency
    
    def _calculate_availability_score(self, model: ModelConfig) -> float:
        """Calculate availability score."""
        return model.constraints.availability
    
    def _calculate_quality_score(
        self, 
        model: ModelConfig, 
        analysis: PromptAnalysis
    ) -> float:
        """Calculate expected quality score."""
        base_quality = model.constraints.avg_quality_score
        
        # Adjust for complexity
        complexity_factor = {
            "simple": 1.0,
            "medium": 0.95,
            "complex": 0.9,
            "expert": 0.85
        }.get(analysis.complexity.value, 0.9)
        
        return base_quality * complexity_factor
    
    def _calculate_rag_score(
        self, 
        model: ModelConfig, 
        rag_results: Optional[List[Dict[str, Any]]]
    ) -> tuple[Optional[float], Optional[List[str]]]:
        """Calculate RAG-based similarity score."""
        if not rag_results:
            return None, None
        
        # Find results relevant to this model
        model_results = [
            result for result in rag_results
            if result.get("metadata", {}).get("model_id") == model.model_id
        ]
        
        if not model_results:
            return None, None
        
        # Calculate average similarity
        similarities = [result.get("similarity", 0.0) for result in model_results]
        avg_similarity = sum(similarities) / len(similarities)
        
        # Extract evidence
        evidence = [
            result.get("content", "")[:200] + "..."
            for result in model_results[:3]  # Top 3 pieces of evidence
        ]
        
        return avg_similarity, evidence
    
    def _check_constraints(
        self,
        model: ModelConfig,
        estimated_cost: float,
        estimated_latency: float,
        context: RoutingContext
    ) -> bool:
        """Check if model meets all constraints."""
        # Cost constraint
        if context.max_cost is not None and estimated_cost > context.max_cost:
            return False
        
        # Latency constraint
        if context.max_latency_ms is not None and estimated_latency > context.max_latency_ms:
            return False
        
        # Quality constraint
        if context.min_quality is not None:
            if model.constraints.avg_quality_score < context.min_quality:
                return False
        
        return True
    
    def get_fallback_models(
        self, 
        selected_model_id: str,
        scores: List[RoutingScore],
        max_fallbacks: int = 3
    ) -> List[str]:
        """Get ordered list of fallback models.
        
        Args:
            selected_model_id: ID of the selected model
            scores: All model scores
            max_fallbacks: Maximum number of fallbacks
            
        Returns:
            List of fallback model IDs
        """
        # Get models that meet constraints, excluding the selected one
        fallback_candidates = [
            score for score in scores
            if score.model_id != selected_model_id and score.meets_constraints
        ]
        
        # Sort by final score
        fallback_candidates.sort(key=lambda x: x.final_score, reverse=True)
        
        # Return top fallbacks
        return [
            score.model_id for score in fallback_candidates[:max_fallbacks]
        ]
    
    def explain_selection(
        self, 
        selected_score: RoutingScore,
        analysis: PromptAnalysis,
        context: RoutingContext
    ) -> Dict[str, Any]:
        """Explain why a model was selected.
        
        Args:
            selected_score: Score of the selected model
            analysis: Prompt analysis
            context: Routing context
            
        Returns:
            Dictionary with explanation details
        """
        model = self.models[selected_score.model_id]
        
        explanation = {
            "model_id": selected_score.model_id,
            "model_name": model.name,
            "final_score": selected_score.final_score,
            "reasons": [],
            "trade_offs": [],
            "constraints_met": selected_score.meets_constraints
        }
        
        # Identify primary reasons for selection
        if selected_score.capability_score > 0.8:
            explanation["reasons"].append(
                f"Strong capability match for {analysis.task_type.value} tasks"
            )
        
        if selected_score.cost_score > 0.8:
            explanation["reasons"].append(
                f"Cost-effective at ${selected_score.estimated_cost:.4f}"
            )
        
        if selected_score.latency_score > 0.8:
            explanation["reasons"].append(
                f"Fast response time (~{selected_score.estimated_latency_ms:.0f}ms)"
            )
        
        if selected_score.rag_similarity and selected_score.rag_similarity > 0.7:
            explanation["reasons"].append(
                "High relevance based on model documentation"
            )
        
        # Identify trade-offs
        if selected_score.cost_score < 0.5:
            explanation["trade_offs"].append(
                f"Higher cost (${selected_score.estimated_cost:.4f})"
            )
        
        if selected_score.latency_score < 0.5:
            explanation["trade_offs"].append(
                f"Slower response (~{selected_score.estimated_latency_ms:.0f}ms)"
            )
        
        if selected_score.capability_score < 0.7:
            explanation["trade_offs"].append(
                "May not be optimal for this specific task type"
            )
        
        return explanation
