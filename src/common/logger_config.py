# MCP_Agents/src/common/logger_config.py
"""
Logging Configuration Module

Provides a function to set up consistent logging across the application,
including console output and rotating file logs stored in a 'logs' directory.
"""

import logging
import logging.handlers
import os
from pathlib import Path
from .config import PROJECT_ROOT_PATH, config # Import config for log level

# Define log directory and file path relative to project root
LOG_DIR = PROJECT_ROOT_PATH / "logs"
LOG_FILE = LOG_DIR / "app.log"
# Define log format
LOG_FORMAT = '%(asctime)s - %(name)s - [%(levelname)s] - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

def setup_logging():
    """
    Sets up global logging configuration based on settings in config.

    - Creates the log directory if it doesn't exist.
    - Configures a rotating file handler to write logs to `logs/app.log`.
    - Configures a stream handler to write logs to the console.
    - Sets the global log level based on `config.LOG_LEVEL`.
    - Adjusts log levels for potentially noisy third-party libraries.

    Returns:
        None
    """
    if config is None:
        # Use basicConfig for critical failure logging if config loading failed
        logging.basicConfig(level=logging.CRITICAL, format=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
        logging.critical("Cannot setup logging because configuration failed to load.")
        return

    log_level_str = config.LOG_LEVEL
    log_level = getattr(logging, log_level_str, logging.INFO)

    # Create the logs directory if it doesn't exist
    try:
        LOG_DIR.mkdir(exist_ok=True)
    except OSError as e:
        # Use basicConfig for critical failure logging
        logging.basicConfig(level=logging.CRITICAL, format=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
        logging.critical(f"Failed to create log directory {LOG_DIR}: {e}")
        return # Cannot proceed without log directory

    # --- Root Logger Configuration ---
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level) # Set the minimum level for the root logger

    # Clear existing handlers to prevent duplicate logs if called multiple times
    # (useful in some testing scenarios or complex startup sequences)
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # --- Formatter ---
    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    # --- Console Handler ---
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level) # Match root logger level for console
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # --- Rotating File Handler ---
    try:
        # Rotates logs when they reach 5MB, keeping up to 5 backup files.
        file_handler = logging.handlers.RotatingFileHandler(
            LOG_FILE, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8'
        )
        file_handler.setLevel(log_level) # Match root logger level for file
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        root_logger.error(f"Failed to set up file handler for {LOG_FILE}: {e}", exc_info=True)
        # Continue with console logging if file logging fails

    # --- Adjust noisy loggers (optional) ---
    # Uvicorn access logs can be noisy; set them higher unless debugging network
    uvicorn_access_level = logging.DEBUG if config.DEBUG_MODE else logging.WARNING
    logging.getLogger("uvicorn.access").setLevel(uvicorn_access_level)
    logging.getLogger("uvicorn.error").setLevel(log_level) # Match app level
    # Other potentially noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("googleapiclient").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.INFO) # Can be noisy on DEBUG

    # Log completion
    root_logger.info(f"Logging setup complete. Level: {log_level_str}. Outputting to console and {LOG_FILE}")

# --- Make __init__.py files ---
# Ensure you have empty __init__.py files in src/ and src/common/ directories
# to make them recognizable as Python packages.

# MCP_Agents/src/__init__.py (empty file)
# MCP_Agents/src/common/__init__.py (empty file)