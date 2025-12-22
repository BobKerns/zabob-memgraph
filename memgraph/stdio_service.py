#!/usr/bin/env python3
"""
Stdio-based MCP service for zabob-memgraph.

Provides direct stdio transport for MCP protocol without HTTP/SSE overhead.
Can run alongside HTTP server - SQLite WAL mode handles concurrent access.
"""

import asyncio
import logging
from memgraph.config import Config, default_config_dir, load_config
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
