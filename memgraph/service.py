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
from contextlib import asynccontextmanager

# Use absolute imports
import memgraph.web_service as web_service
import memgraph.mcp_service as mcp_service
from memgraph.service_logging import (
    service_setup_context,
    service_async_context,
    log_app_creation,
    log_route_mounting,
    log_server_start,
    configure_uvicorn_logging
)


def create_unified_app(static_dir: str = "web", service_logger=None) -> FastAPI:
    """
    Create unified FastAPI application with both web and MCP routes.

    Args:
        static_dir: Directory containing static web assets
        service_logger: Logger instance for tracking app creation

    Returns:
        Configured FastAPI application with both route collections
    """
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with service_async_context(service_logger):
            yield

    app = FastAPI(
        title="Knowledge Graph Unified Service",
        description="Combined web content and MCP protocol server",
        version="1.0.0",
        lifespan=lifespan
    )

    if service_logger:
        log_app_creation(service_logger, "unified", {
            "static_dir": static_dir,
            "title": "Knowledge Graph Unified Service"
        })

    # Set up static routes directly on our app
    static_path = Path(static_dir)

    if not static_path.exists():
        error_msg = f"Static directory not found: {static_path}"
        if service_logger:
            service_logger.logger.error(error_msg)
        raise FileNotFoundError(error_msg)

    # Mount static files directory
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse
    from fastapi import HTTPException

    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    if service_logger:
        log_route_mounting(service_logger, "/static", str(static_dir))

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

    # Include MCP service routes at /mcp path
    # Use include_router instead of mount for FastMCP integration
    app.include_router(mcp_service.mcp.router, prefix="/mcp")
    if service_logger:
        log_route_mounting(service_logger, "/mcp", "mcp_service")

    if service_logger:
        service_logger.logger.info("Unified service routes configured")

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
    args = {
        "host": host,
        "port": port,
        "static_dir": static_dir,
        "log_file": log_file
    }

    with service_setup_context("unified_service", args, log_file) as service_logger:
        try:
            app = create_unified_app(static_dir, service_logger)
            log_server_start(service_logger, host, port)

            # Configure uvicorn logging to use same log file
            uvicorn_config = configure_uvicorn_logging(log_file)

            uvicorn.run(
                app,
                host=host,
                port=port,
                log_level="info",
                **uvicorn_config
            )

        except FileNotFoundError as e:
            service_logger.logger.error(f"Configuration error: {e}")
            service_logger.logger.error(f"Please ensure the '{static_dir}' directory exists and contains web assets.")
            return 1
        except Exception as e:
            service_logger.logger.error(f"Failed to start unified service: {e}", exc_info=True)
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
