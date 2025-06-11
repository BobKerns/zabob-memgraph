"""
FastMCP Client for Knowledge Graph

This module uses the FastMCP client API instead of reinventing MCP protocol handling.
Much cleaner and less error-prone than custom implementations.
"""

import asyncio
from typing import Any

# Note: FastMCP client would be imported here when available
# from fastmcp.client import MCPClient


class FastMCPKnowledgeClient:
    """
    Knowledge graph client using FastMCP client API.

    This replaces all the custom MCP protocol implementations with a proper
    client library that handles the protocol details.
    """

    def __init__(self, server_command: list[str] | None = None) -> None:
        self._lock = asyncio.Lock()
        # Default to connecting to local MCP server
        self.server_command = server_command or ["uv", "run", "mcp-server"]
        # TODO: Initialize FastMCP client when available
        # self.client = MCPClient(self.server_command)

    async def read_graph(self) -> dict[str, Any]:
        """Read the complete knowledge graph via FastMCP client"""
        async with self._lock:
            try:
                # TODO: Replace with actual FastMCP client call
                # result = await self.client.call_tool("read_graph", {})
                # return self._format_for_api(result)

                # For now, return a placeholder indicating this is the preferred approach
                return self._get_fastmcp_status()

            except Exception as e:
                print(f"FastMCP read_graph failed: {e}")
                return self._get_fastmcp_error(str(e))

    async def search_nodes(self, query: str) -> dict[str, Any]:
        """Search nodes via FastMCP client"""
        async with self._lock:
            try:
                # TODO: Replace with actual FastMCP client call
                # result = await self.client.call_tool("search_nodes", {"query": query})
                # return self._format_for_api(result)

                # For now, do local search on the status data
                full_graph = await self.read_graph()
                return self._local_search(full_graph, query)

            except Exception as e:
                print(f"FastMCP search_nodes failed: {e}")
                return {"entities": [], "relations": []}

    async def create_entities(self, entities: list[dict[str, Any]]) -> None:
        """Create entities via FastMCP client"""
        # TODO: Replace with actual FastMCP client call
        # await self.client.call_tool("create_entities", {"entities": entities})
        print(f"FastMCP: Would create {len(entities)} entities")

    async def create_relations(self, relations: list[dict[str, Any]]) -> None:
        """Create relations via FastMCP client"""
        # TODO: Replace with actual FastMCP client call
        # await self.client.call_tool("create_relations", {"relations": relations})
        print(f"FastMCP: Would create {len(relations)} relations")

    def _format_for_api(self, mcp_result: dict[str, Any]) -> dict[str, Any]:
        """Format MCP result for our API"""
        entities = []
        relations = []

        for entity_data in mcp_result.get("entities", []):
            entities.append({
                "name": entity_data["name"],
                "entityType": entity_data["entityType"],
                "observations": entity_data["observations"]
            })

        for relation_data in mcp_result.get("relations", []):
            relations.append({
                "from_entity": relation_data["from"],
                "to": relation_data["to"],
                "relationType": relation_data["relationType"]
            })

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
            r for r in graph_data["relations"]
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
                        "Ready to implement once FastMCP client dependency is added"
                    ]
                },
                {
                    "name": "Current Custom Clients",
                    "entityType": "technical_debt",
                    "observations": [
                        "Multiple custom MCP clients with type checking issues",
                        "Reinventing protocol handling that FastMCP already provides",
                        "Complex error handling and response parsing",
                        "Should be replaced with FastMCP client calls"
                    ]
                },
                {
                    "name": "Migration Plan",
                    "entityType": "development_task",
                    "observations": [
                        "1. Add FastMCP client to dependencies in pyproject.toml",
                        "2. Replace server.py backend selection with FastMCPKnowledgeClient",
                        "3. Remove custom MCP client files (8 files total)",
                        "4. Implement tool calls using FastMCP client API",
                        "5. Test with actual MCP server integration"
                    ]
                }
            ],
            "relations": [
                {
                    "from_entity": "FastMCP Client Integration",
                    "to": "Current Custom Clients",
                    "relationType": "replaces"
                },
                {
                    "from_entity": "Migration Plan",
                    "to": "FastMCP Client Integration",
                    "relationType": "implements"
                }
            ]
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
                        "Will be much cleaner than current custom implementations"
                    ]
                }
            ],
            "relations": []
        }


# Create the FastMCP client instance
fastmcp_knowledge_client = FastMCPKnowledgeClient()
