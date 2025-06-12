#!/usr/bin/env python3
'''
A FastAPI application for Memgraph with a web interface.
'''

import sys
from fastmcp import FastMCP

from memgraph.sqlite_backend import SQLiteKnowledgeGraphDB


mcp = FastMCP(
    name="Zabob Memgraph Knowledge Graph Server",
    instructions="A FastAPI application for Memgraph with a web interface.",\
)


DB = SQLiteKnowledgeGraphDB(
    db_path="knowledge_graph.db",
)

@mcp.tool
async def read_graph(name: str='foo', val2: dict|None=None) -> dict:
    """
    Read a graph from the Memgraph database.

    Args:
        graph_name (str): The name of the graph to read.

    Returns:
        dict: The graph data.
    """
    # Placeholder for actual implementation
    print(f"Reading graph: {name}, val2: {val2}", file=sys.stderr)
    return await DB.read_graph()

@mcp.tool
async def search_nodes(query: str) -> dict:
    """
    Search the graph for entities and relations matching the query.

    Args:
        query (str): The search query.

    Returns:
        dict: The search results containing entities and relations.
    """
    # Placeholder for actual implementation
    print(f"Searching graph with query: {query}", file=sys.stderr)
    return await DB.search_nodes(query)

if __name__ == "__main__":
    # Run the MCP server
    try:
        mcp.run()
    except KeyboardInterrupt:
        print("Server stopped by user", file=sys.stderr)
    except Exception as e:
        print(f"Server error: {e}", file=sys.stderr)
        sys.exit(1)
