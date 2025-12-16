![Zabob Memory Holodeck](docs/images/zabob-banner.jpg)

# Zabob Memgraph Deployment Guide

Complete guide for deploying Zabob Memgraph in various configurations.

## Overview

Zabob Memgraph supports multiple deployment patterns to fit different use cases:

- **stdio mode**: For AI assistant integration (Claude Desktop, etc.)
- **HTTP server mode**: For web UI access and API endpoints
- **Docker**: For containerized deployments
- **Local**: For development and single-user scenarios

For all of these, sharing between all configured agents is the default. Separating them is as easy as choosing a different database location and network port.

## Understanding Server Modes

### stdio Mode

**Purpose**: Direct integration with AI assistants via stdin/stdout

**Characteristics**:

- Communicates via stdin/stdout using MCP protocol
- **Still listens on HTTP port** for web UI access
- Suitable for single-user desktop integration
- **Cannot share knowledge base across systems** (local only)

**Use Cases**:

- Claude Desktop integration
- Local AI assistant workflows
- Development and testing

### HTTP Server Mode

**Purpose**: Network-accessible server with web UI

**Characteristics**:

- HTTP/SSE transport for MCP protocol
- Web visualization interface
- **Can share knowledge base across systems**
- Supports multiple concurrent clients
- Thread-safe SQLite with WAL mode

**Use Cases**:

- Desktop + Laptop scenario (shared KB)
- Team collaboration
- Production deployments
- Cloud hosting

## Deployment Patterns

### 1. stdio with Docker (Easy Setup)

**Best for**: Quick Claude Desktop integration without installing Python

```json
{
  "mcpServers": {
    "zabob-memgraph": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-v", "${HOME}/.zabob/memgraph:/data/.zabob/memgraph",
        "bobkerns/zabob-memgraph:latest",
        "run"
      ]
    }
  }
}
```

**Pros**:

- No Python installation required
- Isolated environment
- Easy updates (`docker pull`)

**Cons**:

- Requires Docker
- stdio mode limits sharing to local machine

### 2. stdio with pipx/uvx (Minimal Installation)

**Best for**: Users who want minimal system impact

#### Using pipx

```bash
# Install once
pipx install zabob-memgraph

# Configure Claude Desktop
{
  "mcpServers": {
    "zabob-memgraph": {
      "command": "zabob-memgraph",
      "args": ["run"]
    }
  }
}
```

#### Using uvx (no installation)

```bash
# Configure Claude Desktop (downloads on demand)
{
  "mcpServers": {
    "zabob-memgraph": {
      "command": "uvx",
      "args": ["zabob-memgraph", "run"]
    }
  }
}
```

**Pros**:

- Lightweight installation
- System Python not affected
- Automatic dependency management

**Cons**:

- stdio mode limits sharing to local machine
- Requires pipx or uv

### 3. HTTP Server with Docker (Production)

**Best for**: Production deployments, team collaboration, multi-system access

```bash
# docker-compose.yml
version: '3.8'
services:
  zabob-memgraph:
    image: bobkerns/zabob-memgraph:latest
    command: ["start", "--host", "0.0.0.0", "--port", "6789"]
    ports:
      - "6789:6789"
    volumes:
      - ~/.zabob/memgraph:/data/.zabob/memgraph
    environment:
      - MEMGRAPH_HOST=0.0.0.0
      - MEMGRAPH_PORT=6789
      - MEMGRAPH_LOG_LEVEL=INFO
    restart: unless-stopped
    init: true

# Start server
docker-compose up -d

# Or with docker run
docker run -d --name zabob-memgraph \
  -p 6789:6789 \
  -v ${HOME}/.zabob/memgraph:/data/.zabob/memgraph \
  bobkerns/zabob-memgraph:latest \
  start --host 0.0.0.0 --port 6789

# Access web UI
open http://localhost:6789

# Configure AI assistants to use HTTP endpoint
# http://your-server:6789/mcp
```

**Pros**:

- **Shares knowledge base across systems** (Desktop + Laptop)
- Production-ready
- Easy scaling
- Automatic restarts
- Volume persistence

**Cons**:

- Requires Docker
- Network configuration for remote access

**Multi-System Setup**:

```bash
# On server (always-on machine)
docker-compose up -d

# On desktop
export MEMGRAPH_URL=http://server:6789

# On laptop
export MEMGRAPH_URL=http://server:6789

# Both systems access the same knowledge base!
```

### 4. HTTP Server Local (Development)

**Best for**: Development, testing, local experimentation

```bash
# Install development dependencies
uv sync

# Run with auto-reload (development)
zabob-memgraph run --reload --port 6789

# Or run in production mode
zabob-memgraph start --port 6789
```

**Pros**:

- Fast iteration
- Direct code access
- No containerization overhead

**Cons**:

- Requires Python 3.12+
- Manual dependency management
- Not suitable for production

## Multiple Server Scenarios

### Scenario: Development + Production

Run both a development server (with hot reload) and a production server:

```bash
# Production server (port 6789)
zabob-memgraph start --port 6789

# Development server (port 6790)
zabob-memgraph run --reload --port 6790
```

**Opening Web UI** (picks first available server):

```bash
# Opens whichever server is running
zabob-memgraph open

# Or from AI: "Open the knowledge graph"
# AI calls open_browser() MCP tool
```

### Scenario: Desktop + Laptop (Shared KB)

**Setup**: HTTP server on always-on machine, clients on multiple devices

```bash
# On server (always-on machine)
docker-compose up -d

# On desktop - configure AI assistant to connect to server
{
  "mcpServers": {
    "zabob-memgraph": {
      "command": "uvx",
      "args": ["zabob-memgraph", "run"]
      "env": {
        "MEMGRAPH_URL": "http://192.168.1.100:6789"
      }
    }
  }
}

# On laptop - same configuration
{
  "mcpServers": {
    "zabob-memgraph": {
      "command": "uvx",
      "args": ["zabob-memgraph", "run"]
      "env": {
        "MEMGRAPH_URL": "http://192.168.1.100:6789"
      }
    }
  }
}

# Both systems share the same knowledge base!
# Web UI accessible from any device: http://192.168.1.100:6789
```

**Benefits**:

- Single source of truth
- Synchronized knowledge across devices
- Accessible from anywhere on network
- Automatic backups in one location

## Deployment Decision Tree

```tree
Do you need to share KB across multiple systems?
│
├─ NO (single system)
│  │
│  ├─ Minimal installation?
│  │  └─ Use: stdio with pipx/uvx
│  │
│  └─ Don't want Python?
│     └─ Use: stdio with Docker
│
└─ YES (Desktop + Laptop, team, etc.)
   │
   ├─ Production deployment?
   │  └─ Use: HTTP server with Docker
   │
   └─ Development/testing?
      └─ Use: HTTP server local
```

## Configuration Comparison

| Feature | stdio (Docker) | stdio (pipx/uvx) | HTTP (Docker) | HTTP (Local) |
|---------|----------------|-------------------|---------------|--------------|
| Python Required | ❌ | ❌* | ❌ | ✅ |
| Docker Required | ✅ | ❌ | ✅ | ❌ |
| Web UI | ✅ | ✅ | ✅ | ✅ |
| Share Across Systems | ❌ | ❌ | ✅ | ⚠️** |
| Auto Restart | ❌ | ❌ | ✅ | ❌ |
| Hot Reload | ❌ | ❌ | ❌ | ✅ (dev) |
| Installation | Easy | Easy | Easy | Medium |
| Best For | Claude Desktop | Minimal setup | Production | Development |

\* uvx downloads Python if needed
\*\* Local HTTP can be shared on LAN but not production-ready

## Port Management

### Default Port: 6789

All modes use port 6789 by default. Configure with:

```bash
# Environment variable
export MEMGRAPH_PORT=8080

# Command line
zabob-memgraph start --port 8080

# Docker
docker run -p 8080:6789 zabob-memgraph

# Config file (~/.zabob/memgraph/config.json)
{
  "port": 8080,
  "host": "localhost"
}
```

### Auto Port Finding

If configured port is busy, the server automatically finds a free port:

```bash
# Configured for 6789, but it's busy
# Server finds 6790, saves it to config
# Future starts use 6790 automatically
# Old browser sessions still work!
```

### Multiple Servers

Run multiple servers on different ports:

```bash
# Production
zabob-memgraph start --port 6789

# Development
./zabob-memgraph-dev.py run --port 6790 --reload

# Check status
zabob-memgraph status

# Open browser (picks first available)
zabob-memgraph open
```

## Environment Variables Reference

| Variable | Description | Default |
|----------|-------------|---------|
| `MEMGRAPH_HOST` | Bind address | `localhost` |
| `MEMGRAPH_PORT` | Server port | `6789` |
| `MEMGRAPH_MODE` | `stdio` or `server` | `server` |
| `MEMGRAPH_LOG_LEVEL` | Log level | `INFO` |
| `MEMGRAPH_CONFIG_DIR` | Config directory | `~/.zabob/memgraph` |
| `MEMGRAPH_DATABASE_PATH` | DB file path | `~/.zabob/memgraph/data/knowledge_graph.db` |
| `DOCKER_CONTAINER` | Running in Docker | (auto-detected) |

## Troubleshooting

### "Server already running"

```bash
# Check status
zabob-memgraph status

# Stop if needed
zabob-memgraph stop

# Or use different port
zabob-memgraph start --port 6790
```

### "Cannot open browser in Docker"

Browser opening doesn't work inside containers. Use:

```bash
# Get the URL from status
zabob-memgraph status

# Open manually
open http://localhost:6789
```

Or the AI will provide the URL when you ask it to open the graph.

### "Port conflicts"

```bash
# See what's using the port
lsof -i :6789

# Use auto port finding
zabob-memgraph start
# (Finds next available port automatically)
```

### "Database locked"

This shouldn't happen with WAL mode, but if it does:

```bash
# Check for other server instances
zabob-memgraph status

# Stop all servers
zabob-memgraph stop

# Restart
zabob-memgraph start
```

## Migration Paths

### From stdio to HTTP

```bash
# Current: stdio mode (local only)
# Want: HTTP mode (share across systems)

# 1. Stop stdio server
# 2. Start HTTP server
zabob-memgraph start --docker --detach

# 3. Update AI assistant config
{
  "mcpServers": {
    "zabob-memgraph": {
      "command": "zabob-memgraph",
      "args": ["run"]
    }
  }
}

# Database is preserved!
```

### From Local to Docker

```bash
# Backup your data
cp -r ~/.zabob/memgraph ~/.zabob/memgraph.backup

# Start Docker with volume mount
docker run -d \
  -p 6789:6789 \
  -v ~/.zabob/memgraph:/data/.zabob/memgraph \
  --init \
  bobkerns/zabob-memgraph:latest \
  start --host 0.0.0.0 --port 6789

# Data is automatically migrated!
```

## Security Considerations

### Local Development

- Default: `localhost` binding (safe)
- Not accessible from network
- No authentication required

### Production Deployment

- Change to `0.0.0.0` binding
- Add reverse proxy (nginx, caddy)
- Enable HTTPS
- Configure CORS origins
- Consider authentication
- Use firewall rules

Example nginx config:

```nginx
server {
    listen 443 ssl;
    server_name memgraph.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:6789;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Best Practices

1. **Choose the right mode for your use case**
   - Single system → stdio
   - Multiple systems → HTTP server

2. **Use Docker for production**
   - Consistent environment
   - Easy updates
   - Automatic restarts

3. **Regular backups**
   - Automatic on server start
   - Manual: `cp ~/.zabob/memgraph/data/knowledge_graph.db backup.db`

4. **Monitor server health**
   - `zabob-memgraph monitor`
   - Check logs: `tail -f ~/.zabob/memgraph/memgraph.log`

5. **Test endpoints**
   - `zabob-memgraph test`
   - Verify health check: `curl http://localhost:6789/health`

## Summary

- **stdio mode**: Easy setup, local only, still has web UI
- **HTTP mode**: Network accessible, shareable, production-ready
- **Docker**: Recommended for production and easy setup
- **pipx/uvx**: Minimal installation for stdio mode
- **Multiple servers**: Supported, use different ports
- **Auto port finding**: Handles conflicts automatically
- **Browser opening**: Works in all modes (manual in Docker)

Choose the deployment pattern that fits your needs:

- Quick start → stdio with Docker
- Minimal impact → stdio with pipx/uvx
- Desktop + Laptop → HTTP server with Docker
- Development → HTTP server local with hot reload
