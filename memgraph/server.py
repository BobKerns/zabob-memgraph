"""
MCP HTTP Server for Knowledge Graph

Provides both MCP protocol support and HTTP REST endpoints for knowledge graph data.
Serves the D3.js visualization client as static files.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

# Knowledge graph data storage (in production, this would connect to actual MCP tools)
SAMPLE_KNOWLEDGE_GRAPH = {
    "entities": [
        {
            "name": "Hiromi",
            "entityType": "person",
            "observations": ["User's wife"]
        },
        {
            "name": "Bob", 
            "entityType": "person",
            "observations": ["The person I'm talking with"]
        },
        {
            "name": "Zabob Project",
            "entityType": "project",
            "observations": [
                "AI MCP-based agent to make Houdini accessible to AIs for assistance",
                "Has database of Python modules and routines available within Houdini",
                "Has database of all node types and parameters that ship with Houdini",
                "Currently transitioning from setup phase to delivering real data",
                "Uses MCP (Model Context Protocol) architecture"
            ]
        },
        {
            "name": "Knowledge Graph Visualization System",
            "entityType": "visualization tool", 
            "observations": [
                "Interactive D3.js-based knowledge graph visualization",
                "HTTP-based architecture for unlimited scalability",
                "Real-time data updates without page refresh",
                "Full-text search across all content"
            ]
        }
    ],
    "relations": [
        {"from": "Bob", "to": "Hiromi", "relationType": "is married to"},
        {"from": "Hiromi", "to": "Bob", "relationType": "is married to"},
        {"from": "Bob", "to": "Zabob Project", "relationType": "created"},
        {"from": "Knowledge Graph Visualization System", "to": "Zabob Project", "relationType": "visualizes"}
    ]
}

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Knowledge Graph MCP Server",
    description="HTTP interface for knowledge graph visualization",
    version="0.1.0"
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
            <h1>Knowledge Graph MCP Server</h1>
            <p>Web client not found. Check that memgraph/web/index.html exists.</p>
            <p>API endpoints:</p>
            <ul>
                <li><a href="/api/knowledge-graph">/api/knowledge-graph</a> - Full graph data</li>
                <li><a href="/api/entities">/api/entities</a> - All entities</li>
                <li><a href="/api/search?q=test">/api/search?q=test</a> - Search</li>
                <li><a href="/docs">/docs</a> - API documentation</li>
            </ul>
        </body>
    </html>
    """)

@app.get("/api/knowledge-graph")
async def get_knowledge_graph() -> Dict[str, Any]:
    """Get the complete knowledge graph data"""
    # Transform to the format expected by the D3 visualization
    nodes = []
    for entity in SAMPLE_KNOWLEDGE_GRAPH["entities"]:
        # Map entity types to visualization groups
        group = "person" if entity["entityType"] == "person" else \
               "project" if entity["entityType"] == "project" else \
               "technology"
        
        nodes.append({
            "id": entity["name"],
            "group": group,
            "type": entity["entityType"],
            "observations": entity["observations"]
        })
    
    links = []
    for relation in SAMPLE_KNOWLEDGE_GRAPH["relations"]:
        links.append({
            "source": relation["from"],
            "target": relation["to"],
            "relation": relation["relationType"]
        })
    
    return {
        "nodes": nodes,
        "links": links,
        "stats": {
            "entityCount": len(nodes),
            "relationCount": len(links)
        }
    }

@app.get("/api/entities")
async def get_entities() -> List[Dict[str, Any]]:
    """Get all entities"""
    return SAMPLE_KNOWLEDGE_GRAPH["entities"]

@app.get("/api/search")
async def search_knowledge_graph(q: str) -> List[Dict[str, Any]]:
    """Search across all entities and observations"""
    if not q or len(q.strip()) < 2:
        return []
    
    query = q.lower().strip()
    results = []
    
    for entity in SAMPLE_KNOWLEDGE_GRAPH["entities"]:
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

@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint"""
    return {"status": "healthy", "service": "knowledge-graph-mcp"}

def run_server(host: str = "localhost", port: int = 8080) -> None:
    """Run the server with uvicorn"""
    import uvicorn
    logger.info(f"Starting Knowledge Graph MCP Server on {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")

if __name__ == "__main__":
    run_server()
