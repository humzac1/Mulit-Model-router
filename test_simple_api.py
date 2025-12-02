#!/usr/bin/env python3
"""Simple API test without full server startup."""

import os
import asyncio
from dotenv import load_dotenv

load_dotenv()
os.environ['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY', '')

async def test_routing():
    """Test the routing functionality directly."""
    print("🧪 Testing Multi-Model Router Core Functionality")
    print("=" * 60)
    
    try:
        from src.routing.prompt_analyzer import PromptAnalyzer
        from src.routing.routing_engine import RoutingEngine
        from src.models.prompt import PromptRequest
        from src.models.routing import RoutingContext
        from src.models.model_config import ModelConfig
        import yaml
        from pathlib import Path
        
        print("\n1️⃣ Testing Prompt Analyzer...")
        analyzer = PromptAnalyzer()
        test_prompt = "Write a Python function to calculate fibonacci numbers"
        analysis = await analyzer.analyze_prompt(test_prompt)
        print(f"   ✅ Prompt analyzed: {analysis.task_type.value}, complexity: {analysis.complexity.value}")
        
        print("\n2️⃣ Loading Model Configurations...")
        config_path = Path("data/configs/models.yaml")
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        
        models = []
        for model_data in config_data.get("models", {}).values():
            try:
                model_config = ModelConfig(**model_data)
                if model_config.is_enabled and model_config.provider.value == "openai":
                    models.append(model_config)
            except Exception as e:
                print(f"   ⚠️  Skipped model: {e}")
                continue
        
        print(f"   ✅ Loaded {len(models)} OpenAI models")
        for model in models:
            print(f"      - {model.model_id} ({model.name})")
        
        print("\n3️⃣ Testing Model Integration...")
        from src.integrations.model_factory import ModelFactory
        
        factory = ModelFactory()
        test_model = models[0] if models else None
        
        if test_model:
            print(f"   Testing {test_model.model_id}...")
            model_instance = factory.create_from_config(test_model.dict())
            
            print("\n4️⃣ Testing Text Generation...")
            response = await model_instance.generate_response(
                prompt="Hello! What is 2+2?",
                temperature=0.7,
                max_tokens=50
            )
            
            print(f"   ✅ Generation successful!")
            print(f"   Response: {response.content[:100]}...")
            print(f"   Tokens: {response.input_tokens} input, {response.output_tokens} output")
            print(f"   Cost: ${response.cost_usd:.6f}")
            print(f"   Latency: {response.latency_ms:.0f}ms")
            
        print("\n" + "=" * 60)
        print("✅ All core functionality tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_routing())
    exit(0 if success else 1)
