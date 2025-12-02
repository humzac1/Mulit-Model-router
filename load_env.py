#!/usr/bin/env python3
"""Helper script to load .env file and export variables."""

import os
import sys
from pathlib import Path

# Try to load dotenv if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Fallback: manually parse .env file
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Remove quotes if present
                    value = value.strip('"\'')
                    os.environ[key.strip()] = value

# Check OpenAI API key
api_key = os.getenv("OPENAI_API_KEY", "")

if not api_key or api_key in ["YOUR_OPEN_AI_API_KEY", "your_openai_api_key_here", ""]:
    print("❌ OPENAI_API_KEY not properly configured in .env file")
    print("")
    print("Please update your .env file with:")
    print("OPENAI_API_KEY=sk-proj-your_actual_key_here")
    sys.exit(1)

# Check if it looks like a valid key
if not api_key.startswith("sk-"):
    print(f"⚠️  Warning: API key doesn't start with 'sk-' (current: {api_key[:10]}...)")
    print("This might not be a valid OpenAI API key format")

print(f"✅ Found OpenAI API key (length: {len(api_key)})")
print(f"   Key preview: {api_key[:20]}...")

# Export for shell scripts
print(f"export OPENAI_API_KEY='{api_key}'")

