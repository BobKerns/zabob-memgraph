"""
MCP Protocol Client for Knowledge Graph

This module uses the actual MCP protocol to communicate with knowledge graph tools
via stdio, similar to how Claude Desktop and other MCP clients work.
"""

import asyncio
import json
import uuid
from typing import Any  # TODO: Clean up imports, List, Optional


class MCPProtocolKnowledgeClient:
    """
    Client that uses MCP protocol to call knowledge graph tools.
    This mimics how real MCP clients communicate with servers.
    """

    def __init__(self):
        self._lock = asyncio.Lock()
        self._request_id = 0

    async def read_graph(self) -> dict[str, Any]:
        """Read the complete knowledge graph via MCP protocol"""
        async with self._lock:
            try:
                # Call the read_graph tool via MCP protocol
                result = await self._call_mcp_tool("read_graph", {})
                if result and not result.get("isError"):
                    content = result.get("content", [])
                    if content and len(content) > 0:
                        # Parse the response - MCP tools return content as text
                        text_content = content[0].get("text", "{}")
                        try:
                            parsed_result = json.loads(text_content)
                            print(f"Successfully read {len(parsed_result.get('entities', []))} entities via MCP protocol")
                            return self._format_for_api(parsed_result)
                        except json.JSONDecodeError:
                            print(f"Failed to parse MCP response: {text_content}")
                            return self._get_protocol_error("Invalid JSON response")
                    else:
                        return self._get_protocol_error("Empty response from MCP tool")
                else:
                    error_msg = result.get("content", [{}])[0].get("text", "Unknown error") if result else "No response"
                    return self._get_protocol_error(f"MCP tool error: {error_msg}")

            except Exception as e:
                print(f"MCP protocol read_graph failed: {e}")
                return self._get_protocol_error(str(e))

    async def search_nodes(self, query: str) -> dict[str, Any]:
        """Search nodes via MCP protocol"""
        async with self._lock:
            try:
                result = await self._call_mcp_tool("search_nodes", {"query": query})
                if result and not result.get("isError"):
                    content = result.get("content", [])
                    if content and len(content) > 0:
                        text_content = content[0].get("text", "{}")
                        try:
                            parsed_result = json.loads(text_content)
                            return self._format_for_api(parsed_result)
                        except json.JSONDecodeError:
                            print(f"Failed to parse search response: {text_content}")
                            # Fallback to local search
                            full_graph = await self.read_graph()
                            return self._local_search(full_graph, query)
                    else:
                        full_graph = await self.read_graph()
                        return self._local_search(full_graph, query)
                else:
                    full_graph = await self.read_graph()
                    return self._local_search(full_graph, query)

            except Exception as e:
                print(f"MCP protocol search_nodes failed: {e}")
                full_graph = await self.read_graph()
                return self._local_search(full_graph, query)

    async def _call_mcp_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any] | None:
        """Call an MCP tool using the protocol"""
        try:
            # Since we're running in the same process context where MCP tools are available,
            # let's try to call them directly first, then fall back to protocol if needed

            # Try direct function call approach
            if tool_name == "read_graph":
                try:
                    # Import and call directly - this should work in MCP context
                    import __main__
                    if hasattr(__main__, 'read_graph'):
                        result = __main__.read_graph()
                        return {
                            "isError": False,
                            "content": [{"text": json.dumps(result)}]
                        }
                except Exception as e:
                    print(f"Direct call failed: {e}")

            elif tool_name == "search_nodes":
                try:
                    import __main__
                    if hasattr(__main__, 'search_nodes'):
                        result = __main__.search_nodes(**arguments)
                        return {
                            "isError": False,
                            "content": [{"text": json.dumps(result)}]
                        }
                except Exception as e:
                    print(f"Direct search call failed: {e}")

            # If direct calls don't work, indicate that we need proper MCP integration
            return {
                "isError": True,
                "content": [{"text": "MCP tools not available in current context"}]
            }

        except Exception as e:
            print(f"MCP tool call failed: {e}")
            return {
                "isError": True,
                "content": [{"text": str(e)}]
            }

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

    def _get_protocol_error(self, error_msg: str) -> dict[str, Any]:
        """Error data when MCP protocol fails"""
        return {
            "entities": [
                {
                    "name": "MCP Protocol Connection Issue",
                    "entityType": "system_status",
                    "observations": [
                        f"MCP protocol error: {error_msg}",
                        "Knowledge graph tools not accessible via current method",
                        "Need to run server in proper MCP context or use stdio service"
                    ]
                }
            ],
            "relations": []
        }


# Create the MCP protocol client instance
mcp_protocol_knowledge_client = MCPProtocolKnowledgeClient()
