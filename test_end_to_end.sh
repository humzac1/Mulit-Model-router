#!/bin/bash

echo "🧪 End-to-End Testing for Multi-Model Router"
echo "=============================================="

# Check multiple sources for API key
echo "📄 Checking for OpenAI API key..."

# First check if already set in environment
if [ -n "$OPENAI_API_KEY" ] && [[ "$OPENAI_API_KEY" =~ ^sk- ]] && [ "$OPENAI_API_KEY" != "YOUR_OPEN_AI_API_KEY" ]; then
    echo "✅ Found API key in environment variable"
    echo "   Length: ${#OPENAI_API_KEY} characters"
elif [ -f .env ]; then
    # Try loading from .env file
    echo "📄 Loading from .env file..."
    
    # Use Python to load .env properly
    LOADED_KEY=$(python3 -c "
import os
try:
    from dotenv import load_dotenv
    load_dotenv()
    key = os.getenv('OPENAI_API_KEY', '')
    if key and key not in ['YOUR_OPEN_AI_API_KEY', 'your_openai_api_key_here', '']:
        print(key)
except:
    pass
" 2>/dev/null)
    
    if [ -n "$LOADED_KEY" ] && [[ "$LOADED_KEY" =~ ^sk- ]]; then
        export OPENAI_API_KEY="$LOADED_KEY"
        echo "✅ Loaded API key from .env file"
        echo "   Length: ${#OPENAI_API_KEY} characters"
    else
        echo "❌ OPENAI_API_KEY not properly configured"
        echo ""
        echo "Please set your OpenAI API key in one of these ways:"
        echo ""
        echo "Option 1: Update .env file:"
        echo "  OPENAI_API_KEY=sk-proj-your_actual_key_here"
        echo ""
        echo "Option 2: Export as environment variable:"
        echo "  export OPENAI_API_KEY='sk-proj-your_actual_key_here'"
        echo ""
        echo "Option 3: Use the helper script:"
        echo "  ./set_api_key.sh 'your_key_here'"
        echo ""
        exit 1
    fi
else
    echo "❌ No .env file found and OPENAI_API_KEY not set"
    exit 1
fi

# Test 1: Start the server
echo ""
echo "🚀 Starting the Multi-Model Router server..."
python3 main.py serve --host 127.0.0.1 --port 8000 &
SERVER_PID=$!
sleep 5

# Check if server is running
if ! curl -s http://127.0.0.1:8000/health > /dev/null; then
    echo "❌ Server failed to start"
    kill $SERVER_PID 2>/dev/null
    exit 1
fi

echo "✅ Server started successfully on http://127.0.0.1:8000"

# Test 2: Health check
echo ""
echo "🏥 Testing health endpoint..."
HEALTH_RESPONSE=$(curl -s http://127.0.0.1:8000/health)
if [ $? -eq 0 ]; then
    echo "✅ Health check passed"
    echo "Response: $HEALTH_RESPONSE"
else
    echo "❌ Health check failed"
fi

# Test 3: Model health
echo ""
echo "🔍 Testing model health..."
MODEL_HEALTH=$(curl -s http://127.0.0.1:8000/health/models)
if [ $? -eq 0 ]; then
    echo "✅ Model health check completed"
    echo "Models checked. This will show connectivity status."
else
    echo "❌ Model health check failed"
fi

# Test 4: Prompt analysis
echo ""
echo "🧠 Testing prompt analysis..."
ANALYSIS_RESPONSE=$(curl -s -X POST http://127.0.0.1:8000/analysis/analyze \
    -H "Content-Type: application/json" \
    -d '{"prompt": "Write a Python function to calculate fibonacci numbers"}')

if [ $? -eq 0 ] && echo "$ANALYSIS_RESPONSE" | grep -q "task_type"; then
    echo "✅ Prompt analysis successful"
    echo "Detected task type:" $(echo "$ANALYSIS_RESPONSE" | grep -o '"task_type":"[^"]*"' | cut -d'"' -f4)
else
    echo "❌ Prompt analysis failed"
    echo "Response: $ANALYSIS_RESPONSE"
fi

# Test 5: Routing decision
echo ""
echo "🎯 Testing routing decision..."
ROUTE_RESPONSE=$(curl -s -X POST http://127.0.0.1:8000/api/v1/route \
    -H "Content-Type: application/json" \
    -d '{
        "prompt": "Write a Python function to calculate fibonacci numbers",
        "max_cost": 0.01
    }')

if [ $? -eq 0 ] && echo "$ROUTE_RESPONSE" | grep -q "selected_model"; then
    echo "✅ Routing decision successful"
    SELECTED_MODEL=$(echo "$ROUTE_RESPONSE" | grep -o '"selected_model":"[^"]*"' | cut -d'"' -f4)
    echo "Selected model: $SELECTED_MODEL"
else
    echo "❌ Routing decision failed"
    echo "Response: $ROUTE_RESPONSE"
fi

# Test 6: Text generation (the main test!)
echo ""
echo "📝 Testing text generation with OpenAI..."
GENERATE_RESPONSE=$(curl -s -X POST http://127.0.0.1:8000/api/v1/generate \
    -H "Content-Type: application/json" \
    -d '{
        "prompt": "Hello! Can you explain what machine learning is in simple terms?",
        "max_tokens": 150,
        "temperature": 0.7
    }')

if [ $? -eq 0 ] && echo "$GENERATE_RESPONSE" | grep -q "response_text"; then
    echo "✅ Text generation successful!"
    MODEL_USED=$(echo "$GENERATE_RESPONSE" | grep -o '"selected_model":"[^"]*"' | cut -d'"' -f4)
    COST=$(echo "$GENERATE_RESPONSE" | grep -o '"total_cost":[0-9.]*' | cut -d':' -f2)
    echo "Model used: $MODEL_USED"
    echo "Estimated cost: $$COST"
    echo ""
    echo "📄 Generated response preview:"
    echo "$GENERATE_RESPONSE" | grep -o '"response_text":"[^"]*"' | cut -d'"' -f4 | head -c 200
    echo "..."
else
    echo "❌ Text generation failed"
    echo "Response: $GENERATE_RESPONSE"
fi

# Test 7: List available models
echo ""
echo "📋 Testing model listing..."
MODELS_RESPONSE=$(curl -s http://127.0.0.1:8000/api/v1/models)

if [ $? -eq 0 ] && echo "$MODELS_RESPONSE" | grep -q "models"; then
    echo "✅ Model listing successful"
    MODEL_COUNT=$(echo "$MODELS_RESPONSE" | grep -o '"total_count":[0-9]*' | cut -d':' -f2)
    ENABLED_COUNT=$(echo "$MODELS_RESPONSE" | grep -o '"enabled_count":[0-9]*' | cut -d':' -f2)
    echo "Total models: $MODEL_COUNT, Enabled: $ENABLED_COUNT"
else
    echo "❌ Model listing failed"
fi

# Cleanup
echo ""
echo "🧹 Shutting down server..."
kill $SERVER_PID 2>/dev/null
wait $SERVER_PID 2>/dev/null

echo ""
echo "🎉 End-to-end testing completed!"
echo ""
echo "💡 Tips for troubleshooting:"
echo "   - Make sure your OpenAI API key is valid and has credits"
echo "   - Check server logs for detailed error messages"
echo "   - Ensure all required Python packages are installed"
echo "   - Verify model configurations in data/configs/models.yaml"
