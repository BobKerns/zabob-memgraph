#!/usr/bin/env python3
"""
A FastAPI application for Memgraph with a web interface.
"""

import json
import logging
import os
import webbrowser
from pathlib import Path
from fastmcp import FastMCP

from memgraph.sqlite_backend import SQLiteKnowledgeGraphDB

logger = logging.getLogger(__name__)


mcp = FastMCP(
    name="Zabob Memgraph Knowledge Graph Server",
    instructions="A FastAPI application for Memgraph with a web interface.",
)

# Get database path from environment or use default in config directory
db_path = os.getenv('MEMGRAPH_DATABASE_PATH')
if not db_path:
    config_dir = Path.home() / ".zabob-memgraph"
    db_path = str(config_dir / "data" / "knowledge_graph.db")

DB = SQLiteKnowledgeGraphDB(
    db_path=db_path,
)


@mcp.tool
async def read_graph(name: str = "default") -> dict:
    """
    Read the complete knowledge graph from the database.

    This returns all entities, relations, and observations in the graph,
    formatted for visualization or analysis.

    Args:
        name (str): Graph identifier (default: 'default')

    Returns:
        dict: Complete graph data with entities, relations, and observations
    """
    logger.info(f"Reading graph: {name}")
    return await DB.read_graph()


@mcp.tool
async def search_nodes(query: str) -> dict:
    """
    Search the knowledge graph for entities and relations matching the query.

    Performs full-text search across entity names, types, and observations.

    Args:
        query (str): Search query string

    Returns:
        dict: Search results containing matching entities and their metadata
    """
    logger.info(f"Searching graph with query: {query}")
    return await DB.search_nodes(query)


@mcp.tool
async def get_stats() -> dict:
    """
    Get statistics about the knowledge graph.

    Returns counts and metadata about entities, relations, and observations
    in the database.

    Returns:
        dict: Statistics including entity count, relation count, observation count, etc.
    """
    logger.info("Getting graph statistics")
    return await DB.get_stats()


@mcp.tool
async def create_entities(entities: list[dict]) -> dict:
    """
    Create new entities in the knowledge graph.

    Each entity should have:
    - name (str): Entity identifier
    - entityType (str): Type of entity
    - observations (list[str], optional): Initial observations

    Args:
        entities (list[dict]): List of entity objects to create

    Returns:
        dict: Result with count of entities created
    """
    logger.info(f"Creating {len(entities)} entities")
    await DB.create_entities(entities)
    return {"created": len(entities), "entities": [e.get("name") for e in entities]}


@mcp.tool
async def create_relations(relations: list[dict]) -> dict:
    """
    Create new relations between entities in the knowledge graph.

    Each relation should have:
    - source (str): Source entity name
    - target (str): Target entity name
    - relation (str): Type of relation

    Args:
        relations (list[dict]): List of relation objects to create

    Returns:
        dict: Result with count of relations created
    """
    logger.info(f"Creating {len(relations)} relations")
    await DB.create_relations(relations)
    return {"created": len(relations), "relations": [f"{r.get('source')} -> {r.get('target')}" for r in relations]}


@mcp.tool
async def add_observations(entity_name: str, observations: list[str]) -> dict:
    """
    Add observations to an existing entity.

    Args:
        entity_name (str): Name of the entity to add observations to
        observations (list[str]): List of observation strings to add

    Returns:
        dict: Result with count of observations added
    """
    logger.info(f"Adding {len(observations)} observations to {entity_name}")
    # Create a pseudo-entity update with new observations
    await DB.create_entities(
        [
            {
                "name": entity_name,
                "entityType": "update",  # Will merge with existing
                "observations": observations,
            }
        ]
    )
    return {"entity": entity_name, "added": len(observations)}


@mcp.tool
async def open_browser(node_id: str | None = None) -> dict:
    """
    Open a browser window to visualize the knowledge graph.

    Reads the server URL from server_info.json and opens it in the default browser.
    Optionally focuses on a specific node if node_id is provided.

    Note: Only available when running locally, not in Docker containers.

    Args:
        node_id (str, optional): ID of a specific node to focus on in the visualization

    Returns:
        dict: Status of the operation with URL that was opened
    """
    # Check if we're in a Docker container
    if os.getenv('DOCKER_CONTAINER') or os.path.exists('/.dockerenv'):
        return {
            "success": False,
            "error": "Browser opening is not available when running in a Docker container.",
            "hint": "Connect from the host machine at the exposed port (usually http://localhost:6789)",
            "url": None
        }

    try:
        # Get server info to find the correct port
        config_dir = Path.home() / ".zabob-memgraph"
        info_file = config_dir / "server_info.json"

        if not info_file.exists():
            return {
                "success": False,
                "error": "Server info not found. Is the server running?",
                "url": None
            }

        # Read server info
        info = json.loads(info_file.read_text())
        port = info.get('port', 6789)

        # Build URL
        url = f"http://localhost:{port}"
        if node_id:
            url += f"#{node_id}"

        # Open browser
        webbrowser.open(url)

        logger.info(f"Opened browser to {url}")

        message = "Browser opened to knowledge graph visualization"
        if node_id:
            message += f" focused on node {node_id}"

        return {
            "success": True,
            "url": url,
            "message": message
        }

    except Exception as e:
        logger.error(f"Failed to open browser: {e}")
        return {
            "success": False,
            "error": str(e),
            "url": None
        }


if __name__ == "__main__":
    # Run the MCP server
    import sys

    try:
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)
