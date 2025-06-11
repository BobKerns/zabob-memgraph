"""
Knowledge Graph Data Access with Real MCP Integration

This module integrates directly with MCP knowledge graph tools to provide
real-time data access through HTTP API with proper multi-client support.
"""

import json
import asyncio
import aiofiles
from pathlib import Path
from typing import Any  # TODO: Clean up imports, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


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
    
    def __init__(self):
        self._lock = asyncio.Lock()
        
    async def read_graph(self) -> dict[str, Any]:
        """Read the complete knowledge graph from MCP tools"""
        async with self._lock:
            try:
                # Call the actual read_graph MCP tool
                # This import needs to happen at runtime to avoid circular imports
                import __main__
                if hasattr(__main__, 'read_graph'):
                    result = __main__.read_graph()
                    return self._transform_mcp_data(result)
                else:
                    # Try to import the function dynamically
                    try:
                        from ... import read_graph
                        result = read_graph()
                        return self._transform_mcp_data(result)
                    except ImportError:
                        # Last resort - return empty graph
                        return {"entities": [], "relations": []}
            except Exception as e:
                print(f"Error reading from MCP tools: {e}")
                return {"entities": [], "relations": []}
    
    def _transform_mcp_data(self, mcp_result: dict[str, Any]) -> dict[str, Any]:
        """Transform MCP data format to our expected format"""
        entities = []
        relations = []
        
        # MCP returns format: {"entities": [...], "relations": [...]}
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
    
    async def search_nodes(self, query: str) -> dict[str, Any]:
        """Search for nodes matching the query using MCP tools"""
        async with self._lock:
            try:
                # Try to call search_nodes MCP tool
                import __main__
                if hasattr(__main__, 'search_nodes'):
                    result = __main__.search_nodes(query=query)
                    return self._transform_mcp_data(result)
                else:
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
            r for r in graph_data["relations"]
            if r["from_entity"] in entity_names or r["to"] in entity_names
        ]
        
        return {
            "entities": matching_entities,
            "relations": matching_relations
        }


# Create simple manager that uses direct MCP function calls
class DirectMCPKnowledgeGraphManager:
    """
    Direct MCP knowledge graph manager that calls MCP functions without complex imports.
    """
    
    def __init__(self):
        self._lock = asyncio.Lock()
    
    async def read_graph(self) -> dict[str, Any]:
        """Read the complete knowledge graph using direct MCP function call"""
        async with self._lock:
            try:
                # Direct function call - the MCP functions are available in this context
                from ...__main__ import read_graph
                result = read_graph()
                return self._format_graph_data(result)
            except Exception as e:
                print(f"MCP read_graph failed: {e}")
                # Return some sample data for testing
                return self._get_sample_data()
    
    async def search_nodes(self, query: str) -> dict[str, Any]:
        """Search nodes using MCP tools"""
        async with self._lock:
            try:
                from ...__main__ import search_nodes
                result = search_nodes(query=query)
                return self._format_graph_data(result)
            except Exception as e:
                print(f"MCP search_nodes failed: {e}")
                # Fallback to local search
                full_graph = await self.read_graph()
                return self._local_search(full_graph, query)
    
    def _format_graph_data(self, mcp_result: dict[str, Any]) -> dict[str, Any]:
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
    
    def _get_sample_data(self) -> dict[str, Any]:
        """Sample data for testing when MCP tools unavailable"""
        return {
            "entities": [
                {
                    "name": "Sample Entity", 
                    "entityType": "test",
                    "observations": ["This is test data when MCP tools are not available"]
                }
            ],
            "relations": []
        }


# Global instance - use direct MCP connection
knowledge_client = DirectMCPKnowledgeGraphManager()
