#!/usr/bin/env python3
"""
Demo script showing how to use the Multi-Model Router API.

This script demonstrates various types of requests and shows how the system
intelligently routes them to different models based on the prompt characteristics.
"""

import asyncio
import json
import httpx
from typing import Dict, Any


class RouterClient:
    """Simple client for the Multi-Model Router API."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()
    
    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate text using the router."""
        data = {"prompt": prompt, **kwargs}
        response = await self.client.post(f"{self.base_url}/api/v1/generate", json=data)
        response.raise_for_status()
        return response.json()
    
    async def route(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Get routing decision without generating."""
        data = {"prompt": prompt, **kwargs}
        response = await self.client.post(f"{self.base_url}/api/v1/route", json=data)
        response.raise_for_status()
        return response.json()
    
    async def analyze(self, prompt: str) -> Dict[str, Any]:
        """Analyze prompt characteristics."""
        data = {"prompt": prompt}
        response = await self.client.post(f"{self.base_url}/analysis/analyze", json=data)
        response.raise_for_status()
        return response.json()
    
    async def health(self) -> Dict[str, Any]:
        """Check system health."""
        response = await self.client.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """Close the client."""
        await self.client.aclose()


async def demo_simple_qa():
    """Demo: Simple Q&A - should route to fast/cheap model."""
    print("🔍 Demo 1: Simple Q&A")
    print("Prompt: 'What is the capital of France?'")
    
    client = RouterClient()
    
    # First, analyze the prompt
    analysis = await client.analyze("What is the capital of France?")
    print(f"📊 Analysis: {analysis['task_type']} task, {analysis['complexity']} complexity")
    
    # Get routing decision
    decision = await client.route("What is the capital of France?")
    print(f"🎯 Routing: Selected {decision['selected_model']} (confidence: {decision['confidence']:.2f})")
    
    # Generate response
    response = await client.generate("What is the capital of France?")
    print(f"💡 Response: {response['response_text'][:100]}...")
    print(f"💰 Cost: ${response['total_cost']:.4f}, ⏱️ Latency: {response['total_latency_ms']:.0f}ms")
    
    await client.close()
    print()


async def demo_complex_analysis():
    """Demo: Complex analysis - should route to powerful model."""
    print("🔍 Demo 2: Complex Analysis")
    complex_prompt = """Analyze the potential economic impacts of widespread AI adoption 
    on employment markets over the next decade. Consider sector-specific effects, 
    regional variations, and policy implications. Provide actionable recommendations."""
    
    print(f"Prompt: {complex_prompt[:80]}...")
    
    client = RouterClient()
    
    # Analyze
    analysis = await client.analyze(complex_prompt)
    print(f"📊 Analysis: {analysis['task_type']} task, {analysis['complexity']} complexity")
    print(f"   Domain expertise: {analysis['domain_expertise']:.2f}")
    
    # Route with quality preference
    decision = await client.route(
        complex_prompt, 
        min_quality=0.9,
        strategy="quality_optimized"
    )
    print(f"🎯 Routing: Selected {decision['selected_model']} (confidence: {decision['confidence']:.2f})")
    print(f"   Expected cost: ${decision['expected_cost']:.4f}")
    
    await client.close()
    print()


async def demo_code_generation():
    """Demo: Code generation - should route to code-specialized model."""
    print("🔍 Demo 3: Code Generation")
    code_prompt = """Write a Python function that implements a binary search algorithm. 
    Include proper error handling, documentation, and example usage."""
    
    print(f"Prompt: {code_prompt[:80]}...")
    
    client = RouterClient()
    
    # Analyze
    analysis = await client.analyze(code_prompt)
    print(f"📊 Analysis: {analysis['task_type']} task, {analysis['complexity']} complexity")
    
    # Route preferring code models
    decision = await client.route(
        code_prompt,
        preferred_models=["codellama-13b", "gpt-4-turbo"]
    )
    print(f"🎯 Routing: Selected {decision['selected_model']}")
    
    await client.close()
    print()


async def demo_cost_optimization():
    """Demo: Cost-constrained request - should route to cheap model."""
    print("🔍 Demo 4: Cost Optimization")
    prompt = "Write a brief summary of renewable energy benefits."
    
    print(f"Prompt: {prompt}")
    
    client = RouterClient()
    
    # Route with strict cost constraint
    decision = await client.route(
        prompt,
        max_cost=0.01,  # Very low cost limit
        strategy="cost_optimized"
    )
    print(f"🎯 Routing: Selected {decision['selected_model']} (expected cost: ${decision['expected_cost']:.4f})")
    
    # Generate with cost constraint
    response = await client.generate(
        prompt,
        max_cost=0.01
    )
    print(f"💰 Actual cost: ${response['total_cost']:.4f}")
    print(f"📝 Response length: {len(response['response_text'])} characters")
    
    await client.close()
    print()


async def demo_latency_optimization():
    """Demo: Latency-sensitive request - should route to fast model."""
    print("🔍 Demo 5: Latency Optimization")
    prompt = "Give me 3 quick tips for better sleep."
    
    print(f"Prompt: {prompt}")
    
    client = RouterClient()
    
    # Route with strict latency constraint
    decision = await client.route(
        prompt,
        max_latency_ms=1000,  # Must respond in under 1 second
        strategy="latency_optimized"
    )
    print(f"🎯 Routing: Selected {decision['selected_model']} (expected latency: {decision['expected_latency_ms']:.0f}ms)")
    
    # Generate with latency constraint
    response = await client.generate(
        prompt,
        max_latency_ms=1000
    )
    print(f"⏱️ Actual latency: {response['total_latency_ms']:.0f}ms")
    print(f"📝 Response: {response['response_text'][:150]}...")
    
    await client.close()
    print()


async def demo_system_overview():
    """Demo: Show system capabilities and health."""
    print("🔍 System Overview")
    
    client = RouterClient()
    
    # Health check
    try:
        health = await client.health()
        print(f"✅ System status: {health['status']}")
        
        # Get model health
        model_health_response = await client.client.get("http://localhost:8000/health/models")
        if model_health_response.status_code == 200:
            model_health = model_health_response.json()
            print(f"🤖 Models: {model_health['summary']['healthy']}/{model_health['summary']['total']} healthy")
            
            # Show healthy models
            healthy_models = [model for model, status in model_health['models'].items() if status]
            print(f"   Available: {', '.join(healthy_models)}")
        
        # Get available models
        models_response = await client.client.get("http://localhost:8000/api/v1/models")
        if models_response.status_code == 200:
            models_data = models_response.json()
            print(f"📋 Total configured models: {models_data['total_count']}")
            print(f"   Enabled: {models_data['enabled_count']}")
        
    except httpx.ConnectError:
        print("❌ Cannot connect to router service. Is it running?")
        print("   Start with: python main.py serve")
        return False
    
    await client.close()
    print()
    return True


async def main():
    """Run all demos."""
    print("🚀 Multi-Model Router API Demo")
    print("=" * 50)
    print()
    
    # Check if system is running
    system_ok = await demo_system_overview()
    if not system_ok:
        return
    
    # Run demos
    demos = [
        demo_simple_qa,
        demo_complex_analysis,
        demo_code_generation,
        demo_cost_optimization,
        demo_latency_optimization,
    ]
    
    for demo in demos:
        try:
            await demo()
        except httpx.HTTPStatusError as e:
            print(f"❌ Demo failed: {e.response.status_code} - {e.response.text}")
            print()
        except Exception as e:
            print(f"❌ Demo failed: {e}")
            print()
    
    print("🎉 Demo complete!")
    print()
    print("💡 Key takeaways:")
    print("   • Simple questions → Fast, cheap models")
    print("   • Complex analysis → High-quality models")
    print("   • Code tasks → Code-specialized models")
    print("   • Cost constraints → Automatic optimization")
    print("   • Latency constraints → Speed prioritization")
    print()
    print("🔗 Try the interactive docs: http://localhost:8000/docs")


if __name__ == "__main__":
    asyncio.run(main())
