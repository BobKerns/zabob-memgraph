#!/usr/bin/env python3
'''
A FastAPI application for Memgraph with a web interface.
'''

import logging
from fastmcp import FastMCP

from memgraph.sqlite_backend import SQLiteKnowledgeGraphDB

logger = logging.getLogger(__name__)


mcp = FastMCP(
    name="Zabob Memgraph Knowledge Graph Server",
    instructions="A FastAPI application for Memgraph with a web interface.",
)


DB = SQLiteKnowledgeGraphDB(
    db_path="knowledge_graph.db",
)


@mcp.tool
async def read_graph(name: str = 'default') -> dict:
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
    return {
        "created": len(relations),
        "relations": [f"{r.get('source')} -> {r.get('target')}" for r in relations]
    }


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
    await DB.create_entities([{
        "name": entity_name,
        "entityType": "update",  # Will merge with existing
        "observations": observations
    }])
    return {
        "entity": entity_name,
        "added": len(observations)
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
