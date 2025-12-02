#!/bin/bash
# Helper script to set OpenAI API key

if [ -z "$1" ]; then
    echo "Usage: ./set_api_key.sh 'your_openai_api_key_here'"
    echo ""
    echo "Or set it as an environment variable:"
    echo "export OPENAI_API_KEY='your_key_here'"
    echo "./test_end_to_end.sh"
    exit 1
fi

API_KEY="$1"

# Validate format
if [[ ! "$API_KEY" =~ ^sk- ]]; then
    echo "⚠️  Warning: API key should start with 'sk-'"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Export for current session
export OPENAI_API_KEY="$API_KEY"
echo "✅ API key set for this session"
echo "   Length: ${#API_KEY} characters"
echo "   Preview: ${API_KEY:0:20}..."

# Run the test
echo ""
echo "🚀 Running end-to-end test..."
./test_end_to_end.sh
