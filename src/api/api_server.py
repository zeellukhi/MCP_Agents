# MCP_Agents/src/api/api_server.py
"""
API Server Module

Defines the main Starlette application that serves the user interface (built React app)
and handles API requests (e.g., '/api/chat'). It initializes the language model,
connects to the MCP server to get available tools, runs the LangChain agent,
and returns the agent's response.
"""

import logging
import asyncio
import sys
from typing import Dict, Any
from pathlib import Path # Import Path

# Starlette imports
from starlette.applications import Starlette
from starlette.responses import JSONResponse, FileResponse, Response
from starlette.routing import Route, Mount # Import Mount
from starlette.requests import Request
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException
from starlette.staticfiles import StaticFiles # Import StaticFiles

# LangChain and MCP imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langchain_mcp_tools.langchain_mcp_tools import convert_mcp_to_langchain_tools

# Internal imports
from src.common.config import config, PROJECT_ROOT_PATH # Use centralized config

logger = logging.getLogger(__name__)

# --- Global Initializations ---

# Initialize Language Model (LLM)
llm = None
if config and config.GOOGLE_API_KEY:
    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-pro", # Or your desired Gemini model
            google_api_key=config.GOOGLE_API_KEY,
            temperature=0.2, # Adjust temperature as needed
            max_retries=2,
        )
        logger.info(f"Initialized ChatGoogleGenerativeAI with model: {llm}")
    except Exception as e:
        logger.error(f"Failed to initialize Google LLM: {e}", exc_info=True)
else:
    logger.error("GOOGLE_API_KEY not found. LLM initialization skipped.")


# Define path to the frontend build output directory
# Assumes your React app builds to 'frontend/dist' relative to the project root
FRONTEND_BUILD_DIR = PROJECT_ROOT_PATH / "frontend" / "dist"
FRONTEND_INDEX_FILE = FRONTEND_BUILD_DIR / "index.html"
# Vite usually puts built assets (JS, CSS) in an 'assets' subfolder within 'dist'
# Adjust this path if your build tool uses a different structure
FRONTEND_ASSETS_DIR = FRONTEND_BUILD_DIR / "assets"

# --- API Endpoint Functions ---

async def chat_endpoint(request: Request) -> JSONResponse:
    """
    Handles POST requests to /api/chat for processing user queries.

    Connects to the MCP server, retrieves tools, runs the agent,
    and returns the final response.

    Input (JSON Body):
        {"query": "User's message text"}

    Output (JSON Response):
        On Success: {"response": "Agent's final answer"}
        On Error:   {"error": "Description of the error"}
    """
    logger.debug("Received request on /api/chat")
    if not llm:
         logger.error("Cannot process chat request: LLM not initialized.")
         return JSONResponse({"error": "LLM not configured or failed to initialize."}, status_code=503) # Service Unavailable

    try:
        data = await request.json()
        query = data.get("query")
        if not query or not isinstance(query, str) or not query.strip():
            logger.warning("Chat request received with missing or empty query.")
            return JSONResponse({"error": "Query parameter is missing or empty."}, status_code=400) # Bad Request
        logger.info(f"Processing query: '{query}'")

    except Exception as e:
        logger.warning(f"Failed to parse request JSON: {e}", exc_info=True)
        return JSONResponse({"error": "Invalid request body. Expected JSON."}, status_code=400)

    # --- MCP Tool Loading ---
    tools = []
    cleanup_func = None
    # Use host/port from config for MCP server URL
    mcp_server_url = f"http://{config.MCP_HOST}:{config.MCP_PORT}/sse"
    mcp_servers_config = {
        "personal_assistant": { # Matches the server_id in mcp_server.py
            "url": mcp_server_url
        }
    }

    try:
        logger.info(f"Connecting to MCP server at {mcp_server_url} to load tools...")
        tools, cleanup_func = await convert_mcp_to_langchain_tools(mcp_servers_config)

        if not tools:
            logger.warning("No tools were loaded from the MCP server.")
        else:
             logger.info(f"Successfully loaded {len(tools)} tools from MCP.")
             for tool in tools:
                  logger.debug(f"  - Loaded tool: {tool.name} - {tool.description}")

    except Exception as e:
        logger.error(f"Failed to connect to or load tools from MCP server at {mcp_server_url}: {e}", exc_info=True)
        # Clean up if connection failed partway through potentially
        if cleanup_func:
            try:
                await cleanup_func()
            except Exception as ce:
                 logger.warning(f"Error during cleanup after connection failure: {ce}")
        return JSONResponse({"error": f"Could not load tools from MCP server: {e}"}, status_code=503) # Service Unavailable

    # --- Agent Execution ---
    try:
        logger.info("Creating and invoking agent...")
        agent_executor = create_react_agent(llm, tools if tools else [])
        # Use the message format expected by the agent
        agent_input = {"messages": [("user", query)]}

        response = await agent_executor.ainvoke(agent_input)

        # Extract the final answer - adjust structure based on agent output if needed
        final_message = "Could not determine final answer."
        if isinstance(response, dict):
             if "output" in response:
                  final_message = response["output"]
             elif "messages" in response and isinstance(response["messages"], list) and response["messages"]:
                  last_msg = response["messages"][-1]
                  if hasattr(last_msg, 'content'):
                       final_message = last_msg.content
                  else:
                       final_message = str(last_msg)
             else:
                  final_message = str(response)
        elif isinstance(response, str):
             final_message = response

        logger.info("Agent invocation successful.")
        logger.debug(f"Agent final response: '{final_message}'")
        return JSONResponse({"response": final_message})

    except Exception as e:
        logger.error(f"Agent execution failed: {e}", exc_info=True)
        return JSONResponse({"error": f"Agent processing failed: {e}"}, status_code=500) # Internal Server Error

    finally:
        # --- Cleanup MCP Connection ---
        if cleanup_func:
            try:
                await cleanup_func()
                logger.info("MCP tool connection cleaned up.")
            except Exception as e:
                logger.warning(f"Error during MCP cleanup: {e}", exc_info=True)

async def serve_frontend_app(request: Request) -> Response:
    """
    Serves the built frontend's index.html for the root path and any other path
    not explicitly handled by other routes (supports client-side routing).
    """
    logger.debug(f"Attempting to serve frontend index: {FRONTEND_INDEX_FILE}")
    if not FRONTEND_INDEX_FILE.is_file():
        logger.error(f"Frontend index.html not found at {FRONTEND_INDEX_FILE}. "
                     "Did you run 'npm run build' in the frontend directory?")
        # Return a simple 404 page if the main index isn't found
        return Response("Frontend build not found. Run 'npm run build' in the /frontend directory.",
                        status_code=404, media_type="text/plain")
    try:
        return FileResponse(str(FRONTEND_INDEX_FILE))
    except Exception as e:
        logger.error(f"Error serving frontend index file: {e}", exc_info=True)
        # Return a generic 500 error
        return Response("Internal server error serving frontend.",
                        status_code=500, media_type="text/plain")


# --- Starlette Application Setup ---
# Define middleware (e.g., CORS)
middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"], # Allow all origins for simplicity, restrict in production
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"], # Allow necessary methods including OPTIONS for preflight
        allow_headers=["*"],
    )
]

# Define application routes
routes = [
    Route("/api/chat", endpoint=chat_endpoint, methods=["POST"]),

    # Serve static assets (JS, CSS) from the build output's assets directory
    # Requests to /assets/... will serve files from frontend/dist/assets/...
    # Check if the assets directory exists before mounting
    Mount("/assets", app=StaticFiles(directory=FRONTEND_ASSETS_DIR, check_dir=True), name="static-assets"),

    # Serve the main index.html for the root path AND any other path not matched above
    # This MUST be the LAST route to catch all non-API/asset paths for client-side routing
    Route("/{path:path}", endpoint=serve_frontend_app, methods=["GET"]),
]

# Create the main Starlette application instance
app = Starlette(
    debug=config.DEBUG_MODE if config else False,
    routes=routes,
    middleware=middleware,
    # Optional: Add exception handlers for better error pages if needed
    # exception_handlers={ ... }
)

logger.info(f"API server Starlette application created (debug={app.debug}).")
logger.info(f"API at '/api/chat', Frontend served from '{FRONTEND_BUILD_DIR}'.")

# Note: The actual running of this app happens in main.py using uvicorn.