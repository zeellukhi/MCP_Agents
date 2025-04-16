# MCP_Agents/src/tools/google_calendar_tool.py
"""
Google Calendar Tool Module

Provides asynchronous functions to interact with the Google Calendar API,
specifically for adding events. Handles OAuth2 authentication flow using
credentials specified in the application configuration.
"""

import logging
import os
import asyncio
from datetime import datetime, date, time, timedelta
from typing import Optional, Tuple, Any

# Third-party imports for Google API and OAuth
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource
from googleapiclient.errors import HttpError

# Internal imports
from src.common.config import config, PROJECT_ROOT_PATH # Use centralized config and project root

# --- Setup ---
logger = logging.getLogger(__name__) # Get logger instance

# Constants
SCOPES = ['https://www.googleapis.com/auth/calendar'] # Define required permissions
_google_service: Optional[Resource] = None # Cache for the service object
_service_lock = asyncio.Lock() # Lock to prevent race conditions during service creation

# --- Helper Functions ---

def _get_token_path() -> str:
    """Returns the absolute path to the token file."""
    # GOOGLE_TOKEN_FILE might be relative, resolve it against project root
    return str(PROJECT_ROOT_PATH / config.GOOGLE_TOKEN_FILE)

def _get_client_secret_path() -> str:
    """Returns the absolute path to the client secrets file."""
    if not config.GOOGLE_CLIENT_SECRET_FILE:
        return None # Should have been caught by config validation, but double-check
    # Resolve potential relative path against project root
    return str(PROJECT_ROOT_PATH / config.GOOGLE_CLIENT_SECRET_FILE)


async def _get_google_calendar_service() -> Optional[Resource]:
    """
    Handles Google OAuth2 authentication flow and returns an authorized Calendar service object.
    Uses cached service object if available and valid. Manages token refresh and
    initial user authorization flow.

    Output:
        Optional[Resource]: An authorized Google Calendar API service object,
                            or None if authentication fails.
    """
    global _google_service
    async with _service_lock: # Ensure only one coroutine tries to build service at a time
        creds: Optional[Credentials] = None
        token_path = _get_token_path()
        secret_path = _get_client_secret_path()

        if not secret_path or not os.path.exists(secret_path):
            logger.error(f"Google Client Secret file not found at '{secret_path}'. "
                        "Cannot authenticate Google Calendar.")
            return None

        # Check if token file exists
        if os.path.exists(token_path):
            try:
                creds = Credentials.from_authorized_user_file(token_path, SCOPES)
                logger.debug(f"Loaded credentials from {token_path}")
            except Exception as e:
                logger.warning(f"Failed to load token file from {token_path}: {e}. Will attempt re-auth.")
                creds = None # Force re-authentication attempt

        # If no valid credentials, try to refresh or run auth flow
        if not creds or not creds.valid:
            needs_auth = True
            if creds and creds.expired and creds.refresh_token:
                logger.info("Google credentials expired, attempting refresh...")
                try:
                    # Use async run_in_executor for blocking refresh request
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(None, creds.refresh, Request())
                    logger.info("Credentials refreshed successfully.")
                    needs_auth = False
                except Exception as e:
                    logger.error(f"Failed to refresh Google credentials: {e}. Need new authorization.", exc_info=True)
                    # Delete potentially corrupted token file to force re-auth
                    try:
                         os.remove(token_path)
                         logger.info(f"Removed potentially corrupted token file: {token_path}")
                    except OSError:
                         logger.warning(f"Could not remove token file: {token_path}")
                    creds = None # Ensure re-auth happens
                    needs_auth = True

            # If still need authentication (no creds, or refresh failed)
            if needs_auth:
                logger.info("No valid Google credentials found or refresh failed. Starting OAuth flow...")
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(secret_path, SCOPES)
                    # Run the potentially blocking auth flow in an executor
                    loop = asyncio.get_running_loop()
                    # Note: This will print a URL to the console and wait for user interaction
                    creds = await loop.run_in_executor(None, flow.run_local_server, 0)
                    logger.info("OAuth flow completed successfully.")
                except FileNotFoundError:
                     logger.error(f"Client secrets file not found at {secret_path}. Cannot run OAuth flow.")
                     return None
                except Exception as e:
                    logger.error(f"Google OAuth flow failed: {e}", exc_info=True)
                    return None # Authentication failed

            # Save the credentials for the next run
            if creds:
                try:
                    with open(token_path, 'w') as token_file:
                        token_file.write(creds.to_json())
                    logger.info(f"Saved new Google credentials to {token_path}")
                except IOError as e:
                     logger.error(f"Failed to save token file to {token_path}: {e}")
                     # Proceed with current creds, but warn user


        # Build and cache the service object if authentication succeeded
        if creds and creds.valid:
            try:
                # Use async run_in_executor for blocking build call
                loop = asyncio.get_running_loop()
                _google_service = await loop.run_in_executor(
                    None, build, 'calendar', 'v3', credentials=creds
                )
                logger.info("Google Calendar service built successfully.")
                return _google_service
            except Exception as e:
                logger.error(f"Failed to build Google Calendar service: {e}", exc_info=True)
                _google_service = None # Ensure service is None if build fails
                return None
        else:
             logger.error("Could not obtain valid Google credentials after auth attempt.")
             _google_service = None
             return None


def _parse_datetime(dt_str: str) -> Tuple[Optional[datetime], Optional[date], bool]:
    """
    Parses a string into either a datetime or date object.
    Handles ISO formats (YYYY-MM-DDTHH:MM:SS or YYYY-MM-DD).

    Args:
        dt_str: The date/datetime string to parse.

    Returns:
        Tuple containing:
        - Optional[datetime]: Parsed datetime object if time is included.
        - Optional[date]: Parsed date object if only date is provided.
        - bool: True if parsing was successful, False otherwise.
    """
    try:
        # Try parsing as full datetime first
        dt_obj = datetime.fromisoformat(dt_str)
        return dt_obj, None, True
    except ValueError:
        try:
            # Try parsing as date only
            date_obj = date.fromisoformat(dt_str)
            return None, date_obj, True
        except ValueError:
            logger.warning(f"Could not parse datetime string: '{dt_str}'. Expected YYYY-MM-DD or ISO datetime format.")
            return None, None, False


# --- Tool Function ---

async def add_google_calendar_event(
    summary: str,
    start_datetime_str: str,
    end_datetime_str: Optional[str] = None,
    description: Optional[str] = None,
    location: Optional[str] = None
) -> str:
    """
    Adds an event to the primary Google Calendar.

    Handles both specific time events (if start_datetime_str includes time)
    and all-day events (if start_datetime_str is only a date).

    Input:
        summary (str): The title of the event (Required).
        start_datetime_str (str): Start date (YYYY-MM-DD) or datetime (ISO format). (Required).
        end_datetime_str (Optional[str]): End date/datetime (same format as start).
                                         If omitted for a timed event, defaults to 1 hour after start.
                                         If omitted for an all-day event, defaults to a single day event.
        description (Optional[str]): Event description.
        location (Optional[str]): Event location.

    Output:
        str: Confirmation message with event link or an error message.
    """
    logger.info(f"Attempting to add Google Calendar event: '{summary}' starting {start_datetime_str}")

    service = await _get_google_calendar_service()
    if not service:
        return "Error: Failed to authenticate Google Calendar service. Check logs and configuration."

    start_dt, start_date, parsed_start = _parse_datetime(start_datetime_str)
    if not parsed_start:
        return f"Error: Invalid start date/time format: '{start_datetime_str}'. Use YYYY-MM-DD or ISO format."

    is_all_day = start_date is not None # True if only date was parsed

    event: Dict[str, Any] = {
        'summary': summary,
        'start': {},
        'end': {},
    }
    if description:
        event['description'] = description
    if location:
        event['location'] = location

    # Process start and end times/dates
    if is_all_day:
        event['start']['date'] = start_date.isoformat()
        end_date_obj = start_date # Default to same day

        if end_datetime_str:
            _, parsed_end_date, parsed_end = _parse_datetime(end_datetime_str)
            if parsed_end and parsed_end_date:
                 # For all-day events, end date is exclusive, so add one day if
                 # the user likely meant "until the end of this day".
                 # If start=2025-04-16, end=2025-04-16, it's a 1-day event.
                 # If start=2025-04-16, end=2025-04-17, it's a 1-day event (ends *before* 17th).
                 # If start=2025-04-16, end=2025-04-18, it's a 2-day event (16th, 17th).
                if parsed_end_date >= start_date:
                     end_date_obj = parsed_end_date + timedelta(days=1) # API needs exclusive end date
                else:
                     logger.warning("End date cannot be before start date for all-day event. Using start date.")
                     end_date_obj = start_date + timedelta(days=1)
            else:
                logger.warning(f"Could not parse end date '{end_datetime_str}'. Defaulting to single day.")
                end_date_obj = start_date + timedelta(days=1)
        else:
             # No end date provided, default to single all-day event
             end_date_obj = start_date + timedelta(days=1)

        event['end']['date'] = end_date_obj.isoformat()
        logger.debug(f"Creating all-day event from {event['start']['date']} to {event['end']['date']}")

    else: # Timed event
        event['start'] = {
            'dateTime': start_dt.isoformat(),
            'timeZone': config.CALENDAR_TIMEZONE,
        }
        end_dt_obj = start_dt + timedelta(hours=1) # Default to 1 hour duration

        if end_datetime_str:
            parsed_end_dt, _, parsed_end = _parse_datetime(end_datetime_str)
            if parsed_end and parsed_end_dt:
                if parsed_end_dt > start_dt:
                     end_dt_obj = parsed_end_dt
                else:
                     logger.warning("End time cannot be before start time. Using default 1-hour duration.")
            else:
                 logger.warning(f"Could not parse end datetime '{end_datetime_str}'. Using default 1-hour duration.")

        event['end'] = {
            'dateTime': end_dt_obj.isoformat(),
            'timeZone': config.CALENDAR_TIMEZONE,
        }
        logger.debug(f"Creating timed event from {event['start']['dateTime']} to {event['end']['dateTime']} ({config.CALENDAR_TIMEZONE})")


    # --- API Call ---
    try:
        logger.info(f"Inserting event into primary calendar: {event}")
        # Use async run_in_executor for the blocking API call
        loop = asyncio.get_running_loop()
        created_event = await loop.run_in_executor(
            None,
            lambda: service.events().insert(calendarId='primary', body=event).execute()
        )

        event_url = created_event.get('htmlLink', 'N/A')
        logger.info(f"Successfully created Google Calendar event. ID: {created_event.get('id')}, URL: {event_url}")
        return f"Event '{summary}' created successfully. View it here: {event_url}"

    except HttpError as e:
        error_details = e.resp.get('content', str(e))
        logger.error(f"Google API Error adding event '{summary}': {error_details}", exc_info=True)
        return f"Error adding Google Calendar event '{summary}': {error_details}"
    except Exception as e:
        logger.error(f"Unexpected error adding event '{summary}': {e}", exc_info=True)
        return f"An unexpected error occurred while adding event '{summary}'."