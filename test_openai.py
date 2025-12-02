#!/usr/bin/env python3
"""Simple test script to verify OpenAI integration works."""

import os
import asyncio
from src.integrations.model_factory import ModelFactory
from src.models.model_config import ModelProvider

async def test_openai_models():
    """Test OpenAI model connectivity."""

    # Check if API key is available
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment")
        print("💡 Please set your OpenAI API key:")
        print("   export OPENAI_API_KEY='your_api_key_here'")
        print("   Or add it to your .env file as: OPENAI_API_KEY=your_api_key_here")
        return False

    if api_key == "your_api_key_here" or len(api_key) < 20:
        print("❌ OPENAI_API_KEY appears to be a placeholder or too short")
        return False

    print(f"✅ Found OpenAI API key (length: {len(api_key)})")

    # Test GPT-3.5 Turbo
    print("\n🧪 Testing GPT-3.5 Turbo...")
    try:
        success = await ModelFactory.test_integration(
            provider=ModelProvider.OPENAI,
            model_id="gpt-3.5-turbo",
            api_key=api_key
        )
        if success:
            print("✅ GPT-3.5 Turbo connection successful")
        else:
            print("❌ GPT-3.5 Turbo connection failed")
    except Exception as e:
        print(f"❌ GPT-3.5 Turbo test failed: {e}")
        return False

    # Test GPT-4 Turbo
    print("\n🧪 Testing GPT-4 Turbo...")
    try:
        success = await ModelFactory.test_integration(
            provider=ModelProvider.OPENAI,
            model_id="gpt-4-turbo",
            api_key=api_key
        )
        if success:
            print("✅ GPT-4 Turbo connection successful")
        else:
            print("❌ GPT-4 Turbo connection failed")
    except Exception as e:
        print(f"❌ GPT-4 Turbo test failed: {e}")
        return False

    print("\n🎉 All OpenAI model tests passed!")
    return True

async def test_simple_generation():
    """Test a simple text generation with OpenAI."""

    print("\n📝 Testing simple text generation...")

    try:
        factory = ModelFactory()
        model = factory.create_from_config({
            "model_id": "gpt-3.5-turbo",
            "name": "GPT-3.5 Turbo",
            "provider": "openai",
            "model_type": "chat",
            "version": "gpt-3.5-turbo",
            "api_key_env": "OPENAI_API_KEY"
        })

        response = await model.generate_response(
            prompt="Hello! Can you tell me what 2+2 equals?",
            temperature=0.7,
            max_tokens=100
        )

        print("✅ Generation successful!")
        print(f"Response: {response.content}")
        print(f"Tokens: {response.input_tokens} input, {response.output_tokens} output")
        print(f"Cost: ${response.cost_usd:.4f}")

        return True

    except Exception as e:
        print(f"❌ Generation test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing OpenAI Integration")

    async def main():
        # Test connectivity
        connectivity_ok = await test_openai_models()

        if connectivity_ok:
            # Test generation
            await test_simple_generation()
        else:
            print("❌ Skipping generation test due to connectivity issues")

    asyncio.run(main())
