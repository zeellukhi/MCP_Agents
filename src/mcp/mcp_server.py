# /src/mcp/mcp_server.py - MCP server code
# src/mcp/mcp_server.py
import os
import asyncio
import logging
from mcp.server.fastmcp import FastMCP
from src.tools.notion_tool import (
    add_notion_task,
    update_task_status,
    delete_task,
    create_travel_plan,
    add_daily_checklist_item,
    add_daily_expense,
    update_task_notes
)
from src.tools.google_calendar_tool import add_google_calendar_event
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.requests import Request
from starlette.responses import StreamingResponse, JSONResponse
from starlette.middleware.cors import CORSMiddleware
import uvicorn
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)

from dotenv import load_dotenv
load_dotenv()

mcp = FastMCP("personal_assistant")
mcp.tool()(add_notion_task)
mcp.tool()(update_task_status)
mcp.tool()(delete_task)
mcp.tool()(create_travel_plan)
mcp.tool()(add_daily_checklist_item)
mcp.tool()(add_daily_expense)
mcp.tool()(update_task_notes)
mcp.tool()(add_google_calendar_event)

def create_starlette_app(mcp_server, *, debug=False):
    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request):
        async with sse.connect_sse(
            request.scope,
            request.receive,
            request._send,
        ) as (read_stream, write_stream):
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options(),
            )

    async def chat_endpoint(request):
        data = await request.json()
        user_message = data.get("message", "")
        if not user_message:
            return JSONResponse({"error": "No message provided."}, status_code=400)

        GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-pro",
            temperature=0,
            max_retries=2,
            google_api_key=GOOGLE_API_KEY
        )
        server_script = os.path.abspath(__file__)
        server_params = StdioServerParameters(
            command="python",
            args=[server_script],
        )
        async def run_agent():
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = await load_mcp_tools(session)
                    agent = create_react_agent(llm, tools)
                    result = await agent.ainvoke({"input": user_message})
                    yield result["output"]
        return StreamingResponse(run_agent(), media_type="text/plain")

    app = Starlette(
        debug=debug,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
            Route("/chat", endpoint=chat_endpoint, methods=["POST"]),
        ],
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Run MCP SSE-based server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=9091, help='Port to listen on')
    args = parser.parse_args()
    starlette_app = create_starlette_app(mcp._mcp_server, debug=True)
    uvicorn.run(starlette_app, host=args.host, port=args.port)
