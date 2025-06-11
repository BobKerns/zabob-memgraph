#!/usr/bin/env uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "aiofiles",
#     "fastapi",
#     "jinja2",
#     "mcp",
#     "pydantic",
#     "uvicorn[standard]",
# ]
# ///
"""
Main entry point for the Knowledge Graph MCP Server
"""

import sys
from pathlib import Path

# Add the package to the path
sys.path.insert(0, str(Path(__file__).parent))

from memgraph.server import run_server

if __name__ == "__main__":
    run_server()
