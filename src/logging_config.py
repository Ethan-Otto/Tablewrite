"""
Centralized logging configuration for dnd_module_gen project.

This module provides consistent logging setup across all project scripts.
Log levels:
    DEBUG: Detailed processing steps, API calls, page-level operations
    INFO: Normal workflow progress (chapter/page processing, file creation)
    WARNING: Non-fatal issues (OCR fallback, word count mismatches, retries)
    ERROR: Processing failures, exceptions, unrecoverable errors

Usage:
    from logging_config import setup_logging

    logger = setup_logging(__name__)
    logger.info("Processing started")
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    name: str,
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
    console_output: bool = True
) -> logging.Logger:
    """
    Configure and return a logger instance.

    Args:
        name: Logger name (typically __name__ from calling module)
        level: Logging level (default: INFO)
        log_file: Optional path to write logs to file
        console_output: Whether to output to console (default: True)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # File handler
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_run_logger(script_name: str, run_dir: Path, level: int = logging.INFO) -> logging.Logger:
    """
    Get a logger configured for a specific run directory.

    This is useful for scripts that create timestamped run directories
    and want logs written to those directories.

    Args:
        script_name: Name of the script (e.g., 'pdf_to_xml')
        run_dir: Run directory path
        level: Logging level (default: INFO)

    Returns:
        Configured logger instance with both console and file output
    """
    log_file = run_dir / f"{script_name}.log"
    return setup_logging(script_name, level=level, log_file=log_file, console_output=True)
