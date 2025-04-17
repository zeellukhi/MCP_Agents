# MCP_Agents/src/tools/notion_tool.py
"""
Notion Tool Module

Provides asynchronous functions to interact with the Notion API for managing
tasks, checklists, and expenses using the official notion-client library.
Relies on configuration loaded via src.common.config.
"""

import logging
import asyncio
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Union

# Third-party imports
from notion_client import AsyncClient as NotionAsyncClient
from notion_client.helpers import is_full_page_or_database
from notion_client.errors import APIResponseError

# Internal imports
from src.common.config import config # Use centralized config

# --- Setup ---
logger = logging.getLogger(__name__) # Get logger instance

# Initialize Notion Client (only if API key is provided)
notion: Optional[NotionAsyncClient] = None
if config and config.NOTION_API_KEY:
    notion = NotionAsyncClient(auth=config.NOTION_API_KEY)
    logger.info("Notion client initialized.")
else:
    logger.warning("NOTION_API_KEY not found in environment variables. Notion tool functions will be disabled.")

# --- Helper Functions ---

def _format_date(date_obj: Union[datetime, date]) -> Dict[str, str]:
    """Formats a datetime or date object into Notion's date property format."""
    return {"start": date_obj.isoformat()}

def _validate_notion_client() -> bool:
    """Checks if the Notion client is initialized."""
    if not notion:
        logger.error("Notion client is not initialized. Check NOTION_API_KEY.")
        return False
    return True

# --- Tool Functions ---

async def add_notion_task(
    task_name: str,
    due_date: Optional[str] = None,
    priority: Optional[str] = None,
    project: Optional[str] = None,
    notes: Optional[str] = None
) -> str:
    """
    Adds a new task page to the configured Notion Task Database.

    Input:
        task_name (str): The name/title of the task (Required).
        due_date (Optional[str]): The due date in 'YYYY-MM-DD' format.
        priority (Optional[str]): Priority level (e.g., 'High', 'Medium', 'Low').
                                  Assumes a 'Priority' Select property exists.
        project (Optional[str]): Associated project name.
                                 Assumes a 'Project' Relation or Select property exists.
        notes (Optional[str]): Additional details/content for the task page body.

    Output:
        str: Confirmation message with task name/URL or an error message.
    """
    if not _validate_notion_client() or not config.NOTION_TASK_DB_ID:
        return "Error: Notion client or Task Database ID is not configured."

    logger.info(f"Attempting to add Notion task: '{task_name}'")
    properties: Dict[str, Any] = {
        "Name": {"title": [{"text": {"content": task_name}}]} # Assumes 'Name' is the Title property
    }

    if due_date:
        try:
            # Ensure correct parsing for YYYY-MM-DD
            dt_obj = date.fromisoformat(due_date) # Use date.fromisoformat for YYYY-MM-DD
            properties["Due Date"] = {"date": _format_date(dt_obj)} # Assumes 'Due Date' is a Date property
        except ValueError:
            logger.warning(f"Invalid due_date format: {due_date}. Should be YYYY-MM-DD.")
            # Return an error as date is likely important if provided
            return f"Error: Invalid due_date format '{due_date}'. Use YYYY-MM-DD."

    if priority:
        properties["Priority"] = {"select": {"name": priority}} # Assumes 'Priority' is a Select property

    if project:
        # Assuming Select for simplicity. Adjust if it's a Relation property (requires page ID).
        properties["Project"] = {"select": {"name": project}} # Assumes 'Project' is a Select property

    # --- Prepare children blocks ONLY if notes are provided ---
    children_blocks = []
    if notes and notes.strip(): # Check if notes actually contain text
        children_blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": notes}}]
            }
        })

    # --- Construct payload for API call ---
    payload = {
         "parent": {"database_id": config.NOTION_TASK_DB_ID},
         "properties": properties
    }
    # *** Conditionally add children ***
    if children_blocks:
         payload["children"] = children_blocks
    # If children_blocks is empty, the 'children' key will NOT be sent, avoiding the null issue.


    try:
        # Use the constructed payload
        response = await notion.pages.create(**payload)
        page_id = response.get('id', 'N/A')
        page_url = response.get('url', '')
        logger.info(f"Successfully added Notion task '{task_name}'. Page ID: {page_id}")
        # Provide a more useful confirmation including the URL
        return f"Task '{task_name}' added to Notion. URL: {page_url}"

    except APIResponseError as e:
        # Extract the core error message from Notion's response body
        error_message = e.body.get('message', str(e))
        logger.error(f"Notion API Error adding task '{task_name}': {error_message}", exc_info=True)
        # Return a simple, clean error string
        return f"Error adding Notion task '{task_name}': {error_message}"
    except Exception as e:
        logger.error(f"Unexpected error adding Notion task '{task_name}': {e}", exc_info=True)
        # Return a simple, clean error string
        return f"An unexpected error occurred while adding task '{task_name}'."


# --- Other functions (add_daily_checklist_item, add_daily_expense, etc.) remain the same ---
# Make sure they also return simple strings on error if you modify them.

async def add_daily_checklist_item(item_name: str, checked: bool = False) -> str:
    # ... (keep existing implementation) ...
    if not _validate_notion_client() or not config.NOTION_DAILY_CHECKLIST_DB_ID:
        return "Error: Notion client or Daily Checklist Database ID is not configured."
    # ... rest of the function ...
    try:
        # ... notion call ...
        return f"Checklist item '{item_name}' added for today."
    except APIResponseError as e:
         error_message = e.body.get('message', str(e))
         logger.error(f"Notion API Error adding checklist item '{item_name}': {error_message}", exc_info=True)
         return f"Error adding checklist item '{item_name}': {error_message}" # Simple string
    except Exception as e:
         logger.error(f"Unexpected error adding checklist item '{item_name}': {e}", exc_info=True)
         return f"An unexpected error occurred while adding checklist item '{item_name}'." # Simple string

async def add_daily_expense(
    item_name: str,
    amount: float,
    category: Optional[str] = None,
    expense_date: Optional[str] = None
) -> str:
    # ... (keep existing implementation) ...
    if not _validate_notion_client() or not config.NOTION_EXPENSE_DB_ID:
        return "Error: Notion client or Expense Database ID is not configured."
    # ... rest of the function ...
    try:
        # ... notion call ...
        return f"Expense '{item_name}' of {amount} added for {expense_date}."
    except APIResponseError as e:
        error_message = e.body.get('message', str(e))
        logger.error(f"Notion API Error adding expense '{item_name}': {error_message}", exc_info=True)
        return f"Error adding expense '{item_name}': {error_message}" # Simple string
    except Exception as e:
        logger.error(f"Unexpected error adding expense '{item_name}': {e}", exc_info=True)
        return f"An unexpected error occurred while adding expense '{item_name}'." # Simple string


async def update_task_status(page_id: str, status: str) -> str:
    # ... (keep existing implementation) ...
    if not _validate_notion_client():
        return "Error: Notion client is not configured."
    # ... rest of the function ...
    try:
        # ... notion call ...
        return f"Task status updated to '{status}'."
    except APIResponseError as e:
        error_message = e.body.get('message', str(e))
        logger.error(f"Notion API Error updating status for page {page_id}: {error_message}", exc_info=True)
        return f"Error updating status for task {page_id}: {error_message}" # Simple string
    except Exception as e:
        logger.error(f"Unexpected error updating status for page {page_id}: {e}", exc_info=True)
        return f"An unexpected error occurred while updating status for task {page_id}." # Simple string

# --- Make sure any other tool functions like delete_task, create_travel_plan, update_task_notes ---
# --- also return simple strings on error if you implement/uncomment them ---