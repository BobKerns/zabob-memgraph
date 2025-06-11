"""
Subprocess MCP Integration for Knowledge Graph

This module calls MCP tools via subprocess stdio, similar to how
Docker containers or other MCP servers are invoked.
"""

import asyncio
import json
import subprocess
import sys
from typing import Any, Dict, List, Optional


class SubprocessMCPKnowledgeClient:
    """
    Client that calls MCP knowledge graph functions via subprocess stdio.
    Similar to how Docker MCP containers are invoked.
    """
    
    def __init__(self):
        self._lock = asyncio.Lock()
        # We'll call the MCP tools that are available in this environment
        # For now, we can try calling them via subprocess python execution
    
    async def read_graph(self) -> Dict[str, Any]:
        """Read the complete knowledge graph via subprocess MCP call"""
        async with self._lock:
            try:
                # Method 1: Try calling as a subprocess python script
                result = await self._call_mcp_function("read_graph", {})
                if result:
                    print(f"Successfully read {len(result.get('entities', []))} entities via subprocess MCP")
                    return self._format_for_api(result)
                else:
                    return self._get_connection_error()
                    
            except Exception as e:
                print(f"Subprocess MCP read_graph failed: {e}")
                return self._get_connection_error()
    
    async def search_nodes(self, query: str) -> Dict[str, Any]:
        """Search nodes via subprocess MCP call"""  
        async with self._lock:
            try:
                result = await self._call_mcp_function("search_nodes", {"query": query})
                if result:
                    return self._format_for_api(result)
                else:
                    # Fallback to local search
                    full_graph = await self.read_graph()
                    return self._local_search(full_graph, query)
                    
            except Exception as e:
                print(f"Subprocess MCP search_nodes failed: {e}")
                full_graph = await self.read_graph()
                return self._local_search(full_graph, query)
    
    async def _call_mcp_function(self, function_name: str, args: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Call an MCP function via subprocess"""
        try:
            # Create a Python script that imports and calls the MCP function
            script = f'''
import sys
import json

try:
    # Try to import the MCP functions from the global context
    # This simulates how they would be available in an MCP server
    from __main__ import {function_name}
    
    # Call the function with args
    args = {json.dumps(args)}
    if args:
        result = {function_name}(**args)
    else:
        result = {function_name}()
    
    # Return the result as JSON
    print(json.dumps(result))
    
except ImportError as e:
    print(json.dumps({{"error": "MCP function not available", "details": str(e)}}), file=sys.stderr)
except Exception as e:
    print(json.dumps({{"error": "MCP function failed", "details": str(e)}}), file=sys.stderr)
'''
            
            # Run the script as a subprocess
            process = await asyncio.create_subprocess_exec(
                sys.executable, "-c", script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0 and stdout:
                result = json.loads(stdout.decode())
                if "error" not in result:
                    return result
                else:
                    print(f"MCP function error: {result}")
                    return None
            else:
                if stderr:
                    print(f"Subprocess stderr: {stderr.decode()}")
                return None
                
        except Exception as e:
            print(f"Subprocess execution failed: {e}")
            return None
    
    def _format_for_api(self, mcp_result: Dict[str, Any]) -> Dict[str, Any]:
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
    
    def _get_connection_error(self) -> Dict[str, Any]:
        """Error data when subprocess MCP fails"""
        return {
            "entities": [
                {
                    "name": "Subprocess MCP Connection Issue",
                    "entityType": "system_status",
                    "observations": [
                        "MCP functions not accessible via subprocess",
                        "Need to configure proper MCP stdio service",
                        "Consider using Docker or dedicated MCP server approach"
                    ]
                }
            ],
            "relations": []
        }


# Create the subprocess MCP client instance
subprocess_mcp_knowledge_client = SubprocessMCPKnowledgeClient()
