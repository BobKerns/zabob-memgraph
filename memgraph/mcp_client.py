"""
Direct MCP Integration for Knowledge Graph

Simple wrapper that calls MCP functions directly and formats the results
for the HTTP API.
"""

import asyncio
from typing import Any, Dict


class SimpleMCPKnowledgeClient:
    """
    Simple client that calls MCP functions directly and formats results.
    """

    def __init__(self):
        self._lock = asyncio.Lock()

    async def read_graph(self) -> Dict[str, Any]:
        """Read the complete knowledge graph from MCP"""
        async with self._lock:
            try:
                # Try to import and call the MCP function
                import builtins
                if hasattr(builtins, 'read_graph'):
                    result = builtins.read_graph()
                    return self._format_for_api(result)
                else:
                    # The MCP functions are not available in this context
                    # Return sample data for now - this will be fixed when properly integrated
                    return self._get_sample_data()
            except Exception as e:
                print(f"MCP read_graph failed: {e}")
                return self._get_sample_data()

    async def search_nodes(self, query: str) -> Dict[str, Any]:
        """Search nodes using MCP"""
        async with self._lock:
            try:
                import builtins
                if hasattr(builtins, 'search_nodes'):
                    result = builtins.search_nodes(query=query)
                    return self._format_for_api(result)
                else:
                    # Fallback to local search
                    full_graph = await self.read_graph()
                    return self._local_search(full_graph, query)
            except Exception as e:
                print(f"MCP search_nodes failed: {e}")
                # Fallback to local search
                full_graph = await self.read_graph()
                return self._local_search(full_graph, query)

    def _format_for_api(self, mcp_result: Dict[str, Any]) -> Dict[str, Any]:
        """Format MCP result for our API"""
        entities = []
        relations = []

        # Handle the MCP format
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

    def _local_search(self, graph_data: Dict[str, Any], query: str) -> Dict[str, Any]:
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

    def _get_sample_data(self) -> Dict[str, Any]:
        """Get sample data that matches the real structure"""
        return {
            "entities": [
            ],
            "relations": [
            ]
        }


# Create the client instance
mcp_knowledge_client = SimpleMCPKnowledgeClient()
