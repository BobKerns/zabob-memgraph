"""
Knowledge Graph MCP HTTP Server

Provides HTTP endpoints for knowledge graph data while maintaining MCP compatibility.
Serves static web assets for D3.js visualization client.
"""

from .server import app, run_server

__version__ = "0.1.0"
__all__ = ["app", "run_server"]
