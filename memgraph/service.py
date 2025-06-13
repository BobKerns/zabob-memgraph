#!/usr/bin/env python3
"""
Unified ASGI service combining web and MCP functionality.

Mounts both web_service routes (static content) and mcp_service routes (MCP protocol)
on a single ASGI server for integrated operation.
"""

import logging
from pathlib import Path
from fastapi import FastAPI
import uvicorn
import click

# Import the individual service modules - handle both script and package contexts
try:
    from . import web_service
    from . import mcp_service
except ImportError:
    # Running as script, use absolute imports
    import web_service
    import mcp_service


def create_unified_app(static_dir: str = "web") -> FastAPI:
    """
    Create unified FastAPI application with both web and MCP routes.
    
    Args:
        static_dir: Directory containing static web assets
        
    Returns:
        Configured FastAPI application with both route collections
    """
    app = FastAPI(
        title="Knowledge Graph Unified Service",
        description="Combined web content and MCP protocol server",
        version="1.0.0"
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Creating unified service with static dir: {static_dir}")
    
    # Set up static routes directly on our app
    static_path = Path(static_dir)
    
    if not static_path.exists():
        raise FileNotFoundError(f"Static directory not found: {static_path}")
    
    # Mount static files directory
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse
    from fastapi import HTTPException
    
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    logger.info(f"Mounted /static to {static_dir}")
    
    # Add web service routes
    @app.get("/")
    async def serve_index():
        index_path = static_path / "index.html"
        if not index_path.exists():
            raise HTTPException(status_code=404, detail="index.html not found")
        return FileResponse(index_path)
    
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "unified_service"}
    
    # TODO: Add MCP service routes when mcp_service.py is expanded
    # For now, placeholder for MCP endpoints
    @app.get("/mcp/health")
    async def mcp_health():
        return {"status": "healthy", "service": "mcp_service"}
    
    return app


def main(
    host: str = "localhost",
    port: int = 8080,
    static_dir: str = "web", 
    log_file: str | None = None
):
    """
    Run the unified service.
    
    Args:
        host: Host to bind to (default: localhost)
        port: Port to listen on (default: 8080)
        static_dir: Directory containing static web assets (default: "web")
        log_file: Log file path (default: None, logs to stderr)
    """
    # Configure logging
    if log_file:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            filename=log_file
        )
    else:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    logger = logging.getLogger(__name__)
    
    try:
        app = create_unified_app(static_dir)
        logger.info(f"Starting unified service on {host}:{port}")
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info"
        )
    except Exception as e:
        logger.error(f"Failed to start unified service: {e}")
        return 1


if __name__ == "__main__":
    @click.command()
    @click.option("--host", default="localhost", help="Host to bind to")
    @click.option("--port", type=int, default=8080, help="Port to listen on")
    @click.option("--static-dir", default="web", help="Static files directory")
    @click.option("--log-file", help="Log file path (default: stderr)")
    def cli(host: str, port: int, static_dir: str, log_file: str | None):
        """Knowledge Graph Unified Service - Web + MCP on single port."""
        exit_code = main(
            host=host,
            port=port,
            static_dir=static_dir,
            log_file=log_file
        )
        
        if exit_code:
            exit(exit_code)
    
    cli()
