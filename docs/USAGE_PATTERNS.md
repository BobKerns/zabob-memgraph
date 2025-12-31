![Zabob Memory Holodeck](images/zabob-banner.jpg)
<!-- markdownlint-disable-file MD036 -->
# Zabob Memgraph Usage Patterns

## Three Ways to Use Zabob Memgraph

### 1. Docker with HTTP Server (Recommended for General Use)

**Best for:** Teams, persistent knowledge graphs, web UI access

**What you get:**

- HTTP server with web UI at http://localhost:6789
- MCP protocol at http://localhost:6789/mcp
- Persistent database in Docker volume
- Automatic backups
- Multi-client access

**Setup:**

```bash
# Using docker-compose (recommended)
docker-compose up -d

# Or using docker directly
docker run -d \
  -p 6789:6789 \
  -v zabob_memgraph_data:/data \
  --name zabob-memgraph \
  bobkerns/zabob-memgraph:latest
```

**Access:**

- Web UI: http://localhost:6789
- MCP endpoint: http://localhost:6789/mcp (SSE transport)
- Health check: http://localhost:6789/health

**Use with Claude Desktop:**

```json
{
  "mcpServers": {
    "zabob-memgraph": {
      "url": "http://localhost:6789/mcp",
      "transport": {
        "type": "sse"
      }
    }
  }
}
```

---

### 2. MCP Stdio (For Claude Desktop Integration)

**Best for:** Personal use, minimal setup, direct Claude integration

**What you get:**

- MCP protocol via stdio (no HTTP server)
- Database stored in ~/.zabob-memgraph/
- Lower resource usage
- No web UI

**Setup for Claude Desktop:**

**Option A: Docker stdio (isolated)**

```json
{
  "mcpServers": {
    "zabob-memgraph": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-v", "${HOME}/.zabob-memgraph:/app/.zabob-memgraph",
        "bobkerns/zabob-memgraph:latest",
        "stdio"
      ]
    }
  }
}
```

**Option B: Local Python (direct)**

```json
{
  "mcpServers": {
    "zabob-memgraph": {
      "command": "uvx",
      "args": ["zabob-memgraph", "stdio"]
    }
  }
}
```

**No web UI** - This mode is MCP-only

---

### 3. Local Python Installation (For Development)

**Best for:** Development, testing, customization

**What you get:**

- Full control over code
- Easy debugging
- Hot reload during development
- Can run HTTP server or stdio mode

**Setup:**

```bash
# Install dependencies
uv sync

# Development server with auto-reload
./zabob-memgraph-dev.py run --reload --port 6789

# Or run stdio mode for testing
uv run python main.py stdio
```

**Build web bundle:**

```bash
pnpm install
pnpm run build:web
```

---

## Comparison

| Feature | Docker HTTP | MCP Stdio | Local Python |
| ------- | ----------- | --------- | ------------ |
| Web UI | ✅ | ❌ | ✅ (dev mode) |
| MCP Protocol | ✅ (SSE) | ✅ (stdio) | ✅ (both) |
| Persistent Data | ✅ (volume) | ✅ (~/.zabob) | ✅ (~/.zabob) |
| Multi-client | ✅ | ❌ | ✅ |
| Port Required | 6789 | None | 6789 (HTTP) |
| Setup Complexity | Low | Lowest | Medium |
| Resource Usage | Medium | Low | Medium |

---

## Recommended Workflow

1. **Start with Docker HTTP** for general use and exploration
2. **Add MCP Stdio** configuration if you want Claude Desktop integration
3. **Use Local Python** only for development or customization

## Data Storage

All patterns store data in SQLite databases:

This defaults to `~/.zabob/memgraph/data/knowledge_graph.db`, and usually you will want to use the default. Other useful scenarios include:

- **Project isolation**
  - You are a consultant working for different clients.  KB per client
  - You want to keep distinct roles for different agents. KB per agent
  - Personal vs work
  - In each case, a separate network port number must also be assigned.
- **Docker Volumes**
  - Docker volumes offer various technical advantages, such as better performance, and a wide range of options for management.
  - In this usage pattern, the database is placed in `/data/db/knowledge_graph.db`
  - The docker volume is mounted at `/data`
  - It may also be advisable to set the configuration directory on this volume as well.

- **Docker HTTP**: `/data/knowledge_graph.db` (in Docker volume)
- **MCP Stdio**: `~/.zabob-memgraph/data/knowledge_graph.db`
- **Local Python**: `~/.zabob-memgraph/data/knowledge_graph.db`

You can migrate between patterns by copying the database file. Shut down all servers first.
