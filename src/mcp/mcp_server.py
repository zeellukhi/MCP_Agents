# MCP_Agents/src/mcp/mcp_server.py
"""
MCP Server Module

Sets up the FastMCP server instance, registers tool functions from the 'tools'
package, and creates a Starlette application to serve the tools via
Server-Sent Events (SSE) transport.
"""

import logging
import asyncio
from typing import Any, Callable

# MCP related imports - Ensure 'mcp' package (version 1.6.0 based on search) is installed
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport

# Starlette imports for creating the web application framework
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.requests import Request # Import Request
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

# Import the actual tool functions to be exposed
# Import specific functions you want to expose
from src.tools.notion_tool import (
    add_notion_task,
    add_daily_checklist_item,
    add_daily_expense,
    update_task_status,
    # delete_task, # Uncomment if implemented and needed
    # create_travel_plan, # Uncomment if implemented and needed
    # update_task_notes # Uncomment if implemented and needed
)
from src.tools.google_calendar_tool import (
    add_google_calendar_event
    # Add other Google Calendar functions here if any
)
from src.common.config import config # Use centralized config

logger = logging.getLogger(__name__)

# --- MCP Instance Setup ---
# Create the main MCP server instance. The name ("personal_assistant")
# is used by the API server to identify this set of tools.
try:
    # Ensure necessary config for tools exists before trying to register
    if not config:
        raise ValueError("Configuration not loaded. Cannot proceed.")
    if not config.NOTION_API_KEY or not config.NOTION_TASK_DB_ID:
         logger.warning("Notion API Key or Task DB ID missing in config. Notion tools may fail.")
    if not config.GOOGLE_CLIENT_SECRET_FILE:
        logger.warning("Google Client Secret File missing in config. Google Calendar tool may fail.")

    mcp = FastMCP(server_id="personal_assistant")
    logger.info(f"MCP Server instance created with server_id: '{mcp}'")

    # --- Tool Registration ---
    # Decorate each function imported from the tools modules that you want
    # the agent to be able to call.
    registered_tools_count = 0

    # Notion Tools (Register only if config seems plausible)
    if config.NOTION_API_KEY and config.NOTION_TASK_DB_ID:
        mcp.tool()(add_notion_task)
        logger.info("  - Registered tool: add_notion_task")
        registered_tools_count += 1
        if config.NOTION_DAILY_CHECKLIST_DB_ID:
            mcp.tool()(add_daily_checklist_item)
            logger.info("  - Registered tool: add_daily_checklist_item")
            registered_tools_count += 1
        if config.NOTION_EXPENSE_DB_ID:
            mcp.tool()(add_daily_expense)
            logger.info("  - Registered tool: add_daily_expense")
            registered_tools_count += 1
        mcp.tool()(update_task_status) # Assuming this doesn't strictly need a specific DB ID
        logger.info("  - Registered tool: update_task_status")
        registered_tools_count += 1
        # mcp.tool()(delete_task) # Uncomment/add if implemented
        # mcp.tool()(create_travel_plan) # Uncomment/add if implemented
        # mcp.tool()(update_task_notes) # Uncomment/add if implemented

    # Google Calendar Tools (Register only if config seems plausible)
    if config.GOOGLE_CLIENT_SECRET_FILE:
        mcp.tool()(add_google_calendar_event)
        logger.info("  - Registered tool: add_google_calendar_event")
        registered_tools_count += 1

    logger.info(f"Successfully registered {registered_tools_count} tools with MCP.")

    # REMOVED the problematic logging loop that caused the TypeError:
    # for tool_name in mcp.list_tools(): ...

except Exception as e:
     logger.critical(f"Fatal error during MCP instance creation or tool registration: {e}", exc_info=True)
     # Optionally re-raise or exit if this setup is critical
     raise


# --- Starlette Application Factory ---

def create_starlette_app(mcp_server_obj: Any, debug: bool = False) -> Starlette:
    """
    Creates a Starlette application configured to serve the MCP tools via SSE.

    Args:
        mcp_server_obj: The internal server object from the FastMCP instance
                        (typically accessed via mcp._mcp_server).
        debug (bool): Whether to run Starlette in debug mode.

    Returns:
        Starlette: The configured Starlette application instance.
    """
    logger.info(f"Creating Starlette app for MCP server (debug={debug})")

    # Setup SSE transport which handles communication
    # Correctly pass the base path for message posting
    sse_transport = SseServerTransport("/messages/") # Match the Mount path below

    # **Define the SSE handler function correctly**
    async def handle_sse(request: Request):
        """Handles incoming SSE connection requests."""
        logger.debug(f"SSE connection request received from {request.client}")
        # Use the context manager from the transport to handle the connection
        async with sse_transport.connect_sse(
            request.scope,
            request.receive,
            request._send, # Use internal _send for streaming response
        ) as (read_stream, write_stream):
            logger.debug("SSE connection established. Running MCP server loop.")
            # Run the core MCP server logic for this connection
            await mcp_server_obj.run(
                read_stream,
                write_stream,
                mcp_server_obj.create_initialization_options(),
            )
        logger.debug("SSE connection closed.")

    # Define middleware (e.g., CORS)
    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=["*"], # Allow all origins for simplicity, restrict in production
            allow_credentials=True,
            allow_methods=["GET", "POST", "OPTIONS"], # Allow necessary methods
            allow_headers=["*"],
        )
    ]

    # Define routes
    # /sse: Use the locally defined handle_sse function
    # /messages/: Endpoint for receiving messages (used internally by SSE transport)
    routes = [
        Route("/sse", endpoint=handle_sse), # Use the defined handler
        Mount("/messages/", app=sse_transport.handle_post_message), # Mount the message handler
    ]

    # Create the Starlette app
    app = Starlette(debug=debug, routes=routes, middleware=middleware)
    logger.info("Starlette app for MCP created with SSE endpoint at /sse and message endpoint at /messages/")
    return app

# Note: The actual running of this app happens in main.py using uvicorn.