# Multi-Model Content Pipeline System

An intelligent multi-model content pipeline system that analyzes incoming prompts and routes them to the most appropriate AI model based on complexity, cost, and task requirements. The system uses RAG (Retrieval-Augmented Generation) to make informed routing decisions based on model documentation and capabilities.

## Features

### Core Capabilities
- **Intelligent Routing**: Automatically selects the best model for each task based on complexity, cost, and performance requirements
- **RAG-Powered Decisions**: Uses a vector database of model documentation to make informed routing choices
- **Multi-Provider Support**: Seamlessly integrates OpenAI, Anthropic Claude, and local Ollama models
- **Cost Optimization**: Achieves 20-40% cost reduction compared to using GPT-4 for everything
- **Latency Optimization**: Routes simple queries to faster local models for sub-second responses
- **Fallback Mechanisms**: Automatic fallback to alternative models when the primary choice fails

### Technical Features
- **Prompt Analysis**: Advanced classification of task type, complexity, and domain expertise requirements
- **Real-time Monitoring**: Comprehensive metrics tracking for cost, latency, and quality
- **Health Monitoring**: Continuous health checks for all integrated models
- **Flexible Configuration**: YAML-based model configuration with hot-reloading support
- **RESTful API**: Complete FastAPI-based REST API with OpenAPI documentation
- **Production Ready**: Structured logging, error handling, and observability features

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   FastAPI       │    │   Routing        │    │   Model         │
│   REST API      │───▶│   Engine         │───▶│   Integrations  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Prompt        │    │   RAG Knowledge  │    │   • OpenAI      │
│   Analyzer      │    │   Base (ChromaDB)│    │   • Anthropic   │
└─────────────────┘    └──────────────────┘    │   • Ollama      │
                                                └─────────────────┘
                       ┌──────────────────┐
                       │   Monitoring &   │
                       │   Metrics        │
                       └──────────────────┘
```

## Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd Multi-Model\ Content\ Pipeline\ System
```

### 2. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment

Create a `.env` file:

```bash
# API Keys
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Model Configuration
DEFAULT_MODEL=gpt-3.5-turbo
FALLBACK_MODEL=llama3:8b

# Ollama Configuration (for local models)
OLLAMA_BASE_URL=http://localhost:11434

# Database Configuration
DATABASE_URL=sqlite:///./data/router.db
CHROMA_PERSIST_DIRECTORY=./data/chroma_db

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=true
LOG_LEVEL=INFO
```

### 4. Setup Local Models (Optional)

If you want to use local Ollama models for cost optimization:

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull recommended models
ollama pull llama3:8b
ollama pull codellama:13b
```

### 5. Start the Server

```bash
# Development mode
python main.py serve --reload

# Production mode
python main.py serve --workers 4
```

The API will be available at `http://localhost:8000` with interactive docs at `http://localhost:8000/docs`.

## Usage Examples

### Simple Text Generation

```bash
curl -X POST "http://localhost:8000/api/v1/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Explain quantum computing in simple terms",
    "max_cost": 0.05,
    "max_latency_ms": 3000
  }'
```

### Get Routing Decision Only

```bash
curl -X POST "http://localhost:8000/api/v1/route" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Write a complex financial analysis report",
    "min_quality": 0.9,
    "preferred_models": ["gpt-4-turbo", "claude-3-sonnet"]
  }'
```

### Analyze Prompt Characteristics

```bash
curl -X POST "http://localhost:8000/analysis/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Debug this Python function and explain the issue"
  }'
```

## Configuration

### Model Configuration

Edit `data/configs/models.yaml` to configure available models:

```yaml
models:
  gpt-4-turbo:
    model_id: gpt-4-turbo
    name: GPT-4 Turbo
    provider: openai
    capabilities:
      reasoning_ability: 0.95
      creative_ability: 0.90
      code_ability: 0.85
    constraints:
      input_cost_per_1k_tokens: 0.01
      output_cost_per_1k_tokens: 0.03
      avg_latency_ms: 2000
    preferred_for_tasks: [reasoning, analysis, creative]
    is_enabled: true
```

### CLI Commands

```bash
# Validate configuration
python main.py validate-config

# Initialize knowledge base
python main.py init-knowledge-base --force-reload

# Test model connectivity
python main.py test-model --provider openai --model-id gpt-3.5-turbo
```

## Model Selection Logic

The system uses a sophisticated scoring algorithm that considers:

1. **Capability Matching** (40% weight)
   - Task type alignment (reasoning, creative, code, etc.)
   - Domain expertise requirements
   - Complexity handling ability

2. **Cost Optimization** (20% weight)
   - Per-token costs for input and output
   - Budget constraints and thresholds

3. **Latency Requirements** (20% weight)
   - Average response times
   - Real-time performance needs

4. **Quality Expectations** (20% weight)
   - Historical quality scores
   - User satisfaction ratings

### RAG-Enhanced Decisions

The system queries a vector database of model documentation to find relevant information about:
- Model strengths and weaknesses
- Optimal use cases and scenarios
- Performance benchmarks
- Cost-benefit analysis

## Routing Strategies

- **RAG-Based**: Uses documentation similarity for model selection
- **Cost-Optimized**: Prioritizes lowest-cost options that meet quality thresholds
- **Latency-Optimized**: Routes to fastest available models
- **Quality-Optimized**: Selects highest-quality models regardless of cost
- **Hybrid** (default): Balances all factors using configurable weights

## Monitoring and Metrics

### Available Metrics
- Request latency and throughput
- Cost per request and total spend
- Model utilization and performance
- Routing decision confidence
- Fallback usage rates
- Quality scores and user satisfaction

### Endpoints
- `/health` - System health check
- `/health/models` - Individual model health status
- `/health/knowledge-base` - RAG system status
- `/api/v1/models` - List available models and capabilities

### Prometheus Integration

Enable Prometheus metrics by setting `ENABLE_METRICS=true`. Metrics include:
- `router_requests_total` - Total requests by model and task type
- `router_request_duration_seconds` - Request latency distribution
- `router_request_cost_usd` - Cost distribution by model
- `router_routing_confidence` - Routing decision confidence scores

## Model Integrations

### Supported Providers

| Provider | Models | Authentication | Features |
|----------|--------|---------------|----------|
| OpenAI | GPT-4, GPT-3.5 | API Key | Function calling, JSON mode |
| Anthropic | Claude 3 (Sonnet, Haiku, Opus) | API Key | Large context windows |
| Ollama | Llama 3, CodeLlama, Mistral | None (local) | Zero cost, privacy |

### Adding New Models

1. Update `data/configs/models.yaml` with model configuration
2. Add model documentation to `data/model_docs/`
3. Restart the service to reload configuration

### Custom Integrations

Extend `BaseModelInterface` to add new providers:

```python
from src.integrations.base_model import BaseModelInterface

class CustomModelIntegration(BaseModelInterface):
    @property
    def provider_name(self) -> str:
        return "custom"
    
    async def generate_response(self, prompt: str, **kwargs):
        # Implement your model integration
        pass
```

## Production Deployment

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "main.py", "serve", "--workers", "4"]
```

### Environment Variables

Set these in production:
- `OPENAI_API_KEY` - OpenAI API key
- `ANTHROPIC_API_KEY` - Anthropic API key
- `JSON_LOGS=true` - Enable JSON logging
- `LOG_LEVEL=INFO` - Set appropriate log level
- `WORKERS=4` - Number of worker processes

### Health Checks

Configure your load balancer to use `/health` for health checks.


### Running Tests

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=src tests/
```

### Code Quality

```bash
# Format code
black src/ tests/

# Check types
mypy src/

# Lint code
flake8 src/ tests/
```

## API Reference

### Generate Text
`POST /api/v1/generate`

Generate text using optimal model selection.

**Request Body:**
```json
{
  "prompt": "string",
  "max_cost": 0.05,
  "max_latency_ms": 3000,
  "min_quality": 0.8,
  "preferred_models": ["gpt-4-turbo"],
  "temperature": 0.7
}
```

**Response:**
```json
{
  "request_id": "req_1234567890",
  "selected_model": "gpt-3.5-turbo",
  "response_text": "Generated response...",
  "total_latency_ms": 1250,
  "total_cost": 0.023,
  "routing_confidence": 0.87,
  "fallback_used": false
}
```

### Route Request
`POST /api/v1/route`

Get routing decision without executing.

### Analyze Prompt
`POST /analysis/analyze`

Analyze prompt characteristics for task classification.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- OpenAI for GPT models and APIs
- Anthropic for Claude models
- Meta for Llama models via Ollama
- ChromaDB for vector database capabilities
- FastAPI for the excellent web framework

## Support

For questions and support:
- Create an issue on GitHub
- Check the documentation at `/docs` when running the server
- Review the health endpoints for system status

---

