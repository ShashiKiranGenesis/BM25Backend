"""
Centralized logging configuration for the RAG application.

This module provides a configured logger instance with UTF-8 encoding support
for Windows compatibility, timestamps, log levels, and both console and file output.
"""

import logging
import os
import sys
import atexit


# Track all file handlers for cleanup
_file_handlers = []


def _flush_handlers():
    """Flush all file handlers on program exit."""
    for handler in _file_handlers:
        try:
            handler.flush()
            handler.close()
        except:
            pass


# Register cleanup on program exit
atexit.register(_flush_handlers)


def setup_logger(
    name: str = __name__,
    log_level: int = logging.INFO,
    log_file: str = "app.log",
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
) -> logging.Logger:
    """
    Set up and return a configured logger instance.

    Args:
        name: Logger name (typically __name__ of calling module)
        log_level: Logging level (default: logging.INFO)
        log_file: Path to log file (default: "app.log")
        log_format: Log message format string

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # Check if handlers already exist to avoid duplicates
    has_file_handler = any(isinstance(h, logging.FileHandler) for h in logger.handlers)
    has_console_handler = any(isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler) for h in logger.handlers)

    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)

    # Add console handler if it doesn't exist
    if not has_console_handler:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_formatter = logging.Formatter(log_format)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    # Add file handler if it doesn't exist
    if not has_file_handler:
        log_file_path = os.path.join("logs", log_file)
        file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
        file_handler.setLevel(log_level)
        file_formatter = logging.Formatter(log_format)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        _file_handlers.append(file_handler)

    # Prevent propagation to root logger to avoid duplicate logs
    logger.propagate = False

    return logger


def configure_root_logger(
    log_level: int = logging.INFO,
    log_file: str = "app.log",
) -> None:
    """
    Configure the root logger for the entire application.

    Args:
        log_level: Logging level for all loggers
        log_file: Path to main log file
    """
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    setup_logger(name="root", log_level=log_level, log_file=log_file, log_format=log_format)
