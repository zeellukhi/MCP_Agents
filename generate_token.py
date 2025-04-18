# generate_token.py
import asyncio
import os
from src.common.config import config # Make sure config loads .env

from src.tools.google_calendar_tool import load_or_refresh_credentials

import logging

logger = logging.getLogger(__name__)

async def generate():
    logger.info("Attempting to generate Google Calendar token...")
    # Ensure config paths are correct
    if not config.GOOGLE_CLIENT_SECRET_FILE or not os.path.exists(config.GOOGLE_CLIENT_SECRET_FILE):
        logger.error(f"Client secret file not found or not configured: {config.GOOGLE_CLIENT_SECRET_FILE}")
        return
    if not config.GOOGLE_TOKEN_FILE:
        logger.error("Token file path not configured in config.")
        return

    creds, success = await load_or_refresh_credentials()

    if success and creds:
        logger.info(f"Credentials successfully obtained/refreshed and saved to {config.GOOGLE_TOKEN_FILE}")
    elif creds and not creds.valid:
         logger.warning(f"Credentials exist but are invalid. Check {config.GOOGLE_TOKEN_FILE} or try deleting it and re-running.")
    else:
        logger.error("Failed to obtain credentials. Follow the console prompts if any.")

if __name__ == "__main__":
    # Ensure event loop policy is set for Windows if needed
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    # Ensure config is loaded (it should happen on import if setup correctly)
    logger.info(f"Using Client Secret: {config.GOOGLE_CLIENT_SECRET_FILE}")
    logger.info(f"Using Token File: {config.GOOGLE_TOKEN_FILE}")
    asyncio.run(generate())