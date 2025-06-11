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
Main entry point for the Zabob Memgraph Knowledge Graph Server

This serves as both the standalone script entry point and the Docker container entrypoint.
"""

import os
import sys
from pathlib import Path

# Add the package to the path
sys.path.insert(0, str(Path(__file__).parent))

from memgraph.server import run_server


def main():
    """Main entry point with environment configuration support"""
    # Get configuration from environment variables (useful for Docker)
    host = os.getenv('MEMGRAPH_HOST', 'localhost')
    port = int(os.getenv('MEMGRAPH_PORT', '8080'))
    
    # For Docker, bind to all interfaces
    if os.getenv('DOCKER_CONTAINER') or host == '0.0.0.0':
        host = '0.0.0.0'
    
    print(f"Starting Zabob Memgraph server on {host}:{port}")
    run_server(host=host, port=port)


if __name__ == "__main__":
    main()
