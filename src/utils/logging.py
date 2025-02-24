import structlog
import logging
import sys
from typing import Any

def add_app_info(_, __, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Add application-specific context to log entries."""
    event_dict["app"] = "crewai-agent"
    return event_dict

def configure_logging() -> None:
    """Configure structured logging with enhanced detail and formatting."""
    # Set up standard logging first
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(message)s",
        stream=sys.stdout
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
            add_app_info,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(indent=None)
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Set external loggers to warning to reduce noise
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
