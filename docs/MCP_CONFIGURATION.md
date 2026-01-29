# MCP Configuration for Zabob Memgraph

> **⚠️ NOTE**: This document is partially outdated. REST API endpoints have been removed. See [USAGE_PATTERNS.md](./USAGE_PATTERNS.md) for current deployment options.

## Overview

Zabob Memgraph provides MCP (Model Context Protocol) support for accessing the knowledge graph. The server uses FastMCP to expose MCP tools over HTTP with Server-Sent Events (SSE).

## Server Architecture

The server provides these endpoints:

- **MCP Protocol**: `http://localhost:6789/mcp` (SSE transport)
- **Web UI**: `http://localhost:6789/`
- **Health Check**: `http://localhost:6789/health`

This architecture allows:

- ✅ Multiple clients accessing the same shared SQLite database
- ✅ No process spawning overhead
- ✅ Web UI and MCP tools use the same data
- ✅ Single server instance handles all requests

## MCP Configuration

### VS Code MCP Settings

Add to your `mcp.json` file:

```json
{
  "servers": {
    "zabob-memgraph": {
      "type": "sse",
      "url": "http://localhost:6789/mcp"
    }
  }
}
```

**Note**: VS Code's MCP client support for SSE transport is evolving. If `"type": "sse"` is not supported, you can use the REST API endpoints directly (see below).

### Starting the Server

The server must be running for MCP clients to connect:

```bash
# Start the server
./zabob-memgraph-launcher.py start

# Check status
./zabob-memgraph-launcher.py status

# Stop server
./zabob-memgraph-launcher.py stop
```

### Default Configuration

- **Host**: `localhost`
- **Port**: `6789`
- **Config Directory**: `~/.zabob-memgraph/`
- **Database**: `~/.zabob-memgraph/data/knowledge_graph.db`

## MCP Tools

The following MCP tools are available:

### `read_graph`

Read the complete knowledge graph.

**Parameters:**

- `name` (str, optional): Graph identifier (default: "foo")
- `val2` (dict, optional): Additional parameters

**Returns:**

- Complete graph data with entities, relations, and observations

### `search_nodes`

Search the knowledge graph for entities and relations.

**Parameters:**

- `query` (str): Search query string

**Returns:**

- Search results with matching entities and their metadata

## Using MCP Tools

### From VS Code

Once configured, the MCP tools are available in the VS Code command palette.

### Programmatically

Use the MCP SDK to call tools:

```typescript
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { SSEClientTransport } from '@modelcontextprotocol/sdk/client/sse.js';

const transport = new SSEClientTransport(
  new URL('http://localhost:6789/mcp')
);
const client = new Client({ name: 'my-client', version: '1.0.0' });
await client.connect(transport);

const result = await client.callTool('read_graph', { name: 'main' });
```

```json
{
  "results": [
    {
      "entity": "...",
      "type": "...",
      "snippet": "...",
      "score": ...
    }
  ]
}
```

## Testing MCP Connection

### Using curl

```bash
# Test health endpoint
curl http://localhost:6789/health

# Test MCP endpoint (expects SSE)
curl -H "Accept: text/event-stream" http://localhost:6789/mcp
```

### Expected Response

The MCP endpoint will respond with:

- SSE headers: `Content-Type: text/event-stream`
- JSON-RPC messages for the MCP protocol

## Troubleshooting

### Port Already in Use

```bash
# Check what's using port 6789
./zabob-memgraph-launcher.py status

# Stop existing server
./zabob-memgraph-launcher.py stop
```

### MCP Connection Issues

1. **Verify server is running**: `curl http://localhost:6789/health`
2. **Check logs**: `tail -f ~/.zabob-memgraph/memgraph.log`
3. **Test MCP endpoint**: `curl -H "Accept: text/event-stream" http://localhost:6789/mcp`

### Database Access Issues

The server uses SQLite with WAL mode for thread-safe concurrent access. If you see database locking errors:

1. Stop the server
2. Check for stale lock files: `ls ~/.zabob-memgraph/data/*.db-*`
3. Restart the server

## Advanced Configuration

### Custom Port

```bash
./zabob-memgraph-launcher.py start --port 9000
```

Update `mcp.json`:

```json
{
  "url": "http://localhost:9000/mcp"
}
```

### Network Access (Docker)

```bash
./zabob-memgraph-launcher.py start --docker --detach
```

Update `mcp.json`:

```json
{
  "url": "http://localhost:6789/mcp"
}
```

## Development

### Testing MCP Tools

```bash
# Start server with debug logging
MEMGRAPH_LOG_LEVEL=DEBUG ./zabob-memgraph-launcher.py start

# Monitor requests
tail -f ~/.zabob-memgraph/memgraph.log
```

### Adding New MCP Tools

Edit `memgraph/mcp_service.py`:

```python
@mcp.tool
async def your_tool(param: str) -> dict:
    """Tool description"""
    result = await DB.your_method(param)
    return result
```

Restart the server to load new tools.

## Resources

- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [Zabob Memgraph README](../README.md)
