# src/tools/notion_tool.py

import os
import asyncio
# import logging # Use central logger instead
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from notion_client import AsyncClient as NotionAsyncClient
# from dotenv import load_dotenv # Handled by central config

# Use central config and logger
from src.common.config import config

import logging

logger = logging.getLogger(__name__) # Get logger instance

# --- Notion Client Helper ---
# Helper to initialize client - avoid global instance
def _get_notion_client() -> Optional[NotionAsyncClient]:
    """Initializes and returns Notion client if API key is available."""
    if config.NOTION_API_KEY:
        return NotionAsyncClient(auth=config.NOTION_API_KEY)
    logger.error("Notion API Key not configured in .env file.")
    return None

# --- Reference ID Generator ---
def generate_ref(prefix: str) -> str:
    """Generate a short reference ID for cross-database correlation."""
    # Truncate prefix safely
    safe_prefix = prefix[:15].replace(" ", "_") # Limit length and avoid spaces
    return safe_prefix + "-" + datetime.now().strftime('%H%M%S%f')[:9] # Added microseconds for more uniqueness

# -------------------------------------------------------------------
# 1. Tasks & Travel Functions (Using Task DB)
# -------------------------------------------------------------------

async def add_notion_task(task_name: str, due_date: Optional[str] = None, status: str = "To Do", auto_create_checklist: bool = True) -> str:
    """Adds a task to the Notion Task Database."""
    notion = _get_notion_client()
    if not notion or not config.NOTION_TASK_DB_ID:
        return "Notion client or Task DB ID not configured. Check .env file."
    if not task_name:
        logger.warning("Task name is empty.")
        return "Task name cannot be empty."

    logger.info(f"Adding task: '{task_name}', Due: '{due_date}', Status: '{status}'")
    try:
        ref_id = generate_ref(task_name)
        properties = {
            "Name": {"title": [{"text": {"content": task_name}}]},
            # Ensure 'Status' property matches your DB schema (Select or Status type)
            # If your Status property is of type "Status", use this:
            # "Status": {"status": {"name": status}},
            # If your Status property is of type "Select", use this:
            "Status": {"select": {"name": status}},
            "Reference ID": {"rich_text": [{"text": {"content": ref_id}}]}
        }
        if due_date:
            try:
                datetime.strptime(due_date, "%Y-%m-%d")
                # Ensure 'Due Date' property exists (Date type)
                properties["Due Date"] = {"date": {"start": due_date}}
                logger.debug(f"Validated due date: {due_date}")
            except ValueError:
                logger.warning(f"Invalid due date format: {due_date}")
                return "Invalid due date format. Use YYYY-MM-DD."

        response = await notion.pages.create(
            parent={"database_id": config.NOTION_TASK_DB_ID},
            properties=properties
        )
        task_page_id = response["id"]
        page_url = response.get("url", "N/A") # Get URL if available
        logger.info(f"Task added successfully. Page ID: {task_page_id}, URL: {page_url}")

        # Auto-create checklist item if configured
        if due_date and auto_create_checklist and config.NOTION_DAILY_CHECKLIST_DB_ID:
            checklist_result = await add_daily_checklist_item(due_date, f"Task Due: {task_name}")
            logger.info(f"Auto-created daily checklist item result: {checklist_result}")

        return f"Task '{task_name}' added to Notion. URL: {page_url}"
    except Exception as e:
        logger.error(f"Error adding task: {e}", exc_info=True)
        return f"Failed to add task to Notion: {str(e)}"

async def update_task_status(page_id: str, new_status: str) -> str:
    """Updates the status of a specific task page."""
    notion = _get_notion_client()
    if not notion:
        return "Notion client not configured."
    # Add check for TASK_DB_ID? Although page_id is universal, this tool conceptually belongs to tasks
    if not config.NOTION_TASK_DB_ID:
         return "Notion Task DB ID not configured. Cannot update status."

    logger.info(f"Updating task {page_id} to '{new_status}'")
    try:
        # Ensure 'Status' property matches your DB schema (Select or Status type)
        # If your Status property is of type "Status", use this:
        # properties = {"Status": {"status": {"name": new_status}}}
        # If your Status property is of type "Select", use this:
        properties = {"Status": {"select": {"name": new_status}}}
        await notion.pages.update(page_id=page_id, properties=properties)
        return f"Task ({page_id}) status updated to '{new_status}'."
    except Exception as e:
        logger.error(f"Error updating status for {page_id}: {e}", exc_info=True)
        return f"Failed to update status: {str(e)}"

async def delete_task(page_id: str) -> str:
    """Archives (deletes) a specific task page."""
    notion = _get_notion_client()
    if not notion:
        return "Notion client not configured."
    # Add check for TASK_DB_ID? Although page_id is universal, this tool conceptually belongs to tasks
    if not config.NOTION_TASK_DB_ID:
         return "Notion Task DB ID not configured. Cannot delete task."

    logger.info(f"Archiving task {page_id}")
    try:
        await notion.pages.update(page_id=page_id, archived=True)
        return f"Task {page_id} archived successfully."
    except Exception as e:
        logger.error(f"Error deleting task {page_id}: {e}", exc_info=True)
        return f"Failed to delete task: {str(e)}"

# -------------------------------------------------------------------
# 2. Travel Plan Functionality (Using Task DB with Type=Travel)
# -------------------------------------------------------------------

async def create_travel_plan(
    destination: str,
    start_date: str,
    end_date: str,
    plan_title: Optional[str] = None,
    checklist: Optional[List[str]] = None,
    notes: Optional[str] = None,
    auto_create_daily: bool = True
) -> str:
    """Creates a travel plan entry in the Task Database."""
    notion = _get_notion_client()
    if not notion or not config.NOTION_TASK_DB_ID:
         return "Notion client or Task DB ID not configured."

    plan_title = plan_title or f"Travel Plan: {destination}"
    logger.info(f"Creating travel plan: '{plan_title}' for {destination} from {start_date} to {end_date}")
    try:
        # Validate dates
        start_dt_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_dt_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
        if end_dt_obj < start_dt_obj:
             return "End date cannot be before start date."

        ref_id = generate_ref(plan_title)
        properties = {
            "Name": {"title": [{"text": {"content": plan_title}}]},
            # Ensure 'Type' property exists in your Task DB (Select type)
            "Type": {"select": {"name": "Travel"}},
            # Ensure 'Destination' property exists (Rich Text type)
            "Destination": {"rich_text": [{"text": {"content": destination}}]},
            # Ensure 'Start Date' property exists (Date type)
            "Start Date": {"date": {"start": start_date}},
            # Ensure 'End Date' property exists (Date type)
            "End Date": {"date": {"start": end_date}},
            "Reference ID": {"rich_text": [{"text": {"content": ref_id}}]}
        }
        # Ensure 'Notes' property exists if used (Rich Text type)
        if notes:
            properties["Notes"] = {"rich_text": [{"text": {"content": notes}}]}

        response = await notion.pages.create(
            parent={"database_id": config.NOTION_TASK_DB_ID},
            properties=properties
        )
        travel_page_id = response["id"]
        page_url = response.get("url", "N/A")
        logger.info(f"Travel plan created with page ID: {travel_page_id}, URL: {page_url}")

        # Add checklist items as blocks if provided
        if checklist and isinstance(checklist, list):
            blocks = []
            for item in checklist:
                block = {
                    "object": "block",
                    "type": "to_do",
                    "to_do": {
                        "rich_text": [{"type": "text", "text": {"content": item}}],
                        "checked": False
                    }
                }
                blocks.append(block)
            # Append blocks in chunks of 100 (Notion API limit)
            for i in range(0, len(blocks), 100):
                 chunk = blocks[i:i+100]
                 await notion.blocks.children.append(block_id=travel_page_id, children=chunk)
            logger.info(f"Checklist blocks added to travel plan page {travel_page_id}.")

        # Auto-create daily checklist items if configured
        if auto_create_daily and config.NOTION_DAILY_CHECKLIST_DB_ID:
            current_date = start_dt_obj
            while current_date <= end_dt_obj:
                daily_item = f"Travel: {plan_title} - Day {(current_date - start_dt_obj).days + 1}"
                result = await add_daily_checklist_item(current_date.isoformat(), daily_item)
                logger.debug(f"Auto-created daily checklist item for {current_date}: {result}")
                current_date += timedelta(days=1)

        return f"Travel plan for {destination} created. URL: {page_url}"
    except ValueError as ve:
        logger.warning(f"Invalid date format: {ve}")
        return "Invalid date format. Use YYYY-MM-DD."
    except Exception as e:
        logger.error(f"Error creating travel plan: {e}", exc_info=True)
        return f"Failed to create travel plan: {str(e)}"

# -------------------------------------------------------------------
# 3. Daily Checklist Functions (Separate Database)
# -------------------------------------------------------------------

async def add_daily_checklist_item(date: str, item: str, completed: bool = False) -> str:
    """Adds an item to the Daily Checklist database for a specific date."""
    notion = _get_notion_client()
    if not notion or not config.NOTION_DAILY_CHECKLIST_DB_ID:
        return "Daily Checklist database not configured."

    logger.info(f"Adding daily checklist item: '{item}' for date {date}")
    try:
         # Validate date
        datetime.strptime(date, "%Y-%m-%d")

        ref_id = generate_ref(item)
        properties = {
            # Ensure 'Name' property exists (Title type)
            "Name": {"title": [{"text": {"content": item}}]},
            # Ensure 'Date' property exists (Date type)
            "Date": {"date": {"start": date}},
            # Ensure 'Completed' property exists (Checkbox type)
            "Completed": {"checkbox": completed},
            "Reference ID": {"rich_text": [{"text": {"content": ref_id}}]}
        }
        response = await notion.pages.create(
            parent={"database_id": config.NOTION_DAILY_CHECKLIST_DB_ID},
            properties=properties
        )
        page_url = response.get("url", "N/A")
        logger.info(f"Daily checklist item added. Page ID: {response['id']}, URL: {page_url}")
        return f"Checklist item '{item}' added for {date}. URL: {page_url}"
    except ValueError:
         logger.warning(f"Invalid date format for daily checklist item: {date}")
         return "Invalid date format for daily checklist item. Use YYYY-MM-DD."
    except Exception as e:
        logger.error(f"Error adding daily checklist item: {e}", exc_info=True)
        return f"Failed to add checklist item: {str(e)}"

# -------------------------------------------------------------------
# 4. Expense Tracker Functions (Separate Database)
# -------------------------------------------------------------------

async def add_daily_expense(
    expense_date: str,
    amount: float,
    category: str,
    payment_method: str,
    vendor: Optional[str] = None,
    notes: Optional[str] = None
) -> str:
    """Adds an expense entry to the Expense Tracker database."""
    notion = _get_notion_client()
    if not notion or not config.NOTION_EXPENSE_DB_ID:
        return "Expense Tracker database not configured."

    logger.info(f"Adding expense: {amount} on {expense_date}, Category: {category}")
    try:
         # Validate date
        datetime.strptime(expense_date, "%Y-%m-%d")
        if not isinstance(amount, (int, float)) or amount <= 0:
             return "Invalid amount. Must be a positive number."

        ref_id = "EXP-" + datetime.now().strftime('%y%m%d%H%M%S') # Shortened ref
        properties = {
            # Ensure 'Expense Date' property exists (Date type)
            "Expense Date": {"date": {"start": expense_date}},
            # Ensure 'Amount' property exists (Number type)
            "Amount": {"number": amount},
            # Ensure 'Category' property exists (Select type)
            "Category": {"select": {"name": category}},
            # Ensure 'Payment Method' property exists (Select type)
            "Payment Method": {"select": {"name": payment_method}},
            "Reference ID": {"rich_text": [{"text": {"content": ref_id}}]}
        }
        # Ensure 'Vendor' property exists if used (Rich Text type)
        if vendor:
            properties["Vendor"] = {"rich_text": [{"text": {"content": vendor}}]}
        # Ensure 'Notes' property exists if used (Rich Text type)
        if notes:
            properties["Notes"] = {"rich_text": [{"text": {"content": notes}}]}

        response = await notion.pages.create(
            parent={"database_id": config.NOTION_EXPENSE_DB_ID},
            properties=properties
        )
        page_url = response.get("url", "N/A")
        logger.info(f"Expense added. Page ID: {response['id']}, URL: {page_url}")
        return f"Expense of {amount} added on {expense_date}. URL: {page_url}"
    except ValueError as ve:
         logger.warning(f"Invalid date format for expense: {expense_date} or invalid amount {amount}")
         return "Invalid date format (YYYY-MM-DD) or amount for expense."
    except Exception as e:
        logger.error(f"Error adding expense: {e}", exc_info=True)
        return f"Failed to add expense: {str(e)}"

# -------------------------------------------------------------------
# 5. Update Page Notes Function (Generic)
# -------------------------------------------------------------------

async def update_page_notes(page_id: str, note: str, append: bool = True) -> str:
    """Appends or overwrites the 'Notes' property of a specific Notion page."""
    notion = _get_notion_client()
    if not notion:
        return "Notion client not configured."
    logger.info(f"Updating notes for page {page_id}; append = {append}")
    try:
        # We assume a 'Notes' property exists and is of type 'rich_text'
        # The function doesn't know which database it belongs to, relies on page_id validity
        properties_update = {"Notes": {"rich_text": [{"text": {"content": note}}]}}

        if append:
             # Retrieve existing notes first
             try:
                 page = await notion.pages.retrieve(page_id=page_id)
                 existing_notes = ""
                 # Check if 'Notes' property exists and has content
                 if "Notes" in page.get("properties", {}) and page["properties"]["Notes"].get("rich_text"):
                     # Concatenate plain text from all rich text objects
                     existing_notes = "".join([text.get("plain_text", "") for text in page["properties"]["Notes"]["rich_text"]])

                 if existing_notes:
                     new_notes = existing_notes.strip() + "\n---\n" + note # Add separator
                     properties_update["Notes"]["rich_text"] = [{"text": {"content": new_notes}}]
                 else:
                      # If no existing notes, just use the new note (overwrite behavior)
                      properties_update["Notes"]["rich_text"] = [{"text": {"content": note}}]


             except Exception as retrieve_error:
                 logger.warning(f"Could not retrieve existing notes for page {page_id} to append: {retrieve_error}. Overwriting instead.")
                 # Fallback to overwriting if retrieval fails - properties_update already holds the overwrite value

        await notion.pages.update(
            page_id=page_id,
            properties=properties_update
        )
        return f"Notes for page {page_id} updated."
    except Exception as e:
        logger.error(f"Error updating notes for {page_id}: {e}", exc_info=True)
        # Provide more specific error if possible (e.g., property mismatch)
        error_message = str(e)
        if "property does not exist" in error_message.lower() or "schema mismatch" in error_message.lower():
             return f"Failed to update notes: Ensure page {page_id} has a 'Notes' property of type Rich Text. Error: {error_message}"
        return f"Failed to update notes for page {page_id}: {error_message}"

# Note: The function `update_task_notes` was renamed to `update_page_notes`
# as it can technically update notes on any page, although intended for tasks/travel plans.
# If you specifically need it only for the Task DB, add a check for config.NOTION_TASK_DB_ID
# and potentially retrieve the page first to verify its parent database.