import logging
import sys
from config import LOG_LEVEL
import colorlog


def get_logger(name: str) -> logging.Logger:
    """
    Returns a named logger with colorized formatting (like FastAPI).
    Usage:
        from app.logger import get_logger
        logger = get_logger(__name__)
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = colorlog.StreamHandler(sys.stdout)
        formatter = colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s%(reset)s | %(log_color)s%(levelname)-8s%(reset)s | %(cyan)s%(name)s%(reset)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            log_colors={
                "DEBUG": "blue",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
            },
            reset=True,
            style="%"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    logger.propagate = False

    return logger
