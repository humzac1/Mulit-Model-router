"""Main entry point for the multi-model router server."""

import os
import asyncio
from pathlib import Path
import uvicorn
import click
from dotenv import load_dotenv

from src.api.server import create_app
from src.monitoring.logging_config import setup_logging

# Load environment variables
load_dotenv()


@click.command()
@click.option(
    "--host",
    default=os.getenv("HOST", "0.0.0.0"),
    help="Host to bind to"
)
@click.option(
    "--port",
    default=int(os.getenv("PORT", 8000)),
    help="Port to bind to"
)
@click.option(
    "--reload",
    is_flag=True,
    default=os.getenv("DEBUG", "false").lower() == "true",
    help="Enable auto-reload for development"
)
@click.option(
    "--log-level",
    default=os.getenv("LOG_LEVEL", "INFO"),
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    help="Logging level"
)
@click.option(
    "--json-logs",
    is_flag=True,
    default=os.getenv("JSON_LOGS", "false").lower() == "true",
    help="Output logs in JSON format"
)
@click.option(
    "--workers",
    default=int(os.getenv("WORKERS", 1)),
    help="Number of worker processes"
)
def main(
    host: str,
    port: int,
    reload: bool,
    log_level: str,
    json_logs: bool,
    workers: int
):
    """Start the multi-model router server."""
    
    # Setup logging
    setup_logging(
        log_level=log_level,
        enable_json=json_logs,
        enable_rich=not json_logs
    )
    
    # Create the FastAPI app
    app = create_app()
    
    # Configure uvicorn
    config = {
        "app": app,
        "host": host,
        "port": port,
        "log_level": log_level.lower(),
        "access_log": True,
        "use_colors": not json_logs,
    }
    
    if reload:
        # Development mode
        config.update({
            "reload": True,
            "reload_dirs": ["src"],
            "reload_includes": ["*.py", "*.yaml", "*.yml"],
        })
        click.echo(f"Starting development server on http://{host}:{port}")
        click.echo("Auto-reload enabled - server will restart on code changes")
    else:
        # Production mode
        if workers > 1:
            config["workers"] = workers
        click.echo(f"Starting production server on http://{host}:{port}")
        if workers > 1:
            click.echo(f"Using {workers} worker processes")
    
    # Print environment info
    click.echo(f"Log level: {log_level}")
    click.echo(f"JSON logs: {json_logs}")
    
    # Check for required environment variables
    required_env_vars = []
    
    # Check for API keys (warn if missing)
    if not os.getenv("OPENAI_API_KEY"):
        click.echo("  Warning: OPENAI_API_KEY not set - OpenAI models will not work")
    
    if not os.getenv("ANTHROPIC_API_KEY"):
        click.echo("  Warning: ANTHROPIC_API_KEY not set - Anthropic models will not work")
    
    # Check for local directories
    data_dir = Path("data")
    if not data_dir.exists():
        click.echo("  Warning: data/ directory not found - creating it")
        data_dir.mkdir(exist_ok=True)
        (data_dir / "model_docs").mkdir(exist_ok=True)
        (data_dir / "configs").mkdir(exist_ok=True)
    
    # Start the server
    try:
        uvicorn.run(**config)
    except KeyboardInterrupt:
        click.echo("\n Shutting down gracefully...")
    except Exception as e:
        click.echo(f" Server failed to start: {e}")
        raise


@click.group()
def cli():
    """Multi-Model Content Pipeline System CLI."""
    pass


@cli.command()
@click.option(
    "--config-file",
    default="data/configs/models.yaml",
    help="Path to model configuration file"
)
def validate_config(config_file: str):
    """Validate model configuration file."""
    import yaml
    from src.models.model_config import ModelConfig
    
    try:
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)
        
        models = config_data.get("models", {})
        valid_models = 0
        
        for model_id, model_data in models.items():
            try:
                ModelConfig(**model_data)
                click.echo(f" {model_id}: Valid")
                valid_models += 1
            except Exception as e:
                click.echo(f" {model_id}: {e}")
        
        click.echo(f"\nValidation complete: {valid_models}/{len(models)} models valid")
        
    except FileNotFoundError:
        click.echo(f" Configuration file not found: {config_file}")
    except Exception as e:
        click.echo(f" Validation failed: {e}")


@cli.command()
@click.option(
    "--docs-dir",
    default="data/model_docs",
    help="Path to model documentation directory"
)
@click.option(
    "--force-reload",
    is_flag=True,
    help="Force reload of knowledge base"
)
def init_knowledge_base(docs_dir: str, force_reload: bool):
    """Initialize the RAG knowledge base."""
    import asyncio
    from src.rag.knowledge_base import ModelKnowledgeBase
    
    async def _init():
        kb = ModelKnowledgeBase()
        await kb.initialize_from_documents(docs_dir, force_reload=force_reload)
        stats = kb.get_stats()
        click.echo(f" Knowledge base initialized with {stats['total_documents']} documents")
    
    try:
        asyncio.run(_init())
    except Exception as e:
        click.echo(f" Failed to initialize knowledge base: {e}")


@cli.command()
@click.option(
    "--provider",
    type=click.Choice(["openai", "anthropic", "ollama"]),
    required=True,
    help="Model provider to test"
)
@click.option(
    "--model-id",
    required=True,
    help="Model ID to test"
)
@click.option(
    "--api-key",
    help="API key (optional, will use environment variable if not provided)"
)
def test_model(provider: str, model_id: str, api_key: str):
    """Test connection to a specific model."""
    import asyncio
    from src.integrations.model_factory import ModelFactory
    from src.models.model_config import ModelProvider
    
    async def _test():
        try:
            provider_enum = ModelProvider(provider)
            result = await ModelFactory.test_integration(
                provider=provider_enum,
                model_id=model_id,
                api_key=api_key
            )
            
            if result:
                click.echo(f" {provider}/{model_id}: Connection successful")
            else:
                click.echo(f" {provider}/{model_id}: Connection failed")
                
        except Exception as e:
            click.echo(f" {provider}/{model_id}: {e}")
    
    asyncio.run(_test())


# Add commands to CLI
cli.add_command(main, name="serve")

if __name__ == "__main__":
    cli()
