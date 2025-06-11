"""
Docker MCP Client for Knowledge Graph

This module connects to the actual MCP memory Docker container
to import real knowledge graph data.
"""

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any


class DockerMCPKnowledgeClient:
    """
    Client that connects to MCP memory Docker container to get real knowledge graph data.
    """

    def __init__(self, container_command: list[str] | None = None):
        self._lock = asyncio.Lock()
        self._request_id = 0
        # Default to the memory container pattern you mentioned
        self.container_command = container_command or [
            "docker", "run", "-i",
            "-v", "claude-memory:/app/dist",
            "--rm", "mcp/memory"
        ]

    async def read_graph(self) -> dict[str, Any]:
        """Read the complete knowledge graph from Docker MCP container"""
        async with self._lock:
            try:
                result = await self._call_mcp_tool("read_graph", {})
                if result and not result.get("error"):
                    content = result.get("content", [])
                    if content and len(content) > 0:
                        text_content = content[0].get("text", "{}")
                        try:
                            parsed_result = json.loads(text_content)
                            print(f"Successfully read {len(parsed_result.get('entities', []))} entities from Docker MCP")
                            return self._format_for_api(parsed_result)
                        except json.JSONDecodeError:
                            print(f"Failed to parse Docker MCP response: {text_content}")
                            return self._get_docker_error("Invalid JSON response")
                    else:
                        return self._get_docker_error("Empty response from Docker MCP")
                else:
                    error_msg = result.get("error", {}).get("message", "Unknown error") if result else "No response"
                    return self._get_docker_error(f"Docker MCP error: {error_msg}")

            except Exception as e:
                print(f"Docker MCP read_graph failed: {e}")
                return self._get_docker_error(str(e))

    async def search_nodes(self, query: str) -> dict[str, Any]:
        """Search nodes via Docker MCP container"""
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
                            print(f"Failed to parse Docker search response: {text_content}")
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
                print(f"Docker MCP search_nodes failed: {e}")
                full_graph = await self.read_graph()
                return self._local_search(full_graph, query)

    async def _call_mcp_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any] | None:
        """Call an MCP tool using Docker container with MCP protocol"""
        try:
            self._request_id += 1

            # MCP protocol request
            request = {
                "jsonrpc": "2.0",
                "id": self._request_id,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }

            # Start the Docker container
            process = await asyncio.create_subprocess_exec(
                *self.container_command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Send the MCP request
            request_line = json.dumps(request) + "\n"
            stdout, stderr = await process.communicate(request_line.encode())

            if process.returncode == 0 and stdout:
                # Parse MCP response
                response_text = stdout.decode().strip()
                if response_text:
                    try:
                        response = json.loads(response_text)
                        if "result" in response:
                            return response["result"]
                        elif "error" in response:
                            return {"error": response["error"]}
                        else:
                            return {"error": {"message": "Invalid MCP response format"}}
                    except json.JSONDecodeError:
                        # Sometimes MCP tools return plain text, try to wrap it
                        return {
                            "content": [{"type": "text", "text": response_text}]
                        }
                else:
                    return {"error": {"message": "Empty response from Docker container"}}
            else:
                if stderr:
                    error_msg = stderr.decode()
                    print(f"Docker MCP stderr: {error_msg}")
                    return {"error": {"message": error_msg}}
                else:
                    return {"error": {"message": f"Docker process failed with code {process.returncode}"}}

        except Exception as e:
            print(f"Docker MCP tool call failed: {e}")
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

    def _get_docker_error(self, error_msg: str) -> dict[str, Any]:
        """Error data when Docker MCP fails"""
        return {
            "entities": [
                {
                    "name": "Docker MCP Status",
                    "entityType": "system_status",
                    "observations": [
                        f"Docker MCP error: {error_msg}",
                        "Attempting to connect to MCP memory Docker container",
                        f"Container command: {' '.join(self.container_command)}",
                        "Ensure Docker is running and mcp/memory image is available"
                    ]
                },
                {
                    "name": "Docker Setup",
                    "entityType": "instructions",
                    "observations": [
                        "Pull the MCP memory container: docker pull mcp/memory",
                        "Ensure claude-memory volume exists with your data",
                        "Container should respond to MCP protocol over stdin/stdout"
                    ]
                }
            ],
            "relations": [
                {
                    "from_entity": "Docker MCP Status",
                    "to": "Docker Setup",
                    "relationType": "requires"
                }
            ]
        }


# Create the Docker MCP client instance
docker_mcp_knowledge_client = DockerMCPKnowledgeClient()
