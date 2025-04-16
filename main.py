# MCP_Agents/main.py
"""
Main Application Entry Point

Initializes logging and configuration, then starts the API and MCP servers
concurrently using Uvicorn and Asyncio.
Allows configuration of hosts and ports via command-line arguments,
falling back to values defined in the .env file or defaults.
"""

import asyncio
import argparse
import logging
import sys
import uvicorn

# --- Early Initialization ---
# Attempt to load config and setup logging as the very first steps.
# This ensures logging is available immediately and config drives setup.
try:
    from src.common.config import config, ConfigError
    from src.common.logger_config import setup_logging

    # Setup logging based on the loaded configuration
    setup_logging()

    # Check if config loading failed earlier (logged in config.py)
    if config is None:
         # Log critical error again for visibility if setup_logging was called
         logging.critical("Configuration failed to load. Exiting.")
         sys.exit(1) # Exit if configuration is critically missing

except ImportError as e:
    # Handle cases where src modules aren't found (e.g., running from wrong directory)
    print(f"Import Error: {e}. Ensure you are running python from the MCP_Agents root directory "
          "and your PYTHONPATH is set correctly, or that 'src' is discoverable.", file=sys.stderr)
    sys.exit(1)
except ConfigError as e:
    # ConfigError should have been caught in config.py, but catch again as safety
    logging.critical(f"Configuration Error during startup: {e}")
    sys.exit(1)
except Exception as e:
    # Catch any other unexpected errors during initial setup
    logging.basicConfig(level=logging.CRITICAL) # Fallback basic config
    logging.critical(f"Unexpected error during initialization: {e}", exc_info=True)
    sys.exit(1)

# --- Import Server Components (after config/logging setup) ---
try:
    from src.api.api_server import app as api_app
    # Note: Adjust the import below based on your actual MCP server setup
    # This assumes mcp_server.py defines 'create_starlette_app' and an 'mcp' object instance
    from src.mcp.mcp_server import create_starlette_app, mcp
except ImportError as e:
    logging.critical(f"Failed to import server components: {e}. Check src/api/ and src/mcp/ files.", exc_info=True)
    sys.exit(1)
except AttributeError as e:
     logging.critical(f"Attribute error importing server components: {e}. Ensure mcp_server.py defines required elements.", exc_info=True)
     sys.exit(1)


# --- Main Application Logic ---

logger = logging.getLogger(__name__) # Get logger for main module

def build_servers(api_host: str, api_port: int, mcp_host: str, mcp_port: int) -> tuple[uvicorn.Server, uvicorn.Server]:
    """
    Configures and creates Uvicorn server instances for API and MCP apps.

    Args:
        api_host (str): Host address for the API server.
        api_port (int): Port number for the API server.
        mcp_host (str): Host address for the MCP server.
        mcp_port (int): Port number for the MCP server.

    Returns:
        tuple[uvicorn.Server, uvicorn.Server]: A tuple containing the
            configured API server and MCP server instances.

    Raises:
        AttributeError: If the 'mcp' object from mcp_server doesn't have
                        the expected '_mcp_server' attribute.
        Exception: For other errors during Starlette app creation for MCP.
    """
    try:
        # Configure API Server
        # Pass log_config=None to use the global logging setup
        api_config = uvicorn.Config(
            api_app,
            host=api_host,
            port=api_port,
            log_config=None, # Important: Use our logger config
            access_log=config.DEBUG_MODE # Enable access log only in debug mode
        )
        api_server = uvicorn.Server(api_config)
        logger.info(f"API server configured for {api_host}:{api_port}")

        # Configure MCP Server
        # Assumes create_starlette_app takes the internal MCP server object
        # Ensure mcp._mcp_server exists and is the correct object
        if not hasattr(mcp, '_mcp_server'):
             raise AttributeError("Imported 'mcp' object does not have '_mcp_server' attribute needed for Starlette app.")

        mcp_starlette_app = create_starlette_app(mcp._mcp_server, debug=config.DEBUG_MODE)
        mcp_config = uvicorn.Config(
            mcp_starlette_app,
            host=mcp_host,
            port=mcp_port,
            log_config=None, # Important: Use our logger config
            access_log=config.DEBUG_MODE # Enable access log only in debug mode
        )
        mcp_server = uvicorn.Server(mcp_config)
        logger.info(f"MCP server configured for {mcp_host}:{mcp_port}")

        return api_server, mcp_server

    except AttributeError as ae:
         logger.critical(f"Configuration Error: {ae}", exc_info=True)
         raise # Re-raise to be caught by main exception handler
    except Exception as e:
        logger.critical(f"Failed to build MCP Starlette app: {e}", exc_info=True)
        raise # Re-raise


async def run_servers() -> None:
    """
    Parses command-line arguments and runs the API and MCP servers concurrently.
    """
    parser = argparse.ArgumentParser(
        description="Run MCP Agents API and MCP servers concurrently.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter # Show defaults in help
    )

    # Arguments with defaults pulled from config (which loaded from .env or defaults)
    parser.add_argument('--api-host', default=config.API_HOST,
                        help="Host for the API server.")
    parser.add_argument('--api-port', type=int, default=config.API_PORT,
                        help="Port for the API server.")
    parser.add_argument('--mcp-host', default=config.MCP_HOST,
                        help="Host for the MCP server.")
    parser.add_argument('--mcp-port', type=int, default=config.MCP_PORT,
                        help="Port for the MCP server.")

    args = parser.parse_args()

    logger.info("Building servers...")
    try:
        api_server, mcp_server = build_servers(
            api_host=args.api_host,
            api_port=args.api_port,
            mcp_host=args.mcp_host,
            mcp_port=args.mcp_port
        )
    except Exception:
         # Error already logged in build_servers
         logger.critical("Server building failed. Exiting.")
         return # Exit async function

    # Run both servers concurrently using asyncio.gather
    logger.info("Starting servers...")
    try:
        await asyncio.gather(
            api_server.serve(),
            mcp_server.serve()
        )
    except (KeyboardInterrupt, SystemExit):
        logger.info("Received stop signal. Shutting down servers...")
    except Exception as e:
        # Catch unexpected errors during server runtime
        logger.critical("Servers failed during runtime", exc_info=True)
    finally:
        # Perform any cleanup if needed (servers should handle their own shutdown)
        logger.info("Servers have shut down.")


if __name__ == "__main__":
    # Run the main asynchronous function
    asyncio.run(run_servers())