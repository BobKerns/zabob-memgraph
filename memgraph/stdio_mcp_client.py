"""
Stdio MCP Client for Knowledge Graph

This module implements proper MCP protocol communication via stdio,
similar to how Docker containers and other MCP servers are invoked.
"""

import asyncio
import json
import uuid
from typing import Any


class StdioMCPKnowledgeClient:
    """
    Client that uses MCP protocol over stdio to communicate with knowledge graph tools.
    Follows the same pattern as Docker MCP containers.
    """

    def __init__(self, command: list[str] | None = None):
        self._lock = asyncio.Lock()
        self._request_id = 0
        # Default to calling MCP tools in current Python environment
        # Can be overridden for Docker containers or other stdio services
        self.command = command or ["python", "-c", """
import sys
import json

# MCP protocol handler
def handle_mcp_request():
    try:
        for line in sys.stdin:
            request = json.loads(line.strip())

            if request.get('method') == 'tools/call':
                tool_name = request['params']['name']
                arguments = request['params'].get('arguments', {})

                # Import and call the actual MCP functions
                if tool_name == 'read_graph':
                    from __main__ import read_graph
                    result = read_graph()
                    response = {
                        'jsonrpc': '2.0',
                        'id': request['id'],
                        'result': {
                            'content': [{'type': 'text', 'text': json.dumps(result)}]
                        }
                    }
                elif tool_name == 'search_nodes':
                    from __main__ import search_nodes
                    result = search_nodes(**arguments)
                    response = {
                        'jsonrpc': '2.0',
                        'id': request['id'],
                        'result': {
                            'content': [{'type': 'text', 'text': json.dumps(result)}]
                        }
                    }
                else:
                    response = {
                        'jsonrpc': '2.0',
                        'id': request['id'],
                        'error': {'code': -32601, 'message': f'Tool {tool_name} not found'}
                    }

                print(json.dumps(response))
                sys.stdout.flush()

    except Exception as e:
        response = {
            'jsonrpc': '2.0',
            'id': request.get('id', 1),
            'error': {'code': -32603, 'message': str(e)}
        }
        print(json.dumps(response))
        sys.stdout.flush()

if __name__ == '__main__':
    handle_mcp_request()
"""]

    async def read_graph(self) -> dict[str, Any]:
        """Read the complete knowledge graph via stdio MCP"""
        async with self._lock:
            try:
                result = await self._call_mcp_tool("read_graph", {})
                if result and not result.get("error"):
                    content = result.get("content", [])
                    if content and len(content) > 0:
                        text_content = content[0].get("text", "{}")
                        try:
                            parsed_result = json.loads(text_content)
                            print(f"Successfully read {len(parsed_result.get('entities', []))} entities via stdio MCP")
                            return self._format_for_api(parsed_result)
                        except json.JSONDecodeError:
                            print(f"Failed to parse MCP response: {text_content}")
                            return self._get_stdio_error("Invalid JSON response")
                    else:
                        return self._get_stdio_error("Empty response from MCP tool")
                else:
                    error_msg = result.get("error", {}).get("message", "Unknown error") if result else "No response"
                    return self._get_stdio_error(f"MCP tool error: {error_msg}")

            except Exception as e:
                print(f"Stdio MCP read_graph failed: {e}")
                return self._get_stdio_error(str(e))

    async def search_nodes(self, query: str) -> dict[str, Any]:
        """Search nodes via stdio MCP"""
        async with self._lock:
            try:
                result = await self._call_mcp_tool("search_nodes", {"query": query})
                if result and not result.get("error"):
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
                print(f"Stdio MCP search_nodes failed: {e}")
                full_graph = await self.read_graph()
                return self._local_search(full_graph, query)

    async def _call_mcp_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any] | None:
        """Call an MCP tool using stdio protocol"""
        try:
            self._request_id += 1
            request = {
                "jsonrpc": "2.0",
                "id": self._request_id,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }

            # Start the subprocess
            process = await asyncio.create_subprocess_exec(
                *self.command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Send the request
            request_line = json.dumps(request) + "\n"
            stdout, stderr = await process.communicate(request_line.encode())

            if process.returncode == 0 and stdout:
                response = json.loads(stdout.decode().strip())
                if "result" in response:
                    return response["result"]
                elif "error" in response:
                    return {"error": response["error"]}
                else:
                    return {"error": {"message": "Invalid response format"}}
            else:
                if stderr:
                    error_msg = stderr.decode()
                    print(f"Stdio MCP stderr: {error_msg}")
                    return {"error": {"message": error_msg}}
                else:
                    return {"error": {"message": f"Process failed with code {process.returncode}"}}

        except Exception as e:
            print(f"Stdio MCP tool call failed: {e}")
            return {"error": {"message": str(e)}}

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

    def _get_stdio_error(self, error_msg: str) -> dict[str, Any]:
        """Error data when stdio MCP fails"""
        return {
            "entities": [
                {
                    "name": "Stdio MCP Status",
                    "entityType": "system_status",
                    "observations": [
                        f"Stdio MCP error: {error_msg}",
                        "Attempting to call MCP tools via subprocess stdio",
                        "This approach will work once MCP tools are accessible in subprocess context"
                    ]
                },
                {
                    "name": "Next: SQLite Backend",
                    "entityType": "development_task",
                    "observations": [
                        "Implement SQLite database schema for entities and relations",
                        "Create import functionality to populate from MCP data",
                        "Add database persistence layer to replace file storage"
                    ]
                }
            ],
            "relations": [
                {
                    "from_entity": "Stdio MCP Status",
                    "to": "Next: SQLite Backend",
                    "relationType": "enables"
                }
            ]
        }


# Create the stdio MCP client instance
stdio_mcp_knowledge_client = StdioMCPKnowledgeClient()
