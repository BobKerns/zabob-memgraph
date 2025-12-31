#!/usr/bin/env python3
"""
Stdio-based MCP service for zabob-memgraph.

Provides direct stdio transport for MCP protocol without HTTP/SSE overhead.
Can run alongside HTTP server - SQLite WAL mode handles concurrent access.
"""

import asyncio
import logging
from memgraph.config import Config, default_config_dir, load_config, IN_DOCKER
import memgraph.mcp_service as mcp_service

logger = logging.getLogger(__name__)


async def run_stdio_service(config: Config | None = None) -> None:
    """
    Run the MCP service using stdio transport.

    Args:
        config: Configuration dictionary (loads from default if None)
    """
    if config is None:
        config = load_config(default_config_dir())

    # Set up the MCP service with all tools
    mcp = mcp_service.setup_mcp(config)

    # Log startup
    logger.info("Starting zabob-memgraph stdio service")
    logger.info(f"Database: {config['database_path']}")

    # Run with stdio transport
    await mcp.run_stdio_async()


async def run_stdio_service_with_web(config: Config | None = None) -> None:
    """
    Run the MCP service using stdio transport with web server in background.

    This enables browser visualization while using stdio for MCP protocol.
    SQLite WAL mode handles concurrent access between stdio and web server.

    Args:
        config: Configuration dictionary (loads from default if None)
    """
    if config is None:
        config = load_config(default_config_dir())

    # Determine host and port for web server
    host = config.get("host")
    if host is None:
        host = "0.0.0.0" if IN_DOCKER else "localhost"
    if IN_DOCKER:
        host = "0.0.0.0"

    port = config.get("port", 6789)

    # Log startup
    logger.info("Starting zabob-memgraph stdio service with web server")
    logger.info(f"Database: {config['database_path']}")
    logger.info(f"Web interface: http://{host}:{port}")

    # Import uvicorn and service
    import uvicorn
    from memgraph.service import create_unified_app

    # Create the web app
    app = create_unified_app(config)

    # Create uvicorn server config
    uvicorn_config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="warning",  # Quiet for stdio mode
        access_log=False,
    )
    server = uvicorn.Server(uvicorn_config)

    # Set up MCP stdio service
    mcp = mcp_service.setup_mcp(config)

    # Run both concurrently
    async def run_web_server() -> None:
        await server.serve()

    async def run_stdio() -> None:
        await mcp.run_stdio_async()

    # Run both tasks concurrently
    await asyncio.gather(
        run_web_server(),
        run_stdio(),
    )


def main() -> None:
    """Entry point for stdio service."""
    # Configure logging to stderr (not stdout - that's for MCP protocol)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],  # stderr by default
    )

    # Run the async service
    asyncio.run(run_stdio_service())


if __name__ == "__main__":
    main()
