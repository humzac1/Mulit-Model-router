#!/bin/bash

# Multi-Model Router Setup Script
echo " Setting up Multi-Model Content Pipeline System..."

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
required_version="3.9"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo " Python 3.9+ required. Found: $python_version"
    exit 1
fi

echo " Python version check passed: $python_version"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo " Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo " Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo " Installing dependencies..."
pip install -r requirements.txt

# Create data directories
echo " Creating data directories..."
mkdir -p data/chroma_db data/configs data/model_docs logs

# Check if model configs exist
if [ ! -f "data/configs/models.yaml" ]; then
    echo "  Model configuration not found at data/configs/models.yaml"
    echo "   The system will use the default configuration."
fi

# Check if model docs exist
if [ ! -d "data/model_docs" ] || [ -z "$(ls -A data/model_docs)" ]; then
    echo "  Model documentation directory is empty at data/model_docs/"
    echo "   The RAG system will have limited model knowledge."
fi

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo " Creating .env file from template..."
    cat > .env << EOF
# API Keys
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Model Configuration
DEFAULT_MODEL=gpt-3.5-turbo
FALLBACK_MODEL=llama3:8b

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_TIMEOUT=30

# Database Configuration
DATABASE_URL=sqlite:///./data/router.db
CHROMA_PERSIST_DIRECTORY=./data/chroma_db

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=true
LOG_LEVEL=INFO

# Monitoring
ENABLE_METRICS=true
METRICS_PORT=8001

# Cost and Performance Thresholds
MAX_COST_PER_REQUEST=0.10
MAX_LATENCY_MS=5000
QUALITY_THRESHOLD=0.8

# RAG Configuration
EMBEDDING_MODEL=all-MiniLM-L6-v2
MAX_RAG_RESULTS=5
RAG_SIMILARITY_THRESHOLD=0.7
EOF
    echo "    Created .env file - please update with your API keys"
else
    echo " .env file already exists"
fi

# Validate configuration
echo "🔍 Validating configuration..."
python main.py validate-config 2>/dev/null || echo "⚠️  Configuration validation skipped (configs may not exist yet)"

# Check Ollama connection (optional)
if command -v ollama &> /dev/null; then
    echo " Ollama detected - checking connection..."
    if curl -s http://localhost:11434/api/version > /dev/null; then
        echo "    Ollama is running"
    else
        echo "     Ollama is installed but not running"
        echo "      Start with: ollama serve"
    fi
else
    echo " Ollama not installed - local models will not be available"
    echo "   Install from: https://ollama.ai"
fi

# Initialize knowledge base if docs exist
if [ -d "data/model_docs" ] && [ "$(ls -A data/model_docs)" ]; then
    echo " Initializing knowledge base..."
    python main.py init-knowledge-base
else
    echo " Skipping knowledge base initialization (no docs found)"
fi

echo ""
echo " Setup complete!"
echo ""
echo " Next steps:"
echo "   1. Update .env file with your API keys"
echo "   2. Optionally install and start Ollama for local models"
echo "   3. Start the server: python main.py serve"
echo ""
echo " Documentation:"
echo "   • API docs: http://localhost:8000/docs (after starting server)"
echo "   • Health check: http://localhost:8000/health"
echo "   • README.md for detailed instructions"
echo ""
echo " Development commands:"
echo "   • python main.py serve --reload  (development mode)"
echo "   • python main.py test-model --provider openai --model-id gpt-3.5-turbo"
echo "   • python main.py validate-config"
echo ""
