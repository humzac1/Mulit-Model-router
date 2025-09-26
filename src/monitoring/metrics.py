"""Metrics collection and monitoring."""

import time
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import structlog

logger = structlog.get_logger()


@dataclass
class RequestMetrics:
    """Metrics for a single request."""
    
    request_id: str
    user_id: Optional[str]
    timestamp: datetime
    
    # Request characteristics
    prompt_length: int
    task_type: str
    complexity: str
    domain: str
    
    # Routing decision
    selected_model: str
    routing_confidence: float
    routing_time_ms: float
    rag_query_time_ms: float
    
    # Execution metrics
    total_latency_ms: float
    model_latency_ms: float
    total_cost: float
    input_tokens: int
    output_tokens: int
    
    # Quality metrics
    quality_score: Optional[float] = None
    fallback_used: bool = False
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """Collects and stores metrics for monitoring and analysis."""
    
    def __init__(self, enable_prometheus: bool = False):
        """Initialize metrics collector.
        
        Args:
            enable_prometheus: Whether to enable Prometheus metrics
        """
        self.enable_prometheus = enable_prometheus
        self._request_metrics: Dict[str, RequestMetrics] = {}
        self._prometheus_metrics = None
        
        if enable_prometheus:
            self._setup_prometheus_metrics()
    
    def _setup_prometheus_metrics(self):
        """Setup Prometheus metrics."""
        try:
            from prometheus_client import Counter, Histogram, Gauge
            
            self._prometheus_metrics = {
                "requests_total": Counter(
                    "router_requests_total",
                    "Total number of requests",
                    ["model", "task_type", "complexity"]
                ),
                "request_duration": Histogram(
                    "router_request_duration_seconds",
                    "Request duration in seconds",
                    ["model", "task_type"]
                ),
                "request_cost": Histogram(
                    "router_request_cost_usd",
                    "Request cost in USD",
                    ["model"]
                ),
                "routing_confidence": Histogram(
                    "router_routing_confidence",
                    "Routing decision confidence",
                    ["model", "task_type"]
                ),
                "tokens_processed": Counter(
                    "router_tokens_processed_total",
                    "Total tokens processed",
                    ["model", "token_type"]
                ),
                "fallback_requests": Counter(
                    "router_fallback_requests_total",
                    "Number of requests that used fallback",
                    ["original_model", "fallback_model"]
                ),
                "active_requests": Gauge(
                    "router_active_requests",
                    "Number of currently active requests"
                )
            }
            
            logger.info("Prometheus metrics initialized")
            
        except ImportError:
            logger.warning("Prometheus client not available, metrics disabled")
            self.enable_prometheus = False
    
    def record_request_start(
        self,
        request_id: str,
        user_id: Optional[str],
        prompt_length: int
    ) -> None:
        """Record the start of a request.
        
        Args:
            request_id: Unique request identifier
            user_id: Optional user identifier
            prompt_length: Length of the input prompt
        """
        if self.enable_prometheus and self._prometheus_metrics:
            self._prometheus_metrics["active_requests"].inc()
        
        logger.debug(
            "Request started",
            request_id=request_id,
            user_id=user_id,
            prompt_length=prompt_length
        )
    
    def record_routing_decision(
        self,
        request_id: str,
        selected_model: str,
        task_type: str,
        complexity: str,
        domain: str,
        confidence: float,
        routing_time_ms: float,
        rag_query_time_ms: float
    ) -> None:
        """Record routing decision metrics.
        
        Args:
            request_id: Request identifier
            selected_model: Model selected for the request
            task_type: Detected task type
            complexity: Detected complexity level
            domain: Detected domain
            confidence: Routing confidence score
            routing_time_ms: Time taken for routing decision
            rag_query_time_ms: Time taken for RAG queries
        """
        if self.enable_prometheus and self._prometheus_metrics:
            self._prometheus_metrics["routing_confidence"].labels(
                model=selected_model,
                task_type=task_type
            ).observe(confidence)
        
        logger.debug(
            "Routing decision recorded",
            request_id=request_id,
            selected_model=selected_model,
            confidence=confidence,
            routing_time_ms=routing_time_ms
        )
    
    def record_request_completion(
        self,
        request_id: str,
        user_id: Optional[str],
        prompt_length: int,
        task_type: str,
        complexity: str,
        domain: str,
        selected_model: str,
        routing_confidence: float,
        routing_time_ms: float,
        rag_query_time_ms: float,
        total_latency_ms: float,
        model_latency_ms: float,
        total_cost: float,
        input_tokens: int,
        output_tokens: int,
        quality_score: Optional[float] = None,
        fallback_used: bool = False,
        **metadata
    ) -> None:
        """Record completion of a request.
        
        Args:
            request_id: Request identifier
            user_id: Optional user identifier
            prompt_length: Length of input prompt
            task_type: Detected task type
            complexity: Detected complexity level
            domain: Detected domain
            selected_model: Model used for generation
            routing_confidence: Confidence in routing decision
            routing_time_ms: Time for routing decision
            rag_query_time_ms: Time for RAG queries
            total_latency_ms: Total request latency
            model_latency_ms: Model inference latency
            total_cost: Total cost in USD
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            quality_score: Optional quality score
            fallback_used: Whether fallback was used
            **metadata: Additional metadata
        """
        # Store metrics
        metrics = RequestMetrics(
            request_id=request_id,
            user_id=user_id,
            timestamp=datetime.utcnow(),
            prompt_length=prompt_length,
            task_type=task_type,
            complexity=complexity,
            domain=domain,
            selected_model=selected_model,
            routing_confidence=routing_confidence,
            routing_time_ms=routing_time_ms,
            rag_query_time_ms=rag_query_time_ms,
            total_latency_ms=total_latency_ms,
            model_latency_ms=model_latency_ms,
            total_cost=total_cost,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            quality_score=quality_score,
            fallback_used=fallback_used,
            metadata=metadata
        )
        
        self._request_metrics[request_id] = metrics
        
        # Update Prometheus metrics
        if self.enable_prometheus and self._prometheus_metrics:
            # Request completion
            self._prometheus_metrics["requests_total"].labels(
                model=selected_model,
                task_type=task_type,
                complexity=complexity
            ).inc()
            
            # Duration
            self._prometheus_metrics["request_duration"].labels(
                model=selected_model,
                task_type=task_type
            ).observe(total_latency_ms / 1000)
            
            # Cost
            self._prometheus_metrics["request_cost"].labels(
                model=selected_model
            ).observe(total_cost)
            
            # Tokens
            self._prometheus_metrics["tokens_processed"].labels(
                model=selected_model,
                token_type="input"
            ).inc(input_tokens)
            
            self._prometheus_metrics["tokens_processed"].labels(
                model=selected_model,
                token_type="output"
            ).inc(output_tokens)
            
            # Fallback usage
            if fallback_used:
                # Would need original model info for this
                # self._prometheus_metrics["fallback_requests"].labels(...).inc()
                pass
            
            # Decrement active requests
            self._prometheus_metrics["active_requests"].dec()
        
        logger.info(
            "Request completed",
            request_id=request_id,
            user_id=user_id,
            selected_model=selected_model,
            total_latency_ms=total_latency_ms,
            total_cost=total_cost,
            fallback_used=fallback_used
        )
    
    def record_request_error(
        self,
        request_id: str,
        error_type: str,
        error_message: str,
        model: Optional[str] = None
    ) -> None:
        """Record request error.
        
        Args:
            request_id: Request identifier
            error_type: Type of error
            error_message: Error message
            model: Model that failed (if applicable)
        """
        if self.enable_prometheus and self._prometheus_metrics:
            self._prometheus_metrics["active_requests"].dec()
        
        logger.error(
            "Request error recorded",
            request_id=request_id,
            error_type=error_type,
            error_message=error_message,
            model=model
        )
    
    def get_metrics_summary(
        self,
        time_window_minutes: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get summary of collected metrics.
        
        Args:
            time_window_minutes: Optional time window for filtering metrics
            
        Returns:
            Dictionary with metrics summary
        """
        if time_window_minutes:
            cutoff_time = datetime.utcnow().timestamp() - (time_window_minutes * 60)
            filtered_metrics = [
                m for m in self._request_metrics.values()
                if m.timestamp.timestamp() >= cutoff_time
            ]
        else:
            filtered_metrics = list(self._request_metrics.values())
        
        if not filtered_metrics:
            return {"total_requests": 0}
        
        # Calculate summary statistics
        total_requests = len(filtered_metrics)
        total_cost = sum(m.total_cost for m in filtered_metrics)
        avg_latency = sum(m.total_latency_ms for m in filtered_metrics) / total_requests
        avg_confidence = sum(m.routing_confidence for m in filtered_metrics) / total_requests
        
        # Model usage
        model_usage = {}
        for m in filtered_metrics:
            model_usage[m.selected_model] = model_usage.get(m.selected_model, 0) + 1
        
        # Task type distribution
        task_distribution = {}
        for m in filtered_metrics:
            task_distribution[m.task_type] = task_distribution.get(m.task_type, 0) + 1
        
        # Complexity distribution
        complexity_distribution = {}
        for m in filtered_metrics:
            complexity_distribution[m.complexity] = complexity_distribution.get(m.complexity, 0) + 1
        
        # Fallback usage
        fallback_count = sum(1 for m in filtered_metrics if m.fallback_used)
        
        return {
            "total_requests": total_requests,
            "total_cost_usd": round(total_cost, 4),
            "avg_latency_ms": round(avg_latency, 2),
            "avg_routing_confidence": round(avg_confidence, 3),
            "fallback_usage_rate": round(fallback_count / total_requests, 3) if total_requests > 0 else 0,
            "model_usage": model_usage,
            "task_distribution": task_distribution,
            "complexity_distribution": complexity_distribution,
            "time_window_minutes": time_window_minutes
        }
    
    def get_model_performance(self, model_id: str) -> Dict[str, Any]:
        """Get performance metrics for a specific model.
        
        Args:
            model_id: Model identifier
            
        Returns:
            Dictionary with model performance metrics
        """
        model_metrics = [
            m for m in self._request_metrics.values()
            if m.selected_model == model_id
        ]
        
        if not model_metrics:
            return {"model_id": model_id, "total_requests": 0}
        
        total_requests = len(model_metrics)
        avg_latency = sum(m.total_latency_ms for m in model_metrics) / total_requests
        avg_cost = sum(m.total_cost for m in model_metrics) / total_requests
        avg_confidence = sum(m.routing_confidence for m in model_metrics) / total_requests
        
        # Quality scores (if available)
        quality_scores = [m.quality_score for m in model_metrics if m.quality_score is not None]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else None
        
        return {
            "model_id": model_id,
            "total_requests": total_requests,
            "avg_latency_ms": round(avg_latency, 2),
            "avg_cost_usd": round(avg_cost, 4),
            "avg_routing_confidence": round(avg_confidence, 3),
            "avg_quality_score": round(avg_quality, 3) if avg_quality else None,
            "total_input_tokens": sum(m.input_tokens for m in model_metrics),
            "total_output_tokens": sum(m.output_tokens for m in model_metrics),
            "total_cost_usd": round(sum(m.total_cost for m in model_metrics), 4)
        }
    
    def clear_metrics(self, older_than_hours: int = 24) -> int:
        """Clear old metrics to prevent memory buildup.
        
        Args:
            older_than_hours: Clear metrics older than this many hours
            
        Returns:
            Number of metrics cleared
        """
        cutoff_time = datetime.utcnow().timestamp() - (older_than_hours * 3600)
        
        old_metrics = [
            request_id for request_id, metrics in self._request_metrics.items()
            if metrics.timestamp.timestamp() < cutoff_time
        ]
        
        for request_id in old_metrics:
            del self._request_metrics[request_id]
        
        logger.info(
            "Cleared old metrics",
            cleared_count=len(old_metrics),
            remaining_count=len(self._request_metrics)
        )
        
        return len(old_metrics)
