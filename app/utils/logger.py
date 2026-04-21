import logging
import sys
from config import LOG_LEVEL, LOG_FORMAT


def get_logger(name: str) -> logging.Logger:
    """
    Returns a named logger with consistent formatting.
    Usage:
        from app.logger import get_logger
        logger = get_logger(__name__)
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(handler)

    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    logger.propagate = False

    return logger
