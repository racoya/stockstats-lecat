"""Logger — Centralized logging configuration for LECAT.

Configures Python's standard logging library with:
  - Console handler: INFO level, concise format
  - File handler: DEBUG level, rotating (10MB, 5 backups), detailed format

All LECAT modules should use:
    from lecat.logger import get_logger
    logger = get_logger(__name__)
"""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

import sys

# Default log directory
if getattr(sys, "frozen", False):
    DEFAULT_LOG_DIR = str(Path.home() / ".lecat" / "logs")
else:
    DEFAULT_LOG_DIR = "logs"

DEFAULT_LOG_FILE = "lecat.log"
DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10MB
DEFAULT_BACKUP_COUNT = 5

_configured = False


def setup_logging(
    log_dir: str = DEFAULT_LOG_DIR,
    log_file: str = DEFAULT_LOG_FILE,
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
) -> None:
    """Configure the LECAT logging system.

    Safe to call multiple times — only configures once.

    Args:
        log_dir: Directory for log files.
        log_file: Log file name.
        console_level: Console handler level.
        file_level: File handler level.
        max_bytes: Max log file size before rotation.
        backup_count: Number of backup files to keep.
    """
    global _configured
    if _configured:
        return
    _configured = True

    # Create log directory
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Root logger for lecat namespace
    root_logger = logging.getLogger("lecat")
    root_logger.setLevel(logging.DEBUG)

    # Prevent duplicate handlers
    if root_logger.handlers:
        return

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_format = logging.Formatter("[%(levelname)s] %(message)s")
    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)

    # Rotating file handler
    file_path = log_path / log_file
    file_handler = RotatingFileHandler(
        file_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
    )
    file_handler.setLevel(file_level)
    file_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(file_format)
    root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a LECAT module.

    Ensures logging is configured before returning.

    Args:
        name: Module name (typically __name__).

    Returns:
        Configured logger instance.
    """
    setup_logging()
    return logging.getLogger(name)
