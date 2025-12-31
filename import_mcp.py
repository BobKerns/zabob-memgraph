#!/usr/bin/env uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "aiofiles",
#     "fastmcp",
#     "jinja2",
#     "mcp",
#     "pydantic",
#     "uvicorn[standard]",
# ]
# ///
# flake8: noqa E402
"""
MCP to SQLite Import Utility

This script imports knowledge graph data from MCP tools into SQLite database.
Can be run standalone or called from the HTTP server.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import cast

import httpx

# Add the package to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

# my_client.py
from fastmcp import Client
from mcp.types import TextContent
from fastmcp.client.transports import StdioTransport
from shutil import which


async def import_from_memory_mcp() :
    docker = which("docker")
    if not docker:
        raise RuntimeError("Docker is not installed or not found in PATH. Please install Docker to run this script.")

    """Read data from memory MCP container"""
    transport = StdioTransport(
        command=docker,
        args=[
            "run",  # "--rm",
            "-i",
            "-v", "claude-memory:/app/data",
            "mcp/memory",
        ])

    async with Client(transport) as client:

        print("Listing tools...")
        tools = await client.list_tools()
        print(f"Available tools: {[tool.name for tool in tools]}")
        response = await client.call_tool("read_graph",
                                          {
                                           "graph_name": "claude-memory"})
        response = cast(list[TextContent], response)
        print(f"Read {[d.text for d in response]!r} items from memory MCP")
        return json.loads(response[0].text)


async def send_to_server(graph_data: dict, server_url: str = "http://localhost:8080"):
    """Send data to zabob-memgraph server"""
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{server_url}/api/import-mcp", json=graph_data)
        return response.json()


# Put it together
async def main():
    graph_data = await import_from_memory_mcp()
    result = await send_to_server(graph_data)
    print(f"Import result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
