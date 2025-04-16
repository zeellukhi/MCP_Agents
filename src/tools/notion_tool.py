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
    """
    Formats a datetime or date object into Notion's date property format.

    Args:
        date_obj: The datetime or date object.

    Returns:
        A dictionary suitable for Notion's date property (e.g., {"start": "YYYY-MM-DD"}).
    """
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
        notes (Optional[str]): Additional details for the task.
                               Assumes a 'Notes' Text property exists.

    Output:
        str: Confirmation message with task name or an error message.
    """
    if not _validate_notion_client() or not config.NOTION_TASK_DB_ID:
        return "Error: Notion client or Task Database ID is not configured."

    logger.info(f"Attempting to add Notion task: '{task_name}'")
    properties: Dict[str, Any] = {
        "Name": {"title": [{"text": {"content": task_name}}]} # Assumes 'Name' is the Title property
    }

    if due_date:
        try:
            dt_obj = datetime.strptime(due_date, '%Y-%m-%d').date()
            properties["Due Date"] = {"date": _format_date(dt_obj)} # Assumes 'Due Date' is a Date property
        except ValueError:
            logger.warning(f"Invalid due_date format: {due_date}. Should be YYYY-MM-DD.")
            # Optionally return error here, or just skip the date
            # return f"Error: Invalid due_date format '{due_date}'. Use YYYY-MM-DD."

    if priority:
        properties["Priority"] = {"select": {"name": priority}} # Assumes 'Priority' is a Select property

    if project:
        # Handling project depends on whether it's a Select or Relation property.
        # Assuming Select for simplicity here. Adjust if it's a Relation.
        properties["Project"] = {"select": {"name": project}} # Assumes 'Project' is a Select property

    # Children block for notes (better than property for longer text)
    children = []
    if notes:
        children.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": notes}}]
            }
        })

    try:
        response = await notion.pages.create(
            parent={"database_id": config.NOTION_TASK_DB_ID},
            properties=properties,
            children=children if children else None # Add children only if notes exist
        )
        page_id = response.get('id', 'N/A')
        page_url = response.get('url', '')
        logger.info(f"Successfully added Notion task '{task_name}'. Page ID: {page_id}")
        return f"Task '{task_name}' added to Notion. URL: {page_url}"

    except APIResponseError as e:
        logger.error(f"Notion API Error adding task '{task_name}': {e}", exc_info=True)
        return f"Error adding Notion task '{task_name}': {e.body.get('message', str(e))}"
    except Exception as e:
        logger.error(f"Unexpected error adding Notion task '{task_name}': {e}", exc_info=True)
        return f"An unexpected error occurred while adding task '{task_name}'."


async def add_daily_checklist_item(item_name: str, checked: bool = False) -> str:
    """
    Adds an item to the Daily Checklist Notion Database for today's date.
    Assumes the database has a 'Name' (Title) property and a 'Date' (Date) property.

    Input:
        item_name (str): The name of the checklist item (Required).
        checked (bool): Whether the item should be marked as checked (Defaults to False).
                        Assumes a 'Checked' Checkbox property exists.

    Output:
        str: Confirmation or error message.
    """
    if not _validate_notion_client() or not config.NOTION_DAILY_CHECKLIST_DB_ID:
        return "Error: Notion client or Daily Checklist Database ID is not configured."

    logger.info(f"Attempting to add checklist item: '{item_name}'")
    today = date.today()
    properties: Dict[str, Any] = {
        "Name": {"title": [{"text": {"content": item_name}}]}, # Assumes 'Name' is Title
        "Date": {"date": _format_date(today)}, # Assumes 'Date' is Date property
        "Checked": {"checkbox": checked} # Assumes 'Checked' is Checkbox property
    }

    try:
        response = await notion.pages.create(
            parent={"database_id": config.NOTION_DAILY_CHECKLIST_DB_ID},
            properties=properties,
        )
        page_id = response.get('id', 'N/A')
        logger.info(f"Successfully added checklist item '{item_name}' for {today}. Page ID: {page_id}")
        return f"Checklist item '{item_name}' added for today."

    except APIResponseError as e:
        logger.error(f"Notion API Error adding checklist item '{item_name}': {e}", exc_info=True)
        return f"Error adding checklist item '{item_name}': {e.body.get('message', str(e))}"
    except Exception as e:
        logger.error(f"Unexpected error adding checklist item '{item_name}': {e}", exc_info=True)
        return f"An unexpected error occurred while adding checklist item '{item_name}'."


async def add_daily_expense(
    item_name: str,
    amount: float,
    category: Optional[str] = None,
    expense_date: Optional[str] = None
) -> str:
    """
    Adds an expense item to the Daily Expense Notion Database.

    Input:
        item_name (str): Description of the expense (Required).
        amount (float): The expense amount (Required).
        category (Optional[str]): Expense category (e.g., 'Food', 'Travel').
                                  Assumes a 'Category' Select property exists.
        expense_date (Optional[str]): Date of expense ('YYYY-MM-DD'). Defaults to today.

    Output:
        str: Confirmation or error message.
    """
    if not _validate_notion_client() or not config.NOTION_EXPENSE_DB_ID:
        return "Error: Notion client or Expense Database ID is not configured."

    logger.info(f"Attempting to add expense: '{item_name}' for {amount}")

    target_date: date
    if expense_date:
        try:
            target_date = datetime.strptime(expense_date, '%Y-%m-%d').date()
        except ValueError:
            logger.warning(f"Invalid expense_date format: {expense_date}. Using today.")
            target_date = date.today()
    else:
        target_date = date.today()

    properties: Dict[str, Any] = {
        "Item": {"title": [{"text": {"content": item_name}}]}, # Assumes 'Item' is Title
        "Amount": {"number": amount}, # Assumes 'Amount' is Number property
        "Date": {"date": _format_date(target_date)}, # Assumes 'Date' is Date property
    }
    if category:
        properties["Category"] = {"select": {"name": category}} # Assumes 'Category' is Select

    try:
        response = await notion.pages.create(
            parent={"database_id": config.NOTION_EXPENSE_DB_ID},
            properties=properties,
        )
        page_id = response.get('id', 'N/A')
        logger.info(f"Successfully added expense '{item_name}' for {target_date}. Page ID: {page_id}")
        return f"Expense '{item_name}' of {amount} added for {target_date}."

    except APIResponseError as e:
        logger.error(f"Notion API Error adding expense '{item_name}': {e}", exc_info=True)
        return f"Error adding expense '{item_name}': {e.body.get('message', str(e))}"
    except Exception as e:
        logger.error(f"Unexpected error adding expense '{item_name}': {e}", exc_info=True)
        return f"An unexpected error occurred while adding expense '{item_name}'."

# --- Additional Notion Functions (Example stubs - implement as needed) ---

async def update_task_status(page_id: str, status: str) -> str:
    """
    Updates the status of a Notion task page.

    Input:
        page_id (str): The Notion Page ID of the task to update.
        status (str): The new status (e.g., 'Done', 'In Progress').
                      Assumes a 'Status' Select or Status property exists.

    Output:
        str: Confirmation or error message.
    """
    if not _validate_notion_client():
        return "Error: Notion client is not configured."
    logger.info(f"Attempting to update status for page {page_id} to '{status}'")
    try:
        # Determine if 'Status' is a 'status' type or 'select' type property
        # This example assumes 'status' type. Adjust if needed.
        properties = {"Status": {"status": {"name": status}}}
        await notion.pages.update(page_id=page_id, properties=properties)
        logger.info(f"Successfully updated status for page {page_id} to '{status}'")
        return f"Task status updated to '{status}'."
    except APIResponseError as e:
        logger.error(f"Notion API Error updating status for page {page_id}: {e}", exc_info=True)
        return f"Error updating status for task {page_id}: {e.body.get('message', str(e))}"
    except Exception as e:
        logger.error(f"Unexpected error updating status for page {page_id}: {e}", exc_info=True)
        return f"An unexpected error occurred while updating status for task {page_id}."

# Add other functions like delete_task, create_travel_plan, update_task_notes
# following a similar pattern with error handling and logging.
# Ensure property names ('Name', 'Due Date', 'Status', etc.) match your Notion setup.