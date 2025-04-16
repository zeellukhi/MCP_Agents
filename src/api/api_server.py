# /src/api/api_server.py - REST API server code
# src/api/api_server.py
import os
import asyncio
from starlette.applications import Starlette
from starlette.responses import JSONResponse, FileResponse
from starlette.routing import Route
from starlette.requests import Request
from starlette.middleware.cors import CORSMiddleware
from src.common.config import config
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langchain_mcp_tools.langchain_mcp_tools import convert_mcp_to_langchain_tools

llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-pro",
    google_api_key=config.GOOGLE_API_KEY,
    temperature=0,
    max_retries=3
)

async def chat_endpoint(request: Request):
    try:
        data = await request.json()
        query = data.get("query")
        if not query:
            return JSONResponse({"error": "No query provided."}, status_code=400)

        mcp_servers = {
            "personal_assistant": {
                "url": "http://localhost:9091/sse"
            }
        }
        tools, cleanup = await convert_mcp_to_langchain_tools(mcp_servers)
        if not tools:
            return JSONResponse({"error": "No MCP tools available."}, status_code=500)

        agent = create_react_agent(llm, tools)
        response = await agent.ainvoke({"messages": query})
        messages = response.get("messages", [])
        final_message = messages[-1].content if messages and hasattr(messages[-1], "content") else str(response)
        
        await cleanup()
        return JSONResponse({"response": final_message})
    except Exception as e:
        return JSONResponse({"error": f"Server error: {str(e)}"}, status_code=500)

async def serve_frontend(request: Request):
    try:
        return FileResponse("src/ui/index.html")
    except Exception:
        return JSONResponse({"error": "Frontend file not found."}, status_code=404)

app = Starlette(
    debug=True,
    routes=[
        Route("/api/chat", chat_endpoint, methods=["POST"]),
        Route("/", serve_frontend)
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)
