#!/usr/bin/env python3
"""
A FastAPI application for Memgraph with a web interface.
"""

from typing import Any
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
    config_dir = Path.home() / ".zabob" / "memgraph"
    db_path = str(config_dir / "data" / "knowledge_graph.db")

DB = SQLiteKnowledgeGraphDB(
    db_path=db_path,
)


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
async def create_relations(relations: list[dict[str, Any]]) -> dict[str, Any]:
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
async def add_observations(entity_name: str, observations: list[str]) -> dict[str, Any]:
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
    if os.getenv('DOCKER_CONTAINER') or os.path.exists('/.dockerenv'):
        return {
            "success": False,
            "error": "Browser opening is not available when running in a Docker container.",
            "hint": "Connect from the host machine at the exposed port (usually http://localhost:6789)",
            "url": None
        }

    try:
        # Get server info to find the correct port
        config_dir = Path.home() / ".zabob" / "memgraph"
        info_file = config_dir / "server_info.json"

        port = None

        if info_file.exists():
            # Read server info
            info = json.loads(info_file.read_text())
            port = info.get('port', 6789)
        else:
            # Scan for any running server
            logger.info("Scanning for running servers...")
            for test_port in range(6789, 6800):
                try:
                    import httpx
                    response = httpx.get(f"http://localhost:{test_port}/health", timeout=1)
                    if response.status_code == 200:
                        port = test_port
                        logger.info(f"Found server on port {port}")
                        break
                except Exception:
                    continue

        if port is None:
            return {
                "success": False,
                "error": "No server found running. Please start the server first.",
                "url": None
            }

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


@mcp.tool
async def search_entities_semantic(
    query: str,
    k: int = 10,
    threshold: float = 0.0,
    model_name: str | None = None,
) -> dict[str, Any]:
    """
    Search for entities using semantic similarity via vector embeddings.

    Finds entities whose observations are semantically similar to the query,
    even if they don't share exact keywords. Requires embeddings to be
    generated first.

    Args:
        query (str): Natural language search query
        k (int): Maximum number of results to return (default: 10)
        threshold (float): Minimum similarity score (0-1, default: 0.0)
        model_name (str, optional): Filter by embedding model

    Returns:
        dict: Search results with entity_id, similarity score, and entity data
    """
    from memgraph.embeddings import get_embedding_provider
    from memgraph.vector_sqlite import VectorSQLiteStore

    logger.info(f"Semantic search: {query} (k={k}, threshold={threshold})")

    # Get embedding provider
    provider = get_embedding_provider()
    if provider is None:
        return {
            "error": "No embedding provider configured",
            "hint": "Call configure_embeddings first or set environment variables"
        }

    # Initialize vector store
    vector_store = VectorSQLiteStore(db_path=db_path)  # type: ignore[arg-type]

    try:
        # Generate query embedding
        query_embedding = provider.generate(query)

        # Search vector store
        results = vector_store.search(
            query_embedding=query_embedding,
            k=k,
            threshold=threshold,
            model_name=model_name,
        )

        # Fetch entity data for results
        entities = []
        for entity_id, score in results:
            # Use existing search to get entity data
            entity_data = await DB.search_nodes(entity_id)
            if entity_data.get("entities"):
                entity_info = entity_data["entities"][0]
                entity_info["similarity_score"] = score
                entities.append(entity_info)

        return {
            "query": query,
            "count": len(entities),
            "results": entities,
        }

    except Exception as e:
        logger.error(f"Semantic search failed: {e}")
        return {"error": str(e)}
    finally:
        vector_store.close()


@mcp.tool
async def search_hybrid(
    query: str,
    k: int = 10,
    semantic_weight: float = 0.7,
    threshold: float = 0.0,
) -> dict[str, Any]:
    """
    Hybrid search combining keyword and semantic similarity.

    Merges results from traditional keyword search and vector similarity
    search, with configurable weighting between the two approaches.

    Args:
        query (str): Search query
        k (int): Maximum results to return (default: 10)
        semantic_weight (float): Weight for semantic results (0-1, default: 0.7)
        threshold (float): Minimum similarity threshold (default: 0.0)

    Returns:
        dict: Combined search results ranked by hybrid score
    """
    logger.info(f"Hybrid search: {query} (semantic_weight={semantic_weight})")

    # Get both keyword and semantic results
    keyword_results = await search_nodes(query)  # type: ignore[operator]
    semantic_results = await search_entities_semantic(query, k=k * 2, threshold=threshold)  # type: ignore[operator]

    # Handle errors
    if "error" in semantic_results:
        logger.warning(f"Semantic search failed, falling back to keyword only: {semantic_results['error']}")
        return keyword_results  # type: ignore[no-any-return]

    # Build entity scores
    entity_scores: dict[str, dict[str, Any]] = {}

    # Process keyword results (give them keyword_weight score)
    keyword_weight = 1.0 - semantic_weight
    for entity in keyword_results.get("entities", []):
        entity_id = entity.get("name", "")
        entity_scores[entity_id] = {
            "entity": entity,
            "keyword_score": keyword_weight,
            "semantic_score": 0.0,
        }

    # Process semantic results
    for entity in semantic_results.get("results", []):
        entity_id = entity.get("name", "")
        sim_score = entity.pop("similarity_score", 0.0)

        if entity_id in entity_scores:
            # Entity found by both methods
            entity_scores[entity_id]["semantic_score"] = sim_score * semantic_weight
        else:
            # Entity only found by semantic search
            entity_scores[entity_id] = {
                "entity": entity,
                "keyword_score": 0.0,
                "semantic_score": sim_score * semantic_weight,
            }

    # Calculate hybrid scores and sort
    ranked_results = []
    for _entity_id, scores in entity_scores.items():
        hybrid_score = scores["keyword_score"] + scores["semantic_score"]
        result = scores["entity"].copy()
        result["hybrid_score"] = hybrid_score
        result["keyword_score"] = scores["keyword_score"]
        result["semantic_score"] = scores["semantic_score"]
        ranked_results.append(result)

    # Sort by hybrid score descending
    ranked_results.sort(key=lambda x: x["hybrid_score"], reverse=True)

    # Limit to k results
    ranked_results = ranked_results[:k]

    return {
        "query": query,
        "count": len(ranked_results),
        "semantic_weight": semantic_weight,
        "results": ranked_results,
    }


@mcp.tool
async def generate_embeddings(
    batch_size: int = 100,
    model_name: str | None = None,
) -> dict[str, Any]:
    """
    Generate vector embeddings for all entities that don't have them yet.

    Processes entities in batches to create embeddings from their observations.
    Embeddings enable semantic search capabilities.

    Args:
        batch_size (int): Number of entities to process per batch (default: 100)
        model_name (str, optional): Specific embedding model to use

    Returns:
        dict: Statistics about embeddings generated
    """
    from memgraph.embeddings import get_embedding_provider
    from memgraph.vector_sqlite import VectorSQLiteStore

    logger.info(f"Generating embeddings (batch_size={batch_size})")

    # Get embedding provider
    provider = get_embedding_provider()
    if provider is None:
        return {
            "error": "No embedding provider configured",
            "hint": "Call configure_embeddings first or set environment variables"
        }

    # Initialize vector store
    vector_store = VectorSQLiteStore(db_path=db_path)  # type: ignore[arg-type]

    try:
        # Get all entities
        graph = await DB.read_graph()
        entities = graph.get("entities", [])

        # Filter entities that need embeddings
        existing_count = vector_store.count(model_name=provider.model_name)
        logger.info(f"Found {len(entities)} total entities, {existing_count} already have embeddings")

        # Get entities without embeddings
        entities_to_process = []
        for entity in entities:
            entity_id = entity.get("name", "")
            if vector_store.get(entity_id) is None:
                entities_to_process.append(entity)

        if not entities_to_process:
            return {
                "message": "All entities already have embeddings",
                "total_entities": len(entities),
                "existing_embeddings": existing_count,
                "generated": 0,
            }

        # Process in batches
        generated = 0
        for i in range(0, len(entities_to_process), batch_size):
            batch = entities_to_process[i:i + batch_size]

            # Create text from observations
            texts = []
            entity_ids = []
            for entity in batch:
                entity_id = entity.get("name", "")
                observations = entity.get("observations", [])
                text = " ".join(observations) if observations else entity_id
                texts.append(text)
                entity_ids.append(entity_id)

            # Generate embeddings
            embeddings = provider.batch_generate(texts)

            # Store embeddings
            vector_store.batch_add(
                entity_ids=entity_ids,
                embeddings=embeddings,
                model_name=provider.model_name,
            )

            generated += len(batch)
            logger.info(f"Generated {generated}/{len(entities_to_process)} embeddings")

        return {
            "message": f"Generated {generated} embeddings",
            "total_entities": len(entities),
            "existing_embeddings": existing_count,
            "generated": generated,
            "model": provider.model_name,
        }

    except Exception as e:
        logger.error(f"Failed to generate embeddings: {e}")
        return {"error": str(e)}
    finally:
        vector_store.close()


@mcp.tool
async def configure_embeddings(
    provider: str = "sentence-transformers",
    model: str | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    """
    Configure the embedding provider for semantic search.

    Supports local sentence-transformers models or OpenAI's API.

    Args:
        provider (str): "sentence-transformers" or "openai" (default: sentence-transformers)
        model (str, optional): Model name. Defaults:
            - sentence-transformers: "all-MiniLM-L6-v2"
            - openai: "text-embedding-3-small"
        api_key (str, optional): OpenAI API key (for OpenAI provider)

    Returns:
        dict: Configuration status and provider details
    """
    from memgraph.embeddings import configure_from_dict, get_embedding_provider

    logger.info(f"Configuring embeddings: provider={provider}, model={model}")

    try:
        config = {
            "provider": provider,
            "model": model,
            "api_key": api_key,
        }

        configure_from_dict(config)

        # Verify configuration
        active_provider = get_embedding_provider()
        if active_provider is None:
            return {"error": "Failed to configure provider"}

        return {
            "message": "Embedding provider configured successfully",
            "provider": provider,
            "model": active_provider.model_name,
            "dimensions": active_provider.dimensions,
        }

    except Exception as e:
        logger.error(f"Failed to configure embeddings: {e}")
        return {"error": str(e)}


