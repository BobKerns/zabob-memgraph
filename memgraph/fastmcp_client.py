"""
FastMCP Client for Knowledge Graph

This module uses the FastMCP client API instead of reinventing MCP protocol handling.
Much cleaner and less error-prone than custom implementations.
"""

import asyncio
import json
from typing import Any

# Use standard MCP client for now (FastMCP coming later)
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


class FastMCPKnowledgeClient:
    """
    Knowledge graph client using FastMCP client API.

    This replaces all the custom MCP protocol implementations with a proper
    client library that handles the protocol details.
    """

    def __init__(self, server_command: list[str] | None = None) -> None:
        self._lock = asyncio.Lock()
        # Default to a more realistic MCP server command
        # You can override this when creating the client
        self.server_command = server_command or [
            "uv", "run", "/Users/rwk/p/zabob/mcp-server/src/zabob/mcp/server.py"
        ]
        # Initialize MCP client session (will connect on first use)
        self.session: ClientSession | None = None
        self._client_context: Any = None
        self._connected = False

    async def _ensure_connected(self) -> None:
        """Ensure the MCP client is connected"""
        if not self._connected and self.session is None:
            try:
                # Create stdio server parameters
                server_params = StdioServerParameters(
                    command=self.server_command[0],
                    args=self.server_command[1:] if len(self.server_command) > 1 else []
                )
                # Connect using stdio client - get the session properly
                self._client_context = stdio_client(server_params)
                read_stream, write_stream = await self._client_context.__aenter__()
                
                # Create the actual session
                from mcp.client.session import ClientSession
                self.session = ClientSession(read_stream, write_stream)
                await self.session.initialize()
                
                self._connected = True
                print(f"✅ MCP client connected to: {' '.join(self.server_command)}")
                
            except Exception as e:
                print(f"⚠️ MCP server unavailable ({e}), will use fallback data")
                # Don't set connected=True, so we'll use fallback methods
                raise

    async def read_graph(self) -> dict[str, Any]:
        """Read the complete knowledge graph via MCP client"""
        async with self._lock:
            try:
                await self._ensure_connected()
                if self.session is None:
                    raise RuntimeError("Failed to establish MCP session")
                
                # Call the read_graph tool
                result = await self.session.call_tool("read_graph", {})
                
                # Parse the result content
                if result.content and len(result.content) > 0:
                    content = result.content[0]
                    if hasattr(content, 'text'):
                        data = json.loads(content.text)
                        return self._format_for_api(data)
                
                return {"entities": [], "relations": []}

            except Exception as e:
                print(f"MCP read_graph failed: {e}")
                # Try to fall back to SQLite backend
                try:
                    from .sqlite_backend import sqlite_knowledge_db
                    print("🔄 Falling back to SQLite backend...")
                    return await sqlite_knowledge_db.read_graph()
                except Exception as fallback_error:
                    print(f"SQLite fallback also failed: {fallback_error}")
                    # Return error status as last resort
                    return self._get_fastmcp_error(str(e))

    async def search_nodes(self, query: str) -> dict[str, Any]:
        """Search nodes via MCP client"""
        async with self._lock:
            try:
                await self._ensure_connected()
                if self.session is None:
                    raise RuntimeError("Failed to establish MCP session")
                
                result = await self.session.call_tool("search_nodes", {"query": query})
                
                # Parse the result content
                if result.content and len(result.content) > 0:
                    content = result.content[0]
                    if hasattr(content, 'text'):
                        data = json.loads(content.text)
                        return self._format_for_api(data)
                
                return {"entities": [], "relations": []}

            except Exception as e:
                print(f"MCP search_nodes failed: {e}")
                # Try to fall back to SQLite backend
                try:
                    from .sqlite_backend import sqlite_knowledge_db
                    return await sqlite_knowledge_db.search_nodes(query)
                except Exception:
                    return {"entities": [], "relations": []}

    async def create_entities(self, entities: list[dict[str, Any]]) -> None:
        """Create entities via MCP client"""
        async with self._lock:
            await self._ensure_connected()
            if self.session is None:
                raise RuntimeError("Failed to establish MCP session")
            await self.session.call_tool("create_entities", {"entities": entities})

    async def create_relations(self, relations: list[dict[str, Any]]) -> None:
        """Create relations via MCP client"""
        async with self._lock:
            await self._ensure_connected()
            if self.session is None:
                raise RuntimeError("Failed to establish MCP session")
            await self.session.call_tool("create_relations", {"relations": relations})

    async def close(self) -> None:
        """Close the MCP client connection"""
        if self._connected and self.session is not None:
            # Close the session first
            await self.session.close()
            # Then close the client context
            if self._client_context is not None:
                await self._client_context.__aexit__(None, None, None)
                self._client_context = None
            self.session = None
            self._connected = False

    def _format_for_api(self, mcp_result: dict[str, Any]) -> dict[str, Any]:
        """Format MCP result for our API"""
        entities = []
        relations = []

        for entity_data in mcp_result.get("entities", []):
            entities.append(
                {
                    "name": entity_data["name"],
                    "entityType": entity_data["entityType"],
                    "observations": entity_data["observations"],
                }
            )

        for relation_data in mcp_result.get("relations", []):
            relations.append(
                {
                    "from_entity": relation_data["from"],
                    "to": relation_data["to"],
                    "relationType": relation_data["relationType"],
                }
            )

        return {"entities": entities, "relations": relations}

    def _local_search(self, graph_data: dict[str, Any], query: str) -> dict[str, Any]:
        """Local search implementation"""
        query_lower = query.lower()
        matching_entities = []

        for entity in graph_data["entities"]:
            if query_lower in entity["name"].lower():
                matching_entities.append(entity)
                continue

            for obs in entity["observations"]:
                if query_lower in obs.lower():
                    matching_entities.append(entity)
                    break

        entity_names = {e["name"] for e in matching_entities}
        matching_relations = [
            r
            for r in graph_data["relations"]
            if r["from_entity"] in entity_names or r["to"] in entity_names
        ]

        return {"entities": matching_entities, "relations": matching_relations}

    def _get_fastmcp_status(self) -> dict[str, Any]:
        """Status showing FastMCP integration plan"""
        return {
            "entities": [
                {
                    "name": "FastMCP Client Integration",
                    "entityType": "implementation_plan",
                    "observations": [
                        "FastMCP client approach is the correct long-term solution",
                        "Eliminates need for custom MCP protocol implementations",
                        "Provides clean, well-tested client API",
                        "Reduces maintenance burden and type checking complexity",
                        "Ready to implement once FastMCP client dependency is added",
                    ],
                },
                {
                    "name": "Current Custom Clients",
                    "entityType": "technical_debt",
                    "observations": [
                        "Multiple custom MCP clients with type checking issues",
                        "Reinventing protocol handling that FastMCP already provides",
                        "Complex error handling and response parsing",
                        "Should be replaced with FastMCP client calls",
                    ],
                },
                {
                    "name": "Migration Plan",
                    "entityType": "development_task",
                    "observations": [
                        "1. Add FastMCP client to dependencies in pyproject.toml",
                        "2. Replace server.py backend selection with FastMCPKnowledgeClient",
                        "3. Remove custom MCP client files (8 files total)",
                        "4. Implement tool calls using FastMCP client API",
                        "5. Test with actual MCP server integration",
                    ],
                },
            ],
            "relations": [
                {
                    "from_entity": "FastMCP Client Integration",
                    "to": "Current Custom Clients",
                    "relationType": "replaces",
                },
                {
                    "from_entity": "Migration Plan",
                    "to": "FastMCP Client Integration",
                    "relationType": "implements",
                },
            ],
        }

    def _get_fastmcp_error(self, error_msg: str) -> dict[str, Any]:
        """Error status for FastMCP issues"""
        return {
            "entities": [
                {
                    "name": "FastMCP Error",
                    "entityType": "system_status",
                    "observations": [
                        f"FastMCP client error: {error_msg}",
                        "This is the preferred MCP integration approach",
                        "Will be much cleaner than current custom implementations",
                    ],
                }
            ],
            "relations": [],
        }


# Create the FastMCP client instance
fastmcp_knowledge_client = FastMCPKnowledgeClient()
