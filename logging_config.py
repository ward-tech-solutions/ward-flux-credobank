"""
WARD TECH SOLUTIONS - Logging Configuration
Centralized logging setup for all modules
"""
import logging
import logging.handlers
import os
from datetime import datetime


def setup_logging(log_level=logging.INFO):
    """
    Configure application-wide logging

    Args:
        log_level: Logging level (default: INFO)
    """
    # Create logs directory
    os.makedirs("logs", exist_ok=True)

    # Create formatters
    detailed_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    simple_formatter = logging.Formatter("%(levelname)s: %(message)s")

    # Console handler (simple format)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)

    # File handler with rotation (detailed format)
    file_handler = logging.handlers.RotatingFileHandler(
        "logs/ward_app.log", maxBytes=10 * 1024 * 1024, backupCount=5  # 10MB  # Keep 5 old files
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)

    # Error file handler (errors only)
    error_handler = logging.handlers.RotatingFileHandler(
        "logs/ward_errors.log", maxBytes=5 * 1024 * 1024, backupCount=3  # 5MB  # Keep 3 old files
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)

    # Set specific log levels for noisy libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("WARD Tech Solutions - Logging Started")
    logger.info(f"Log Level: {logging.getLevelName(log_level)}")
    logger.info(f"Log Files: logs/ward_app.log, logs/ward_errors.log")
    logger.info("=" * 60)


def get_logger(name):
    """
    Get a logger instance for a module

    Args:
        name: Logger name (usually __name__)

    Returns:
        logging.Logger instance
    """
    return logging.getLogger(name)
