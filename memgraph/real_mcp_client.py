"""
Real MCP Integration for Knowledge Graph

This module calls the actual MCP knowledge graph functions and integrates
the results into the HTTP server.
"""

import asyncio
from typing import Any  # TODO: Clean up imports


class RealMCPKnowledgeClient:
    """
    Client that calls real MCP knowledge graph functions.
    """

    def __init__(self):
        self._lock = asyncio.Lock()

    async def read_graph(self) -> dict[str, Any]:
        """Read the complete knowledge graph from real MCP tools"""
        async with self._lock:
            try:
                # Call the real read_graph function that's available in this execution context
                result = read_graph()
                print(f"Successfully read {len(result.get('entities', []))} entities from MCP")
                return self._format_for_api(result)
            except NameError:
                print("read_graph function not available - MCP tools not in scope")
                return self._get_fallback_data()
            except Exception as e:
                print(f"Error calling read_graph: {e}")
                return self._get_fallback_data()

    async def search_nodes(self, query: str) -> dict[str, Any]:
        """Search nodes using real MCP tools"""
        async with self._lock:
            try:
                result = search_nodes(query=query)
                return self._format_for_api(result)
            except NameError:
                print("search_nodes function not available - using local search")
                # Fallback to local search
                full_graph = await self.read_graph()
                return self._local_search(full_graph, query)
            except Exception as e:
                print(f"Error calling search_nodes: {e}")
                full_graph = await self.read_graph()
                return self._local_search(full_graph, query)

    def _format_for_api(self, mcp_result: dict[str, Any]) -> dict[str, Any]:
        """Format MCP result for our API"""
        entities = []
        relations = []

        # Handle the MCP format - entities and relations are in the result
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
        """Local search fallback"""
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

    def _get_fallback_data(self) -> dict[str, Any]:
        """Fallback data when MCP not available"""
        return {
            "entities": [
                {
                    "name": "MCP Connection Issue",
                    "entityType": "system_status",
                    "observations": [
                        "MCP knowledge graph functions not available in current context",
                        "This indicates the server is not running in the same process as MCP tools",
                        "Need to properly integrate MCP function access"
                    ]
                }
            ],
            "relations": []
        }


# Create the real MCP client instance
real_mcp_knowledge_client = RealMCPKnowledgeClient()
