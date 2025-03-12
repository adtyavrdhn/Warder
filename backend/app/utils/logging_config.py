"""
Logging configuration for the Warder application.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
import os


def configure_logging(logger_name, log_level=logging.INFO):
    """
    Configure logging for the application.

    Args:
        logger_name: Name of the logger
        log_level: Logging level

    Returns:
        Configured logger
    """
    # Create logger
    logger = logging.getLogger(logger_name)
    logger.setLevel(log_level)

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Create file handler
    os.makedirs("logs", exist_ok=True)
    file_handler = RotatingFileHandler(
        f"logs/{logger_name}.log", maxBytes=10485760, backupCount=5  # 10MB
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
