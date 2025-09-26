"""Logging configuration for the multi-model router."""

import os
import sys
import logging
from typing import Optional
import structlog
from rich.logging import RichHandler


def setup_logging(
    log_level: str = "INFO",
    enable_json: bool = False,
    enable_rich: bool = True
) -> None:
    """Setup structured logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        enable_json: Whether to output JSON logs
        enable_rich: Whether to use rich formatting for console
    """
    # Configure log level
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Setup standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level
    )
    
    # Configure processors based on environment
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    if enable_json:
        # JSON output for production
        processors.append(structlog.processors.JSONRenderer())
    else:
        # Pretty console output for development
        if enable_rich:
            # Use rich for better console formatting
            processors.append(structlog.dev.ConsoleRenderer(colors=True))
        else:
            processors.append(structlog.dev.ConsoleRenderer(colors=False))
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Setup rich handler if enabled
    if enable_rich and not enable_json:
        rich_handler = RichHandler(
            show_time=False,  # structlog handles timestamps
            show_path=False,
            markup=True,
            rich_tracebacks=True
        )
        
        # Get root logger and replace handlers
        root_logger = logging.getLogger()
        root_logger.handlers = [rich_handler]
    
    logger = structlog.get_logger(__name__)
    logger.info(
        "Logging configured",
        level=log_level,
        json_output=enable_json,
        rich_console=enable_rich and not enable_json
    )
