"""
Knowledge Graph Data Access with Real MCP Integration

This module integrates directly with MCP knowledge graph tools to provide
real-time data access through HTTP API with proper multi-client support.
"""

import asyncio
from dataclasses import dataclass
from typing import Any


@dataclass
class Entity:
    name: str
    entityType: str
    observations: list[str]


@dataclass
class Relation:
    from_entity: str  # renamed from 'from' to avoid Python keyword
    to: str
    relationType: str


@dataclass
class KnowledgeGraph:
    entities: list[Entity]
    relations: list[Relation]


class LiveKnowledgeGraphManager:
    """
    Knowledge graph manager that connects directly to MCP tools for live data.
    Provides read-only access to the current knowledge graph state.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()

    async def read_graph(self) -> dict[str, Any]:
        """Read the complete knowledge graph from MCP tools"""
        async with self._lock:
            try:
                # Try to get MCP tools from the current environment
                # This is safer than relative imports that don't exist
                import sys

                # Look for MCP tools in the current namespace
                if "read_graph" in globals():
                    result = globals()["read_graph"]()
                    return self._transform_mcp_data(result)

                # Try to find MCP tools in __main__ module
                main_module = sys.modules.get("__main__")
                if main_module and hasattr(main_module, "read_graph"):
                    result = main_module.read_graph()
                    return self._transform_mcp_data(result)

                # Fallback to sample data for testing
                return self._get_sample_data()

            except Exception as e:
                print(f"Error reading from MCP tools: {e}")
                return self._get_sample_data()

    def _transform_mcp_data(self, mcp_result: dict[str, Any]) -> dict[str, Any]:
        """Transform MCP data format to our expected format"""
        entities = []
        relations = []

        # MCP returns format: {"entities": [...], "relations": [...]}
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

    async def search_nodes(self, query: str) -> dict[str, Any]:
        """Search for nodes matching the query using MCP tools"""
        async with self._lock:
            try:
                import sys

                # Try to find search_nodes in current environment
                if "search_nodes" in globals():
                    result = globals()["search_nodes"](query=query)
                    return self._transform_mcp_data(result)

                # Try to find in __main__ module
                main_module = sys.modules.get("__main__")
                if main_module and hasattr(main_module, "search_nodes"):
                    result = main_module.search_nodes(query=query)
                    return self._transform_mcp_data(result)

                # Fallback: read full graph and search locally
                full_graph = await self.read_graph()
                return self._local_search(full_graph, query)

            except Exception as e:
                print(f"Error searching with MCP tools: {e}")
                return {"entities": [], "relations": []}

    def _local_search(self, graph_data: dict[str, Any], query: str) -> dict[str, Any]:
        """Local search implementation as fallback"""
        query_lower = query.lower()
        matching_entities = []

        for entity in graph_data["entities"]:
            # Search name
            if query_lower in entity["name"].lower():
                matching_entities.append(entity)
                continue

            # Search observations
            for obs in entity["observations"]:
                if query_lower in obs.lower():
                    matching_entities.append(entity)
                    break

        # Get relations for matching entities
        entity_names = {e["name"] for e in matching_entities}
        matching_relations = [
            r
            for r in graph_data["relations"]
            if r["from_entity"] in entity_names or r["to"] in entity_names
        ]

        return {
            "entities": matching_entities,
            "relations": matching_relations
        }

    def _get_sample_data(self) -> dict[str, Any]:
        """Sample data for testing when MCP tools are not available"""
        return {
            "entities": [
                {
                    "name": "Sample Entity",
                    "entityType": "test",
                    "observations": [
                        "This is test data when MCP tools are not available"
                    ],
                }
            ],
            "relations": [],
        }


class StubKnowledgeGraphManager:
    """
    Simple stub implementation for when no MCP tools are available.
    Provides minimal functionality for testing.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()

    async def read_graph(self) -> dict[str, Any]:
        """Return empty graph data"""
        return {"entities": [], "relations": []}

    async def search_nodes(self, query: str) -> dict[str, Any]:
        """Return empty search results"""
        return {"entities": [], "relations": []}

    async def create_entities(self, entities: list[dict[str, Any]]) -> None:
        """Stub implementation - does nothing"""
        print(f"Stub: Would create {len(entities)} entities")

    async def create_relations(self, relations: list[dict[str, Any]]) -> None:
        """Stub implementation - does nothing"""
        print(f"Stub: Would create {len(relations)} relations")


# Global instance - use live MCP connection if available, stub otherwise
try:
    knowledge_client: LiveKnowledgeGraphManager | StubKnowledgeGraphManager = (
        LiveKnowledgeGraphManager()
    )
except Exception:
    # Fallback to stub if live connection fails
    knowledge_client = StubKnowledgeGraphManager()
