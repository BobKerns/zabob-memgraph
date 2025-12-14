#!/usr/bin/env python3
"""
Unified ASGI service combining web and MCP functionality.

Mounts web routes onto FastMCP's HTTP app for integrated operation.
"""

from pathlib import Path
from typing import Any
import uvicorn
import click

from starlette.staticfiles import StaticFiles
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Route

# Use absolute imports
import memgraph.mcp_service as mcp_service
from memgraph.service_logging import (
    service_setup_context,
    log_app_creation,
    log_route_mounting,
    log_server_start,
    configure_uvicorn_logging,
    ServiceLogger,
)


def create_unified_app(static_dir: str = "memgraph/web", service_logger: ServiceLogger | None = None) -> Any:
    """
    Create unified application with both web and MCP routes.

    Uses FastMCP's http_app() as the base and adds web routes to it.

    Args:
        static_dir: Directory containing static web assets (default: memgraph/web)
        service_logger: Logger instance for tracking app creation

    Returns:
        Configured Starlette/FastAPI application with both route collections
    """
    # Start with FastMCP's HTTP app which provides /mcp endpoint
    app = mcp_service.mcp.http_app()

    # Add CORS middleware to allow requests from browsers
    from starlette.middleware.cors import CORSMiddleware as StarletteCORS

    app.add_middleware(
        StarletteCORS,
        allow_origins=["*"],  # Allow all origins for development
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if service_logger:
        log_app_creation(
            service_logger,
            "unified",
            {"static_dir": static_dir, "title": "Knowledge Graph with MCP", "base": "FastMCP http_app"},
        )

    # Set up static routes
    static_path = Path(static_dir)

    if not static_path.exists():
        error_msg = f"Static directory not found: {static_path}"
        if service_logger:
            service_logger.logger.error(error_msg)
        raise FileNotFoundError(error_msg)

    # Mount static files directory
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    if service_logger:
        log_route_mounting(service_logger, "/static", str(static_dir))

    # Add web service routes using Starlette's routing
    async def serve_index(request: Any) -> FileResponse | JSONResponse:
        index_path = static_path / "index.html"
        if not index_path.exists():
            return JSONResponse({"error": "index.html not found"}, status_code=404)
        return FileResponse(index_path)

    async def health_check(request: Any) -> JSONResponse:
        return JSONResponse({"status": "healthy", "service": "unified_service"})

    # Add routes to the Starlette app
    app.routes.extend(
        [
            Route("/", serve_index),
            Route("/health", health_check),
        ]
    )

    if service_logger:
        log_route_mounting(service_logger, "/", "index (web UI)")
        log_route_mounting(service_logger, "/health", "health check")
        service_logger.logger.info("Unified service routes configured")

    return app


# Create app at module level for uvicorn auto-reload
app = create_unified_app()


def main(
    host: str = "localhost",
    port: int = 6789,
    static_dir: str = "memgraph/web",
    log_file: str | None = None
) -> int:
    """
    Run the unified service.

    Args:
        host: Host to bind to (default: localhost)
        port: Port to listen on (default: 6789)
        static_dir: Directory containing static web assets (default: memgraph/web)
        log_file: Log file path (default: None, logs to stderr)
    """
    args = {"host": host, "port": port, "static_dir": static_dir, "log_file": log_file}

    with service_setup_context("unified_service", args, log_file) as service_logger:
        try:
            app = create_unified_app(static_dir, service_logger)
            log_server_start(service_logger, host, port)

            # Configure uvicorn logging to use same log file
            uvicorn_config = configure_uvicorn_logging(log_file)

            uvicorn.run(app, host=host, port=port, log_level="info", **uvicorn_config)
            return 0

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
    @click.option("--port", type=int, default=6789, help="Port to listen on")
    @click.option("--static-dir", default="memgraph/web", help="Static files directory")
    @click.option("--log-file", help="Log file path (default: stderr)")
    def cli(host: str, port: int, static_dir: str, log_file: str | None) -> None:
        """Knowledge Graph Unified Service - Web + MCP on single port."""
        exit_code = main(host=host, port=port, static_dir=static_dir, log_file=log_file)

        if exit_code:
            exit(exit_code)

    cli()
