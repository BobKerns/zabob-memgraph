#!/usr/bin/env python3
"""
Static web content server for knowledge graph visualization.

Minimal FastAPI server focused solely on serving static web assets.
Sibling to mcp_service.py - handles web content while MCP service handles data.
"""

import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn


app = FastAPI(
    title="Knowledge Graph Web Service",
    description="Static content server for knowledge graph visualization",
    version="1.0.0"
)


def setup_static_routes(static_dir: str = "web"):
    """
    Configure static file serving.
    
    Args:
        static_dir: Directory containing static web assets (default: "web")
    """
    static_path = Path(static_dir)
    
    if not static_path.exists():
        raise FileNotFoundError(f"Static directory not found: {static_path}")
    
    # Mount static files directory
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    
    # Serve index.html at root
    @app.get("/")
    async def serve_index():
        index_path = static_path / "index.html"
        if not index_path.exists():
            raise HTTPException(status_code=404, detail="index.html not found")
        return FileResponse(index_path)
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "web_service"}


def create_app(static_dir: str = "web") -> FastAPI:
    """
    Create configured FastAPI application.
    
    Args:
        static_dir: Directory containing static web assets
        
    Returns:
        Configured FastAPI application
    """
    setup_static_routes(static_dir)
    return app


def main(
    host: str = "localhost", 
    port: int = 8080, 
    static_dir: str = "web",
    reload: bool = False
):
    """
    Run the web service.
    
    Args:
        host: Host to bind to (default: localhost)
        port: Port to listen on (default: 8080)
        static_dir: Directory containing static web assets (default: "web")
        reload: Enable auto-reload for development (default: False)
    """
    try:
        setup_static_routes(static_dir)
        uvicorn.run(
            "web_service:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info"
        )
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print(f"Please ensure the '{static_dir}' directory exists and contains web assets.")
        return 1
    except Exception as e:
        print(f"Failed to start web service: {e}")
        return 1


if __name__ == "__main__":
    import click
    
    @click.command()
    @click.option("--host", default="localhost", help="Host to bind to")
    @click.option("--port", type=int, default=8080, help="Port to listen on")
    @click.option("--static-dir", default="web", help="Static files directory")
    @click.option("--reload", is_flag=True, help="Enable auto-reload")
    def cli(host: str, port: int, static_dir: str, reload: bool):
        """Knowledge Graph Web Service - Static content server."""
        exit_code = main(
            host=host,
            port=port,
            static_dir=static_dir,
            reload=reload
        )
        
        if exit_code:
            exit(exit_code)
    
    cli()
