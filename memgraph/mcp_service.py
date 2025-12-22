#!/usr/bin/env python3
"""
A FastAPI application for Memgraph with a web interface.
"""

from collections.abc import AsyncGenerator
import atexit
from contextlib import asynccontextmanager
from typing import Any
import logging
import os
import webbrowser

from starlette.types import Lifespan
from fastapi import FastAPI
from fastmcp import FastMCP

from memgraph.config import IN_DOCKER, Config, default_config_dir, load_config
from memgraph.sqlite_backend import SQLiteKnowledgeGraphDB

from memgraph.launcher import save_server_info

logger = logging.getLogger(__name__)


def setup_mcp(config: Config) -> FastMCP:
    """
    Set up the FastMCP application with Memgraph knowledge graph tools.

    Returns:
        FastMCP: Configured FastMCP application
    """
    mcp = FastMCP(
        name="Zabob Memgraph Knowledge Graph Server",
        instructions="A FastAPI application for Memgraph with a web interface.",
        lifespan=get_lifespan_hook(config),
    )
    DB = SQLiteKnowledgeGraphDB(config)

    @mcp.tool
    async def read_graph(name: str = "default") -> dict[str, Any]:
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
    async def search_nodes(query: str) -> dict[str, Any]:
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
    async def get_server_info() -> dict[str, Any]:
        """
        Get information about this server instance.

        Returns server identity information including name, version, port, host,
        database path, and container details if running in Docker.
        Useful for distinguishing between multiple server instances in multi-agent scenarios.

        Returns:
            dict: Server information with name, version, port, host, database_path,
                  in_docker, and container_name (if applicable)
        """
        from memgraph.__version__ import __version__

        info = {
            "name": config.get("name", "default"),
            "version": __version__,
            "port": config.get("real_port") if IN_DOCKER else config.get("port"),
            "host": config.get("host"),
            "database_path": str(config.get("database_path")),
            "in_docker": IN_DOCKER,
        }

        if IN_DOCKER:
            info["container_name"] = config.get("container_name")

        logger.info(f"Returning server info for '{info['name']}'")
        return info

    @mcp.tool
    async def get_stats() -> dict[str, Any]:
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
    async def create_entities(entities: list[dict[str, Any]]) -> dict[str, Any]:
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
    async def create_relations(relations: list[dict[str, Any]], external_refs: list[str]) -> dict[str, Any]:
        """
        Create new relations between entities in the knowledge graph.

        Each relation should have:
        - source (str): Source entity name
        - target (str): Target entity name
        - relation (str): Type of relation

        Args:
            relations (list[dict]): List of relation objects to create
            external_refs (list[str]): Entity names that must exist (REQUIRED).
                Validates all referenced entities exist before creating relations.
                Returns error if any are missing. Use create_subgraph if you need
                to create entities and relations together.

        Returns:
            dict: Result with count of relations created, or error if validation fails
        """
        logger.info(f"Creating {len(relations)} relations (external_refs: {external_refs})")

        # Map field names from MCP format to SQLite backend format
        # Handle both formats: MCP (source/target/relation) and backend (from_entity/to/relationType)
        mapped_relations = []
        for r in relations:
            if "source" in r:
                # MCP format
                mapped_relations.append(
                    {
                        "from_entity": r["source"],
                        "to": r["target"],
                        "relationType": r["relation"],
                    }
                )
            else:
                # Already in backend format
                mapped_relations.append(r)

        # Get initial count for verification
        initial_stats = await DB.get_stats()
        initial_count = initial_stats.get("relation_count", 0)

        # Create relations with validation
        try:
            await DB.create_relations(mapped_relations, external_refs=external_refs)
        except ValueError as e:
            logger.error(f"Validation failed: {e}")
            return {"error": str(e), "created": 0, "relations": []}

        # Verify they were created
        final_stats = await DB.get_stats()
        final_count = final_stats.get("relation_count", 0)
        actual_created = final_count - initial_count

        if actual_created != len(relations):
            logger.warning(f"Expected to create {len(relations)} relations, but only {actual_created} were created")

        return {
            "created": actual_created,
            "relations": [f"{r.get('source')} -> {r.get('target')}" for r in relations],
        }

    @mcp.tool
    async def create_subgraph(
        entities: list[dict[str, Any]],
        relations: list[dict[str, Any]],
        external_refs: list[str] | None = None,
        observations: dict[str, list[str]] | None = None,
    ) -> dict[str, Any]:
        """
        Create a subgraph atomically with entities, relations, and observations.

        This is a high-level operation that combines entity creation, observation
        addition, and relation creation in a single atomic transaction. Use this
        when you need to add a complete, self-contained graph pattern.

        Args:
            entities (list[dict]): New entities to create. Each should have:
                - name (str): Entity name
                - entityType (str): Entity type
                - observations (list[str], optional): Initial observations
            relations (list[dict]): Relations to create. Each should have:
                - source (str): Source entity name
                - target (str): Target entity name
                - relation (str): Relation type
            external_refs (list[str], optional): Existing entity names being referenced.
                These entities must already exist. Defaults to empty list.
            observations (dict[str, list[str]], optional): Additional observations to add
                to any entity (new or existing). Keys are entity names, values are
                lists of observation strings.

        Returns:
            dict: Result with counts of created entities, relations, and observations added,
                  or error if validation fails

        Example:
            create_subgraph(
                entities=[{"name": "Task-123", "entityType": "task", "observations": ["Started today"]}],
                external_refs=["Bob Kerns", "zabob-memgraph"],
                observations={
                    "Task-123": ["Assigned to Bob"],
                    "Bob Kerns": ["Working on Task-123"]
                },
                relations=[
                    {"source": "Task-123", "target": "zabob-memgraph", "relation": "modifies"},
                    {"source": "Bob Kerns", "target": "Task-123", "relation": "assigned_to"}
                ]
            )
        """
        logger.info(
            f"Creating subgraph: {len(entities)} entities, {len(relations)} relations, "
            f"{len(observations or {})} observation groups, external_refs: {external_refs}"
        )

        # Map relation formats
        mapped_relations = []
        for r in relations:
            if "source" in r:
                mapped_relations.append(
                    {
                        "from_entity": r["source"],
                        "to": r["target"],
                        "relationType": r["relation"],
                    }
                )
            else:
                mapped_relations.append(r)

        try:
            await DB.create_subgraph(
                entities=entities,
                relations=mapped_relations,
                external_refs=external_refs,
                observations=observations,
            )

            return {
                "created_entities": len(entities),
                "created_relations": len(relations),
                "observation_groups": len(observations or {}),
                "entities": [e["name"] for e in entities],
                "relations": [f"{r.get('source')} -> {r.get('target')}" for r in relations],
            }
        except ValueError as e:
            logger.error(f"Subgraph creation failed: {e}")
            return {"error": str(e), "created_entities": 0, "created_relations": 0, "observation_groups": 0}

    @mcp.tool
    async def add_observations(
        entity_name: str, observations: list[str], external_refs: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Add observations to an existing entity.

        Args:
            entity_name (str): Name of the entity to add observations to
            observations (list[str]): List of observation strings to add
            external_refs (list[str], optional): Entity names that must exist.
                If provided, validates all referenced entities exist.
                Defaults to [entity_name] if not specified.

        Returns:
            dict: Result with count of observations added, or error if validation fails
        """
        logger.info(f"Adding {len(observations)} observations to {entity_name} (external_refs: {external_refs})")

        # Default to validating the target entity exists
        if external_refs is None:
            external_refs = [entity_name]

        # Validate entity exists
        try:
            import sqlite3

            with sqlite3.connect(DB.db_path) as conn:
                conn.row_factory = sqlite3.Row
                placeholders = ",".join("?" * len(external_refs))
                cursor = conn.execute(
                    f"SELECT name FROM entities WHERE name IN ({placeholders})",
                    external_refs,
                )
                found = {row["name"] for row in cursor}
                missing = set(external_refs) - found
                if missing:
                    error_msg = f"Referenced entities not found: {sorted(missing)}"
                    logger.error(error_msg)
                    return {"error": error_msg, "entity": entity_name, "added": 0}
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return {"error": str(e), "entity": entity_name, "added": 0}

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
    async def open_browser(node_id: str | None = None) -> dict[str, Any]:
        """
        Open a browser window to visualize the knowledge graph.

        Reads the server URL from server_info.json or scans for running servers.
        Optionally focuses on a specific node if node_id is provided.

        If multiple servers are running, opens the first one found.

        Note: Only available when running locally, not in Docker containers.

        Args:
            node_id (str, optional): ID of a specific node to focus on in the visualization

        Returns:
            dict: Status of the operation with URL that was opened
        """
        # Check if we're in a Docker container
        if IN_DOCKER:
            return {
                "success": False,
                "error": "Browser opening is not available when running in a Docker container.",
                "hint": "Connect from the host machine at the exposed port (usually http://localhost:6789)",
                "url": None,
            }

        try:
            config_dir = default_config_dir()
            config = load_config(config_dir)
            real_port = config["real_port"]
            # Build URL
            url = f"http://localhost:{real_port}"
            if node_id:
                url += f"#{node_id}"

            # Open browser
            webbrowser.open(url)

            logger.info(f"Opened browser to {url}")

            message = "Browser opened to knowledge graph visualization"
            if node_id:
                message += f" focused on node {node_id}"

            return {"success": True, "url": url, "message": message}

        except Exception as e:
            logger.error(f"Failed to open browser: {e}")
            return {"success": False, "error": str(e), "url": None}

    return mcp


def get_lifespan_hook(config: Config) -> Lifespan[Any]:
    """
    Create an async lifespan hook for the FastMCP application.
    """

    @asynccontextmanager
    async def lifecycle_hook(app: FastAPI) -> AsyncGenerator[None, Any]:
        """Example of an async lifecycle hook for the unified app."""

        info_file = save_server_info(
            config["config_dir"],
            launched_by="unified_service",
            pid=os.getpid(),
            host=config["host"],
            port=config["port"],
            database_path=config["database_path"],
        )

        def cleanup() -> None:
            if info_file:
                info_file.unlink(missing_ok=True)

        atexit.register(cleanup)
        try:
            yield
        finally:
            info_file.unlink(missing_ok=True)

    return lifecycle_hook


if __name__ == "__main__":
    # Run the MCP server
    import sys

    try:
        mcp = setup_mcp(load_config(default_config_dir()))
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)
