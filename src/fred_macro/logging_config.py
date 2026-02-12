"""
Structured logging configuration for FRED Macro Dashboard.

Provides consistent JSON-formatted logging across all modules.
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """Custom formatter to output logs as JSON."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add any extra fields
        for key, value in record.__dict__.items():
            if key not in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "asctime",
                "message",
            }:
                log_data[key] = value

        return json.dumps(log_data)


class ConsoleFormatter(logging.Formatter):
    """Simple formatter for console output."""

    def __init__(self):
        super().__init__(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


def setup_logging(
    log_level: str = None,
    log_dir: str = "logs",
    json_format: bool = False,
) -> logging.Logger:
    """
    Set up structured logging.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR).
                   Defaults to env var LOG_LEVEL or INFO.
        log_dir: Directory for log files. Defaults to 'logs'.
        json_format: Whether to use JSON formatting. Defaults to False for readability.

    Returns:
        logging.Logger: Configured root logger.
    """
    # Get log level from environment or parameter
    level = (log_level or os.getenv("LOG_LEVEL", "INFO")).upper()
    numeric_level = getattr(logging, level, logging.INFO)

    # Create logs directory
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    # Create logger
    logger = logging.getLogger("fred_macro")
    logger.setLevel(numeric_level)
    logger.handlers = []  # Clear existing handlers

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(ConsoleFormatter())
    logger.addHandler(console_handler)

    # File handler with daily rotation
    date_str = datetime.now().strftime("%Y%m%d")
    log_file = log_path / f"fred_macro_{date_str}.log"

    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(numeric_level)

    if json_format:
        file_handler.setFormatter(JSONFormatter())
    else:
        file_handler.setFormatter(ConsoleFormatter())

    logger.addHandler(file_handler)

    logger.info(f"Logging initialized - Level: {level}, File: {log_file}")

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.

    Args:
        name: Module name (typically __name__).

    Returns:
        logging.Logger: Logger instance.
    """
    return logging.getLogger(f"fred_macro.{name}")
