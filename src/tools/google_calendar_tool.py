# src/tools/google_calendar_tool.py

import os.path
import datetime
from typing import Optional, Tuple, List

# Use central config and logger
from src.common.config import config

import logging

logger = logging.getLogger(__name__)

# Google API Imports
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Define the SCOPES required for the Calendar API
# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

async def load_or_refresh_credentials() -> Tuple[Optional[Credentials], bool]:
    """Loads existing credentials or initiates the OAuth flow.

    Returns:
        A tuple containing the Credentials object (or None) and a boolean indicating success.
    """
    creds = None
    token_file = config.GOOGLE_TOKEN_FILE
    secrets_file = config.GOOGLE_CLIENT_SECRET_FILE

    if not secrets_file:
        logger.error("Google client secret file path not configured in .env (GOOGLE_CLIENT_SECRET_FILE).")
        return None, False
    if not token_file:
        logger.error("Google token file path not configured in .env (GOOGLE_TOKEN_FILE).")
        return None, False
    if not os.path.exists(secrets_file):
         logger.error(f"Google client secret file not found at: {secrets_file}")
         return None, False

    try:
        # Check if token.json exists and load credentials
        if os.path.exists(token_file):
            logger.debug(f"Loading credentials from {token_file}")
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)

        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            logger.info("Credentials not found or invalid.")
            if creds and creds.expired and creds.refresh_token:
                logger.info("Credentials expired, attempting to refresh...")
                try:
                    creds.refresh(Request())
                    logger.info("Credentials refreshed successfully.")
                except Exception as refresh_error:
                    logger.error(f"Failed to refresh credentials: {refresh_error}. Need re-authentication.", exc_info=True)
                    # Indicate failure, might need manual re-auth by deleting token.json and running generate_token.py
                    # Return existing (invalid) creds but signal failure
                    return creds, False # Signal failure, let caller handle it
            else:
                # Initiate the OAuth flow (requires user interaction - run generate_token.py for this)
                logger.info("No valid credentials or refresh token. Initiating OAuth flow...")
                logger.warning("This should ideally be run via generate_token.py script for user interaction.")
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(secrets_file, SCOPES)
                    # Use run_local_server which starts a temporary local web server
                    # to receive the authorization code automatically.
                    logger.info("Starting local server for authentication flow...")
                    creds = flow.run_local_server(port=0) # <--- CORRECTED LINE
                    logger.info("OAuth flow completed successfully.")
                except Exception as flow_error:
                     logger.error(f"OAuth flow failed: {flow_error}", exc_info=True)
                     return None, False # Flow failed entirely

            # Save the credentials for the next run
            try:
                with open(token_file, "w") as token:
                    token.write(creds.to_json())
                logger.info(f"Credentials saved to {token_file}")
            except Exception as save_error:
                 logger.error(f"Failed to save credentials to {token_file}: {save_error}", exc_info=True)
                 # Credentials might be valid in memory but not saved
                 return creds, False # Signal potential issue

        # At this point, creds should be valid (either loaded, refreshed, or newly obtained)
        return creds, True # Credentials should be valid

    except Exception as e:
        logger.error(f"An unexpected error occurred during credential loading/refreshing: {e}", exc_info=True)
        return None, False
async def add_google_calendar_event(
    summary: str,
    start_time_str: str,
    end_time_str: str,
    description: Optional[str] = None,
    attendees: Optional[List[str]] = None
) -> str:
    """Adds an event to the user's primary Google Calendar.

    Args:
        summary: The title of the event.
        start_time_str: Start date/time in ISO format (e.g., 'YYYY-MM-DDTHH:MM:SS').
        end_time_str: End date/time in ISO format (e.g., 'YYYY-MM-DDTHH:MM:SS').
        description: Optional description for the event.
        attendees: Optional list of attendee email addresses.

    Returns:
        A string indicating success or failure, including the event link on success.
    """
    logger.info(f"Attempting to add Google Calendar event: '{summary}'")
    creds, creds_valid = await load_or_refresh_credentials()

    if not creds_valid or not creds:
        logger.error("Failed to obtain valid Google credentials.")
        # Provide a more specific message if possible
        if creds and creds.expired and not creds.refresh_token:
             return "Failed: Google credentials expired and couldn't be refreshed. Please re-authenticate (run generate_token.py)."
        return "Failed to add event: Could not load or refresh Google credentials. Run generate_token.py script if needed."

    try:
        service = build("calendar", "v3", credentials=creds)

        event = {
            "summary": summary,
            "description": description if description else "",
            "start": {
                "dateTime": start_time_str,
                "timeZone": config.TIMEZONE, # Use timezone from config
            },
            "end": {
                "dateTime": end_time_str,
                "timeZone": config.TIMEZONE, # Use timezone from config
            },
        }

        if attendees and isinstance(attendees, list):
            event["attendees"] = [{"email": email} for email in attendees]

        logger.debug(f"Creating event with data: {event}")

        # Use 'primary' for the user's main calendar
        created_event = (
            service.events()
            .insert(calendarId="primary", body=event)
            .execute()
        )

        event_link = created_event.get('htmlLink', 'N/A')
        logger.info(f"Event created successfully. Event ID: {created_event['id']}, Link: {event_link}")
        return f"Successfully added event '{summary}' to Google Calendar. Link: {event_link}"

    except HttpError as error:
        logger.error(f"An API error occurred: {error}", exc_info=True)
        error_details = error.resp.get('content', '{}')
        return f"Failed to add event: An API error occurred - {error_details}"
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        # Check for common format errors
        if "invalid time format" in str(e).lower():
             return f"Failed to add event: Invalid start or end time format. Use 'YYYY-MM-DDTHH:MM:SS'. Error: {e}"
        return f"Failed to add event: An unexpected error occurred - {e}"