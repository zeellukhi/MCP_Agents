# MCP_Agents/src/common/config.py
"""
Configuration Module

Loads environment variables from a .env file and provides access to them
through a Config object. Includes basic validation for required variables.
"""

import os
import logging
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Determine the project root directory (assuming this file is in src/common)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_PATH = PROJECT_ROOT / '.env'

# Load the .env file
if ENV_PATH.is_file():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    # Use basicConfig here temporarily in case logger isn't set up yet
    logging.basicConfig(level=logging.WARNING)
    logging.warning(f".env file not found at {ENV_PATH}. "
                    "Application might not work correctly without configuration.")

class ConfigError(Exception):
    """Custom exception for configuration errors."""
    pass

class _Config:
    """
    Holds the application configuration loaded from environment variables.

    Includes validation checks for essential settings.
    """
    def __init__(self):
        # --- Google AI ---
        self.GOOGLE_API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY")

        # --- Notion ---
        self.NOTION_API_KEY: Optional[str] = os.getenv("NOTION_API_KEY")
        self.NOTION_TASK_DB_ID: Optional[str] = os.getenv("NOTION_TASK_DB_ID")
        self.NOTION_DAILY_CHECKLIST_DB_ID: Optional[str] = os.getenv("NOTION_DAILY_CHECKLIST_DB_ID")
        self.NOTION_EXPENSE_DB_ID: Optional[str] = os.getenv("NOTION_EXPENSE_DB_ID")

        # --- Google Calendar ---
        self.GOOGLE_CLIENT_SECRET_FILE: Optional[str] = os.getenv("GOOGLE_CLIENT_SECRET_FILE")
        self.GOOGLE_TOKEN_FILE: str = os.getenv("GOOGLE_TOKEN_FILE", "token.json") # Default provided
        self.CALENDAR_TIMEZONE: str = os.getenv("CALENDAR_TIMEZONE", "UTC") # Default provided

        # --- Application Settings ---
        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
        self.DEBUG_MODE: bool = os.getenv("DEBUG_MODE", "False").lower() == "true"
        self.TIMEZONE: str = os.getenv("TIMEZONE", "UTC") # Default provided

        # --- Server Settings ---
        self.API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
        self.API_PORT: int = int(os.getenv("API_PORT", "8081"))
        self.MCP_HOST: str = os.getenv("MCP_HOST", "0.0.0.0")
        self.MCP_PORT: int = int(os.getenv("MCP_PORT", "9091"))

        # --- Validation ---
        self._validate()

    def _validate(self):
        """Performs basic validation checks on required configuration."""
        required_vars = {
            "GOOGLE_API_KEY": self.GOOGLE_API_KEY,
            "NOTION_API_KEY": self.NOTION_API_KEY,
            "NOTION_TASK_DB_ID": self.NOTION_TASK_DB_ID,
            "NOTION_DAILY_CHECKLIST_DB_ID": self.NOTION_DAILY_CHECKLIST_DB_ID,
            "NOTION_EXPENSE_DB_ID": self.NOTION_EXPENSE_DB_ID,
            "GOOGLE_CLIENT_SECRET_FILE": self.GOOGLE_CLIENT_SECRET_FILE,
        }
        missing_vars = [name for name, value in required_vars.items() if not value]
        if missing_vars:
            raise ConfigError(f"Missing required environment variables in .env: {', '.join(missing_vars)}")

        if self.GOOGLE_CLIENT_SECRET_FILE and not Path(self.GOOGLE_CLIENT_SECRET_FILE).is_file():
             # Allow relative paths by checking against project root
             if not (PROJECT_ROOT / self.GOOGLE_CLIENT_SECRET_FILE).is_file():
                # Use basicConfig here as logger might not be fully configured yet
                logging.basicConfig(level=logging.WARNING)
                logging.warning(
                    f"GOOGLE_CLIENT_SECRET_FILE path '{self.GOOGLE_CLIENT_SECRET_FILE}' not found. "
                    f"Looked relative to project root: {PROJECT_ROOT}. "
                    f"Google Calendar tool will fail authorization."
                )
                # Don't raise error here, let the tool handle the failure later if used

        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.LOG_LEVEL not in valid_log_levels:
            logging.warning(f"Invalid LOG_LEVEL '{self.LOG_LEVEL}'. Defaulting to INFO. "
                            f"Valid levels are: {valid_log_levels}")
            self.LOG_LEVEL = "INFO"

# Singleton instance of the configuration
try:
    config = _Config()
except ConfigError as e:
    logging.basicConfig(level=logging.CRITICAL)
    logging.critical(f"Configuration Error: {e}")
    # Exit or raise is appropriate here in a real app
    # For this script, we'll allow it to continue so other files can be reviewed,
    # but highlight the critical failure.
    config = None # Indicate configuration failed
    print(f"\nCRITICAL CONFIGURATION ERROR: {e}\nApplication cannot run correctly.\n")


# Make PROJECT_ROOT easily accessible if needed elsewhere
# e.g., resolving paths relative to the project root
PROJECT_ROOT_PATH = PROJECT_ROOT