#!/usr/bin/env python3
"""
Static web content server for knowledge graph visualization.

Minimal FastAPI server focused solely on serving static web assets.
Sibling to mcp_service.py - handles web content while MCP service handles data.
"""

from collections.abc import AsyncGenerator
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Any
import sys

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

from memgraph.__version__ import __version__
from memgraph.config import default_config_dir, load_config, Config
from memgraph.service_logging import (
    service_setup_context,
    service_async_context,
    log_app_creation,
    log_route_mounting,
    log_server_start,
    configure_uvicorn_logging
)


app = FastAPI(
    title="Knowledge Graph Web Service",
    description="Static content server for knowledge graph visualization",
    version="1.0.0"
)


def setup_static_routes(static_dir: str = "web", service_logger: Any = None, target_app: Any = None) -> None:
    """
    Configure static file serving.

    Args:
        static_dir: Directory containing static web assets (default: "web")
        service_logger: Logger instance for tracking setup
        target_app: FastAPI app to configure (uses global app if None)
    """
    if target_app is None:
        target_app = app

    static_path = Path(static_dir)

    if service_logger:
        service_logger.logger.info(f"Setting up static routes for: {str(static_path)}")
        service_logger.logger.info(f"Static path exists: {static_path.exists()}")
        if static_path.exists():
            contents = [str(p.name) for p in static_path.iterdir()]
            service_logger.logger.info(f"Static path contents: {' | '.join(contents)}")

    if not static_path.exists():
        error_msg = f"Static directory not found: {static_path}"
        if service_logger:
            service_logger.logger.error(error_msg)
        raise FileNotFoundError(error_msg)

    # Mount static files directory
    target_app.mount("/static", StaticFiles(directory=static_dir), name="static")
    if service_logger:
        log_route_mounting(service_logger, "/static", str(static_dir))

    # Serve index.html at root
    @target_app.get("/")
    async def serve_index() -> FileResponse:
        index_path = static_path / "index.html"
        if service_logger:
            service_logger.logger.info(f"Serving index from: {str(index_path)}")
            service_logger.logger.info(f"Index exists: {index_path.exists()}")
        if not index_path.exists():
            raise HTTPException(status_code=404, detail="index.html not found")
        return FileResponse(index_path)

    # Health check endpoint
    @target_app.get("/health")
    async def health_check() -> dict[str, str]:
        return {"status": "healthy", "service": "web_service", "version": __version__}


def create_app(static_dir: str = "web", service_logger: Any = None) -> FastAPI:
    """
    Create configured FastAPI application.

    Args:
        static_dir: Directory containing static web assets
        service_logger: Logger instance for tracking app creation

    Returns:
        Configured FastAPI application
    """
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        async with service_async_context(service_logger):
            yield

    app = FastAPI(
        title="Knowledge Graph Web Service",
        description="Static content server for knowledge graph visualization",
        version="1.0.0",
        lifespan=lifespan
    )

    if service_logger:
        log_app_creation(service_logger, "web", {
            "static_dir": static_dir,
            "title": "Knowledge Graph Web Service"
        })

    setup_static_routes(static_dir, service_logger, app)
    return app


def run_web_service(config: Config | None = None) -> int:
    """
    Run the web service.

    Args:
        config: Configuration dictionary (loads from default if None)
          Important keys are 'host', 'port', 'log_level', 'access_log'
            host: Host to bind to (default: localhost except in a container)
            port: Port to listen on (default: 6789)
            static_dir: Directory containing static web assets (default: memgraph/web)
            log_file: Log file path (default: None, logs to stderr)
    """
    config_dir = default_config_dir()
    config = config or load_config(config_dir)
    log_file = str(config['log_file']) if config['log_file'] else None
    log_args = {
        "host": config['host'],
        "port": config['port'],
        "static_dir": str(config['static_dir']),
        "reload": config['reload'],
        "log_file": log_file
    }

    with service_setup_context("web_service", log_args, log_file) as service_logger:
        try:
            # Use create_app instead of global app for better encapsulation
            app_instance = create_app(str(config['static_dir']), service_logger)
            log_server_start(service_logger, config['host'], config['port'])

            # Configure uvicorn logging to use same log file
            uvicorn_config = configure_uvicorn_logging(log_file)

            uvicorn.run(
                app_instance,
                host=config['host'],
                port=config['port'],
                log_level=config['log_level'].lower(),
                reload=config['reload'],
                access_log=config['access_log'],
                ws='websockets-sansio',
                **uvicorn_config
            )
            return 0

        except FileNotFoundError as e:
            service_logger.logger.error(f"Configuration error: {e}")
            static_dir = config['static_dir']
            service_logger.logger.error(f"Please ensure the '{static_dir}' directory exists and contains web assets.")
            return 1
        except Exception as e:
            service_logger.logger.error(f"Failed to start web service: {e}", exc_info=True)
            return 1


if __name__ == "__main__":
    import click

    @click.command()
    @click.option("--host", default="localhost", help="Host to bind to")
    @click.option("--port", type=int, default=6789, help="Port to listen on")
    @click.option("--static-dir", default="web", help="Static files directory")
    @click.option("--reload", is_flag=True, help="Enable auto-reload")
    @click.option("--log-file", help="Log file path (default: stderr)")
    @click.option("--config-dir", type=Path, default=None, help="Path to configuration file")
    def cli(host: str,
            port: int,
            static_dir: str,
            reload: bool,
            log_file: str | None,
            config_dir: Path | None) -> None:
        """
        Knowledge Graph Web Service - Static content server.
        """

        config_dir = config_dir or default_config_dir()
        config = load_config(config_dir,
                             host=host,
                             port=port,
                             static_dir=static_dir,
                             reload=reload,
                             log_file=log_file)
        exit_code = run_web_service(config)

        if exit_code:
            sys.exit(exit_code)

    cli()
