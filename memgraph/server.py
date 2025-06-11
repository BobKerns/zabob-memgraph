"""
MCP HTTP Server for Knowledge Graph

Provides both MCP protocol support and HTTP REST endpoints for knowledge graph data.
Integrates with thread-safe knowledge graph storage to prevent multi-client issues.
"""

import json
import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

# Set up logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try different knowledge graph backends in order of preference
try:
    from .sqlite_backend import sqlite_knowledge_db as knowledge_client
    logger.info("Using SQLite database backend")
except (ImportError, Exception) as e:
    try:
        from .docker_mcp_client import docker_mcp_knowledge_client as knowledge_client
        logger.info("Using Docker MCP client for live data")
    except (ImportError, Exception) as e:
        try:
            from .stdio_mcp_client import stdio_mcp_knowledge_client as knowledge_client
            logger.info("Using stdio MCP client for live data")
        except (ImportError, NameError) as e:
            try:
                from .simple_mcp_bridge import simple_mcp_bridge as knowledge_client
                logger.info("Using simple MCP bridge for live data")
            except (ImportError, NameError) as e:
                try:
                    from .real_mcp_client import real_mcp_knowledge_client as knowledge_client
                    logger.info("Using real MCP integration for live data")
                except (ImportError, NameError) as e:
                    try:
                        from .mcp_client import mcp_knowledge_client as knowledge_client
                        logger.info("Using direct MCP integration for live data")
                    except ImportError:
                        from .knowledge import knowledge_client
                        logger.info("Using file-based storage as fallback")

# Create FastAPI app
app = FastAPI(
    title="Knowledge Graph MCP Server",
    description="HTTP interface for knowledge graph visualization with thread-safe multi-client support",
    version="0.2.0"
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
        return FileResponse(web_file)
    return HTMLResponse("""
    <html>
        <head><title>Knowledge Graph</title></head>
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
    """)

@app.get("/api/knowledge-graph")
async def get_knowledge_graph() -> dict[str, Any]:
    """Get the complete knowledge graph data with thread-safe access"""
    try:
        graph_data = await knowledge_client.read_graph()
        
        # Transform to D3 visualization format
        nodes = []
        for entity in graph_data["entities"]:
            # Map entity types to visualization groups
            group = "person" if entity["entityType"] == "person" else \
                   "project" if entity["entityType"] == "project" else \
                   "development" if "development" in entity["entityType"].lower() else \
                   "strategy" if "strategy" in entity["entityType"].lower() or "plan" in entity["entityType"].lower() else \
                   "debug" if "debug" in entity["entityType"].lower() or "investigation" in entity["entityType"].lower() else \
                   "technology"
            
            nodes.append({
                "id": entity["name"],
                "group": group,
                "type": entity["entityType"],
                "observations": entity["observations"]
            })
        
        links = []
        for relation in graph_data["relations"]:
            links.append({
                "source": relation["from_entity"],
                "target": relation["to"],
                "relation": relation["relationType"]
            })
        
        return {
            "nodes": nodes,
            "links": links,
            "stats": {
                "entityCount": len(nodes),
                "relationCount": len(links),
                "dataSource": "thread-safe file storage"
            }
        }
    except Exception as e:
        logger.error(f"Error reading knowledge graph: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to read knowledge graph: {str(e)}")

@app.get("/api/entities")
async def get_entities() -> list[dict[str, Any]]:
    """Get all entities with thread-safe access"""
    try:
        graph_data = await knowledge_client.read_graph()
        return graph_data["entities"]
    except Exception as e:
        logger.error(f"Error reading entities: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to read entities: {str(e)}")

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
                results.append({
                    "entity": entity["name"],
                    "type": "name",
                    "content": entity["name"],
                    "entityType": entity["entityType"],
                    "score": 10
                })
            
            # Search observations
            for i, obs in enumerate(entity["observations"]):
                if query in obs.lower():
                    results.append({
                        "entity": entity["name"],
                        "type": "observation", 
                        "content": obs,
                        "entityType": entity["entityType"],
                        "observationIndex": i,
                        "score": 5
                    })
        
        # Sort by score (descending)
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:20]  # Limit results
        
    except Exception as e:
        logger.error(f"Error searching knowledge graph: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.post("/api/entities")
async def create_entities(entities: list[dict[str, Any]]) -> dict[str, str]:
    """Create new entities with thread-safe access"""
    try:
        await knowledge_client.create_entities(entities)
        return {"status": "success", "message": f"Created {len(entities)} entities"}
    except Exception as e:
        logger.error(f"Error creating entities: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create entities: {str(e)}")

@app.post("/api/relations") 
async def create_relations(relations: list[dict[str, Any]]) -> dict[str, str]:
    """Create new relations with thread-safe access"""
    try:
        await knowledge_client.create_relations(relations)
        return {"status": "success", "message": f"Created {len(relations)} relations"}
    except Exception as e:
        logger.error(f"Error creating relations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create relations: {str(e)}")

@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "service": "knowledge-graph-mcp",
        "version": "0.2.0",
        "features": ["thread-safe storage", "multi-client support", "sqlite backend"]
    }

@app.post("/api/import-mcp")
async def import_from_mcp() -> dict[str, Any]:
    """Import knowledge graph data from MCP tools into SQLite"""
    try:
        from .sqlite_backend import sqlite_knowledge_db
        
        # Try different MCP clients in order of preference
        mcp_client = None
        client_name = "unknown"
        
        try:
            from .docker_mcp_client import docker_mcp_knowledge_client
            mcp_client = docker_mcp_knowledge_client
            client_name = "Docker MCP"
        except ImportError:
            try:
                from .stdio_mcp_client import stdio_mcp_knowledge_client
                mcp_client = stdio_mcp_knowledge_client
                client_name = "Stdio MCP"
            except ImportError:
                try:
                    from .simple_mcp_bridge import simple_mcp_bridge
                    mcp_client = simple_mcp_bridge
                    client_name = "Simple MCP Bridge"
                except ImportError:
                    return {
                        "status": "error",
                        "message": "No MCP client available for import"
                    }
        
        result = await sqlite_knowledge_db.import_from_mcp(mcp_client)
        
        if result["status"] == "success":
            # Get updated stats
            stats = await sqlite_knowledge_db.get_stats()
            return {
                "status": "success",
                "message": f"MCP data imported successfully from {client_name}",
                "imported_entities": result["imported_entities"],
                "imported_relations": result["imported_relations"],
                "database_stats": stats,
                "source_client": client_name
            }
        else:
            return {
                "status": "error",
                "message": result["message"],
                "source_client": client_name
            }
    except Exception as e:
        logger.error(f"Error importing from MCP: {e}")
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")
@app.get("/api/database-stats")
async def get_database_stats() -> dict[str, Any]:
    """Get SQLite database statistics"""
    try:
        from .sqlite_backend import sqlite_knowledge_db
        stats = await sqlite_knowledge_db.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

def run_server(host: str = "localhost", port: int = 8080) -> None:
    """Run the server with uvicorn"""
    import uvicorn
    logger.info(f"Starting Knowledge Graph MCP Server v0.2.0 on {host}:{port}")
    logger.info("Features: Thread-safe storage, Multi-client support")
    uvicorn.run(app, host=host, port=port, log_level="info")

def run_stdio_server() -> None:
    """Run as a stdio MCP server (not recommended for production)"""
    import asyncio
    import json
    import sys
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import (
        Tool,
        TextContent,
        CallToolResult,
        ListToolsResult,
    )
    
    logger.warning("Running in STDIO mode - this may have file locking issues")
    
    # Create MCP server
    server = Server("memgraph")
    
    @server.list_tools()
    async def list_tools() -> ListToolsResult:
        return ListToolsResult(
            tools=[
                Tool(
                    name="read_graph",
                    description="Read the entire knowledge graph",
                    inputSchema={"type": "object", "properties": {}}
                ),
                Tool(
                    name="search_nodes", 
                    description="Search for nodes in the knowledge graph",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"}
                        },
                        "required": ["query"]
                    }
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
                                        "observations": {"type": "array", "items": {"type": "string"}}
                                    },
                                    "required": ["name", "entityType", "observations"]
                                }
                            }
                        },
                        "required": ["entities"]
                    }
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
                                        "relationType": {"type": "string"}
                                    },
                                    "required": ["from", "to", "relationType"]
                                }
                            }
                        },
                        "required": ["relations"]
                    }
                )
            ]
        )
    
    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
        try:
            if name == "read_graph":
                result = await knowledge_client.read_graph()
                return CallToolResult(content=[TextContent(type="text", text=json.dumps(result, indent=2))])
            elif name == "search_nodes":
                result = await knowledge_client.search_nodes(arguments["query"])
                return CallToolResult(content=[TextContent(type="text", text=json.dumps(result, indent=2))])
            elif name == "create_entities":
                await knowledge_client.create_entities(arguments["entities"])
                return CallToolResult(content=[TextContent(type="text", text="Entities created successfully")])
            elif name == "create_relations":
                await knowledge_client.create_relations(arguments["relations"])
                return CallToolResult(content=[TextContent(type="text", text="Relations created successfully")])
            else:
                raise ValueError(f"Unknown tool: {name}")
        except Exception as e:
            logger.error(f"Tool error: {e}")
            return CallToolResult(content=[TextContent(type="text", text=f"Error: {str(e)}")], isError=True)
    
    # Run the server
    async def main():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("STDIO server stopped")

if __name__ == "__main__":
    run_server()
