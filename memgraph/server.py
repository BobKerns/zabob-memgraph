"""
MCP HTTP Server for Knowledge Graph

Provides both MCP protocol support and HTTP REST endpoints for knowledge graph data.
Integrates with thread-safe knowledge graph storage to prevent multi-client issues.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try different knowledge graph backends in order of preference
# SQLite backend for normal operation, FastMCP client only for external connections
knowledge_client: Any = None

try:
    from .sqlite_backend import sqlite_knowledge_db
    
    knowledge_client = sqlite_knowledge_db
    logger.info("Using SQLite database backend for direct operation")
except ImportError as e:
    logger.error("SQLite backend not available")
    raise ImportError(
        "SQLite backend required for zabob-memgraph operation. "
        "Please ensure sqlite_backend is properly configured."
    ) from e

# Create FastAPI app
app = FastAPI(
    title="Knowledge Graph MCP Server",
    description="HTTP interface for knowledge graph visualization with thread-safe multi-client support",
    version="0.2.0",
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for web client
web_dir = Path(__file__).parent / "web"
if web_dir.exists():
    app.mount("/static", StaticFiles(directory=str(web_dir)), name="static")

@app.get("/")
async def root() -> HTMLResponse:
    """Serve the main visualization page"""
    web_file = Path(__file__).parent / "web" / "index.html"
    if web_file.exists():
        # Convert FileResponse to HTMLResponse for type consistency
        with open(web_file, encoding="utf-8") as f:
            content = f.read()
        return HTMLResponse(content)
    return HTMLResponse(
        """
    <html>
        <head>
            <title>Knowledge Graph</title>
            <link rel="icon" type="image/x-icon" href="/static/favicon.png">
            <link rel="mask-icon" href="/static/favicon.svg" color="#000000">
 color="#000000">
        </head>
        <body>
            <h1>Knowledge Graph MCP Server v0.2.0</h1>
            <p><strong>Thread-Safe Multi-Client Support Enabled</strong></p>
            <p>API endpoints:</p>
            <ul>
                <li><a href="/api/knowledge-graph">/api/knowledge-graph</a> - Full graph data</li>
                <li><a href="/api/search?q=test">/api/search?q=test</a> - Search</li>
                <li><a href="/health">/health</a> - Health check</li>
                <li><a href="/docs">/docs</a> - API documentation</li>
            </ul>
        </body>
    </html>
    """
    )


@app.get("/api/knowledge-graph")
async def get_knowledge_graph() -> dict[str, Any]:
    """Get the complete knowledge graph data with thread-safe access"""
    try:
        graph_data = await knowledge_client.read_graph()

        # Transform to D3 visualization format
        nodes = []
        for entity in graph_data["entities"]:

            # Map entity types to visualization groups
            group = (
                "person"
                if entity["entityType"] == "person"
                else (
                    "project"
                    if entity["entityType"] == "project"
                    else (
                        "development"
                        if "development" in entity["entityType"].lower()
                        else (
                            "strategy"
                            if "strategy" in entity["entityType"].lower()
                            or "plan" in entity["entityType"].lower()
                            else (
                                "debug"
                                if "debug" in entity["entityType"].lower()
                                or "investigation" in entity["entityType"].lower()
                                else "technology"
                            )
                        )
                    )
                )
            )

            nodes.append(
                {
                    "id": entity["name"],
                    "group": group,
                    "type": entity["entityType"],
                    "observations": entity["observations"],
                }
            )

        links = []
        for relation in graph_data["relations"]:
            links.append(
                {
                    "source": relation["from_entity"],
                    "target": relation["to"],
                    "relation": relation["relationType"],
                }
            )

        return {
            "nodes": nodes,
            "links": links,
            "stats": {
                "entityCount": len(nodes),
                "relationCount": len(links),
                "dataSource": "thread-safe file storage",
            },
        }
    except Exception as e:
        logger.error(f"Error reading knowledge graph: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to read knowledge graph: {str(e)}"
        ) from e


@app.get("/api/entities")
async def get_entities() -> list[dict[str, Any]]:
    """Get all entities with thread-safe access"""
    try:
        graph_data = await knowledge_client.read_graph()
        entities: list[dict[str, Any]] = graph_data.get("entities", [])
        return entities
    except Exception as e:
        logger.error(f"Error reading entities: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to read entities: {str(e)}"
        ) from e


@app.get("/api/search")
async def search_knowledge_graph(q: str) -> list[dict[str, Any]]:
    """Search across all entities and observations with thread-safe access"""
    if not q or len(q.strip()) < 2:
        return []

    try:
        search_results = await knowledge_client.search_nodes(q.strip())

        # Transform to search result format
        results = []
        query = q.lower().strip()

        for entity in search_results["entities"]:
            # Search entity name
            if query in entity["name"].lower():
                results.append(
                    {
                        "entity": entity["name"],
                        "type": "name",
                        "content": entity["name"],
                        "entityType": entity["entityType"],
                        "score": 10,
                    }
                )

            # Search observations
            for i, obs in enumerate(entity["observations"]):
                if query in obs.lower():
                    results.append(
                        {
                            "entity": entity["name"],
                            "type": "observation",
                            "content": obs,
                            "entityType": entity["entityType"],
                            "observationIndex": i,
                            "score": 5,
                        }
                    )

        # Sort by score (descending)
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:20]  # Limit results

    except Exception as e:
        logger.error(f"Error searching knowledge graph: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}") from e


@app.post("/api/entities")
async def create_entities(entities: list[dict[str, Any]]) -> dict[str, str]:
    """Create new entities with thread-safe access"""
    try:
        await knowledge_client.create_entities(entities)
        return {"status": "success", "message": f"Created {len(entities)} entities"}
    except Exception as e:
        logger.error(f"Error creating entities: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to create entities: {str(e)}"
        ) from e


@app.post("/api/relations")
async def create_relations(relations: list[dict[str, Any]]) -> dict[str, str]:
    """Create new relations with thread-safe access"""
    try:
        await knowledge_client.create_relations(relations)
        return {"status": "success", "message": f"Created {len(relations)} relations"}
    except Exception as e:
        logger.error(f"Error creating relations: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to create relations: {str(e)}"
        ) from e


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "knowledge-graph-mcp",
        "version": "0.2.0",
        "features": "thread-safe storage, multi-client support, sqlite backend",
    }


@app.post("/api/import-mcp")
async def import_from_mcp(graph_data: dict[str, Any]) -> dict[str, Any]:
    """Import knowledge graph data directly into SQLite"""
    try:
        from .sqlite_backend import sqlite_knowledge_db

        if not graph_data.get("entities"):
            return {"status": "error", "message": "No entities provided"}

        imported_entities = 0
        imported_relations = 0
        timestamp = datetime.utcnow().isoformat()

        # Import entities
        entities = graph_data.get("entities", [])
        if entities:
            await sqlite_knowledge_db.create_entities(entities)
            imported_entities = len(entities)

        # Import relations
        relations = graph_data.get("relations", [])
        if relations:
            await sqlite_knowledge_db.create_relations(relations)
            imported_relations = len(relations)

        # Get updated stats
        stats = await sqlite_knowledge_db.get_stats()
        
        return {
            "status": "success",
            "message": "Data imported successfully",
            "imported_entities": imported_entities,
            "imported_relations": imported_relations,
            "database_stats": stats,
            "timestamp": timestamp,
        }

    except Exception as e:
        logger.error(f"Error importing data: {e}")
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}") from e
@app.get("/api/database-stats")
async def get_database_stats() -> dict[str, Any]:
    """Get SQLite database statistics"""
    try:
        from .sqlite_backend import sqlite_knowledge_db

        stats = await sqlite_knowledge_db.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get stats: {str(e)}"
        ) from e


def run_server(host: str = "localhost", port: int = 8080) -> None:
    """Run the server with uvicorn"""
    import uvicorn

    logger.info(f"Starting Knowledge Graph MCP Server v0.2.0 on {host}:{port}")
    logger.info("Features: Thread-safe storage, Multi-client support")
    uvicorn.run(app, host=host, port=port, log_level="info")


def run_stdio_server() -> None:
    """Run as a stdio MCP server (not recommended for production)"""
    import asyncio

    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import (
        CallToolResult,
        ListToolsResult,
        TextContent,
        Tool,
    )

    logger.warning("Running in STDIO mode - this may have file locking issues")

    # Create MCP server
    server: Server[Any, Any] = Server("memgraph")

    @server.list_tools()  # type: ignore[misc,no-untyped-call]
    async def list_tools() -> ListToolsResult:
        return ListToolsResult(
            tools=[
                Tool(
                    name="read_graph",
                    description="Read the entire knowledge graph",
                    inputSchema={"type": "object", "properties": {}},
                ),
                Tool(
                    name="search_nodes",
                    description="Search for nodes in the knowledge graph",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"}
                        },
                        "required": ["query"],
                    },
                ),
                Tool(
                    name="create_entities",
                    description="Create new entities",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "entities": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "entityType": {"type": "string"},
                                        "observations": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                    },
                                    "required": ["name", "entityType", "observations"],
                                },
                            }
                        },
                        "required": ["entities"],
                    },
                ),
                Tool(
                    name="create_relations",
                    description="Create new relations",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "relations": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "from": {"type": "string"},
                                        "to": {"type": "string"},
                                        "relationType": {"type": "string"},
                                    },
                                    "required": ["from", "to", "relationType"],
                                },
                            }
                        },
                        "required": ["relations"],
                    },
                ),
            ]
        )

    @server.call_tool()  # type: ignore[misc,no-untyped-call]
    async def call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
        try:
            if name == "read_graph":
                result = await knowledge_client.read_graph()
                return CallToolResult(
                    content=[
                        TextContent(type="text", text=json.dumps(result, indent=2))
                    ]
                )
            elif name == "search_nodes":
                result = await knowledge_client.search_nodes(arguments["query"])
                return CallToolResult(
                    content=[
                        TextContent(type="text", text=json.dumps(result, indent=2))
                    ]
                )
            elif name == "create_entities":
                await knowledge_client.create_entities(arguments["entities"])
                return CallToolResult(
                    content=[
                        TextContent(type="text", text="Entities created successfully")
                    ]
                )
            elif name == "create_relations":
                await knowledge_client.create_relations(arguments["relations"])
                return CallToolResult(
                    content=[
                        TextContent(type="text", text="Relations created successfully")
                    ]
                )
            else:
                raise ValueError(f"Unknown tool: {name}")
        except Exception as e:
            logger.error(f"Tool error: {e}")
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error: {str(e)}")],
                isError=True,
            )

    # Run the server
    async def main() -> None:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream, write_stream, server.create_initialization_options()
            )

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("STDIO server stopped")


if __name__ == "__main__":
    run_server()
