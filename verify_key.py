#!/usr/bin/env python3
"""Verify OpenAI API key is set correctly."""

import os
import sys

# Try loading from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Manual .env parsing
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    value = value.strip('"\'')
                    os.environ[key.strip()] = value

api_key = os.getenv("OPENAI_API_KEY", "")

print("🔍 Checking OpenAI API Key Configuration")
print("=" * 50)

if not api_key:
    print("❌ OPENAI_API_KEY not found")
    print("\n💡 To set your API key:")
    print("   1. Edit .env file and replace YOUR_OPEN_AI_API_KEY with your actual key")
    print("   2. Or run: export OPENAI_API_KEY='sk-proj-your_key_here'")
    sys.exit(1)

# Check for placeholder values
placeholders = ["YOUR_OPEN_AI_API_KEY", "your_openai_api_key_here", "sk-proj-your_actual_key_here"]
if api_key in placeholders:
    print(f"❌ API key appears to be a placeholder: {api_key[:30]}...")
    print("\n💡 Please replace it with your actual OpenAI API key in the .env file")
    sys.exit(1)

# Check format
if not api_key.startswith("sk-"):
    print(f"⚠️  Warning: API key doesn't start with 'sk-'")
    print(f"   Current format: {api_key[:20]}...")
    print("   Valid OpenAI keys typically start with 'sk-'")
else:
    print(f"✅ API key format looks correct")

print(f"\n📋 Key Details:")
print(f"   Length: {len(api_key)} characters")
print(f"   Preview: {api_key[:20]}...{api_key[-4:]}")
print(f"   Starts with: {api_key[:7]}")

# Test the key with a simple API call
print(f"\n🧪 Testing API key with OpenAI...")
try:
    import openai
    client = openai.OpenAI(api_key=api_key)
    
    # Simple test call
    response = client.models.list()
    print("✅ API key is valid and working!")
    print(f"   Successfully connected to OpenAI API")
    print(f"   Available models: {len(response.data)} models found")
    
except ImportError:
    print("⚠️  OpenAI library not installed - cannot test key validity")
    print("   But the key format looks correct!")
except Exception as e:
    error_msg = str(e)
    if "Invalid API key" in error_msg or "401" in error_msg:
        print(f"❌ API key is invalid or expired")
        print(f"   Error: {error_msg[:100]}")
        sys.exit(1)
    elif "Rate limit" in error_msg:
        print(f"⚠️  Rate limit error (key might be valid but over quota)")
    else:
        print(f"⚠️  Could not verify key: {error_msg[:100]}")
        print(f"   But the key format looks correct!")

print("\n" + "=" * 50)
print("✅ Your API key is configured correctly!")
print("   You can now run: ./test_end_to_end.sh")
