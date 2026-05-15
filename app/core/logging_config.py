"""Logging configuration for the T1D Companion application."""

import logging
import sys
from datetime import datetime
from logging.config import dictConfig
from typing import Any

from pythonjsonlogger import jsonlogger  # type: ignore


def setup_logging() -> None:
    """Configure structured JSON logging."""
    log_level = logging.INFO

    logging_config: dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": JSONFormatter,
                "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
                "datefmt": "%Y-%m-%dT%H:%M:%S",
            },
            "human": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": "json" if log_level == logging.INFO else "human",
            },
        },
        "loggers": {
            "app": {
                "handlers": ["console"],
                "level": log_level,
                "propagate": False,
            },
            "uvicorn": {
                "handlers": ["console"],
                "level": logging.WARNING,
                "propagate": False,
            },
            "sqlalchemy": {
                "handlers": ["console"],
                "level": logging.WARNING,
                "propagate": False,
            },
        },
        "root": {
            "handlers": ["console"],
            "level": logging.WARNING,
        },
    }

    dictConfig(logging_config)


class JSONFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields."""

    def __init__(self, fmt: str = None, datefmt: str = None):
        super().__init__(fmt, datefmt=datefmt)

    def add_fields(
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        """Add custom fields to log record.
        
        Args:
            log_record: The log record dictionary
            record: The logging record
            message_dict: Parsed message dictionary
        """
        super().add_fields(log_record, record, message_dict)

        log_record["timestamp"] = datetime.utcnow().isoformat()
        log_record["level"] = record.levelname
        log_record["logger"] = record.name

        # Add optional fields
        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_record["user_id"] = record.user_id
        if hasattr(record, "endpoint"):
            log_record["endpoint"] = record.endpoint
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)


# Initialize logging on import
setup_logging()


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given module.
    
    Args:
        name: Module name
        
    Returns:
        logging.Logger: Configured logger
    """
    return logging.getLogger(f"app.{name}")
