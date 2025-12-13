![Zabob Memgraph - Knowledge Graph Server](docs/images/zabob-holodeck-text.jpg)

# Zabob Memgraph - Knowledge Graph Server

A Model Context Protocol (MCP) server for persistent knowledge graph storage with interactive web visualization. Part of the Zabob AI assistant ecosystem, designed for thread-safe multi-client support with Docker deployment.

**📖 See [DEPLOYMENT.md](DEPLOYMENT.md) for comprehensive deployment options**

**📖 See [USAGE_PATTERNS.md](USAGE_PATTERNS.md) for usage examples**

Imagine a future where your AI assistant not only can talk to you, but can remember important things, and can show you everything it remembers.

![zabob](docs/images/zabob-faviicon.png) Zabob remembers this future! Give him your plans and dreams, and he will remember not just the dream, but the journey to get there, even through the darkest nullspace.

![alt text](docs/images/screenshot.png)

## Features

- **MCP Protocol** - Standard Model Context Protocol for AI assistant integration
- **Multiple Transports** - HTTP/SSE for server mode, stdio for Claude Desktop
- **Thread-safe SQLite backend** - WAL mode for concurrent access without locking
- **Interactive D3.js visualization** - Real-time graph exploration via web UI
- **Docker deployment** - Multiple deployment patterns (HTTP server, stdio, local)
- **Persistent storage** - Database with automatic backups and rotation
- **Full-text search** - Search across entities, observations, and relations
- **Modern tooling** - esbuild bundler, Python type checking, comprehensive tests

## Quick Start

### Docker Compose (Recommended)

```bash
# Clone repository
git clone https://github.com/BobKerns/zabob-memgraph.git
cd zabob-memgraph

# Start HTTP server with web UI
docker-compose up -d

# Access web UI at http://localhost:6789
# MCP endpoint at http://localhost:6789/mcp
```

### Claude Desktop Integration

Add to your Claude Desktop MCP config:

**stdio mode (local only)**:

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

**HTTP mode (shareable across systems)**:

```bash
# Start HTTP server
docker run -d --name zabob-memgraph \
  -p 6789:6789 \
  -v ${HOME}/.zabob/memgraph:/data/.zabob/memgraph \
  bobkerns/zabob-memgraph:latest \
  start --host 0.0.0.0 --port 6789
```

Then configure Claude Desktop to connect to `http://localhost:6789/mcp`

**📖 See [DEPLOYMENT.md](DEPLOYMENT.md) for complete deployment options**

## Usage

### Basic Commands

```bash
# Start the server (auto-assigns port)
zabob-memgraph start

# Start on specific port
zabob-memgraph start --port 6789

# Run in foreground (stdio mode or development)
zabob-memgraph run

# Run with auto-reload (development)
zabob-memgraph run --reload

# Check server status
zabob-memgraph status

# Monitor server health
zabob-memgraph monitor

# Test all endpoints
zabob-memgraph test

# Stop server
zabob-memgraph stop
```

### Docker Commands

```bash
# Run in foreground (stdio mode)
docker run --rm -i \
  -v ${HOME}/.zabob/memgraph:/data/.zabob/memgraph \
  bobkerns/zabob-memgraph:latest \
  run

# Run as HTTP server (background)
docker run -d --name zabob-memgraph \
  -p 6789:6789 \
  -v ${HOME}/.zabob/memgraph:/data/.zabob/memgraph \
  bobkerns/zabob-memgraph:latest \
  start --host 0.0.0.0 --port 6789

# Run development commands in container
docker run --rm -it \
  -v $(pwd):/app \
  bobkerns/zabob-memgraph:latest \
  lint
```

### Development Commands

The CLI automatically detects development environments and enables additional commands:

```bash
# Development commands (available when .git exists or dev dependencies installed)
zabob-memgraph run --reload  # Run with auto-reload
zabob-memgraph build         # Build Docker image
zabob-memgraph lint          # Run type checking and linting
zabob-memgraph format        # Format code with ruff
zabob-memgraph clean         # Clean build artifacts

# Production commands (always available)
zabob-memgraph start         # Start server in background
zabob-memgraph stop          # Stop server
zabob-memgraph restart       # Restart server
zabob-memgraph status        # Check server status
zabob-memgraph open          # Open browser to web UI
zabob-memgraph test          # Test all endpoints
zabob-memgraph monitor       # Monitor server health
```

**Development Setup**:

```bash
# Clone repository
git clone <repository-url>
cd zabob-memgraph

# Install dependencies (dev commands auto-enabled)
uv sync

# Build web UI
pnpm install && pnpm run build:web

# Run with auto-reload
zabob-memgraph run --reload
```

## Configuration

### Data Directory

Configuration and data are stored in `~/.zabob/memgraph/`:

```text
~/.zabob/memgraph/
├── config.json           # Server configuration
├── server_info.json      # Current server status
├── memgraph.log          # Application logs
├── data/                 # Database files
│   └── knowledge_graph.db
└── backup/               # Automatic backups
    ├── knowledge_graph_1234567890.db
    └── ...
```

### Configuration File

The `config.json` file supports these options:

```json
{
  "default_port": 6789,
  "default_host": "localhost",
  "log_level": "INFO",
  "backup_on_start": true,
  "max_backups": 5,
  "data_dir": "~/.zabob/memgraph/data"
}
```

### Environment Variables

For Docker or advanced deployments:

```bash
export MEMGRAPH_HOST=0.0.0.0
export MEMGRAPH_PORT=6789
export MEMGRAPH_LOG_LEVEL=DEBUG
export MEMGRAPH_CONFIG_DIR=/custom/path
```

## MCP Tools

Zabob Memgraph provides these MCP tools for AI assistants:

- **create_entities** - Create new entities with observations
- **create_relations** - Create relationships between entities
- **add_observations** - Add observations to existing entities
- **read_graph** - Read the complete knowledge graph
- **search_nodes** - Full-text search across entities and observations
- **delete_entities** - Remove entities and their relations
- **delete_relations** - Remove specific relationships
- **get_stats** - Get graph statistics

### HTTP Endpoints

When running in HTTP server mode:

- `GET /` - Web visualization interface
- `POST /mcp` - MCP protocol endpoint (SSE transport)
- `GET /health` - Health check

### Using MCP Tools

MCP tools are called through the protocol. Example using the web UI:

1. Open http://localhost:6789
2. View entities and relations in the interactive graph
3. Search, zoom, and explore your knowledge graph

For Claude Desktop integration, tools are automatically available after configuration.

## Architecture

### Thread-Safe Design

The server uses SQLite with proper locking for concurrent access:

- **WAL mode**: Enables concurrent readers
- **Proper transactions**: Atomic operations prevent corruption
- **Connection pooling**: Efficient resource management
- **Automatic retries**: Handles temporary locking conflicts

### Component Structure

```text
zabob-memgraph/
├── zabob-memgraph-dev.py         # Development CLI
├── main.py                       # Server entrypoint
├── memgraph/                     # Core package
│   ├── service.py                # Unified ASGI service (MCP + HTTP)
│   ├── mcp_service.py            # FastMCP server implementation
│   ├── knowledge_live.py         # Knowledge graph data layer
│   ├── sqlite_backend.py         # Thread-safe SQLite backend
│   ├── web/                      # Static web assets
│   │   ├── index.html
│   │   ├── graph.bundle.js       # Bundled web UI (built)
│   │   └── style.css
│   └── web-src/                  # Web UI source
│       ├── mcp-client.js         # Browser MCP client
│       └── graph.js              # D3.js visualization
├── docker-compose.yml            # Docker Compose config
└── Dockerfile                    # Container definition
```

## Development

### Setting Up Development Environment

```bash
# Clone repository
git clone <repository-url>
cd zabob-memgraph

# Install dependencies (enables dev commands)
uv sync

# Build web UI
pnpm install && pnpm run build:web

# Run in development mode with auto-reload
zabob-memgraph run --reload --port 6789

# Run tests
zabob-memgraph test

# Lint code
zabob-memgraph lint

# Format code
zabob-memgraph format
```

### Docker Development

```bash
# Build Docker image
zabob-memgraph build

# Run in Docker (if configured)
zabob-memgraph start --docker --detach

# Check status
zabob-memgraph status

# Stop services
zabob-memgraph stop
```

## Troubleshooting

### Common Issues

**Server already running**:

```bash
zabob-memgraph status
zabob-memgraph stop
```

**Port conflicts**:

```bash
zabob-memgraph start --port 8081
```

**Docker issues**:

```bash
# Check if image exists
docker images | grep zabob-memgraph

# Build if missing
./zabob-memgraph-dev.py build
```

**Database issues**:

```bash
# Check logs
tail -f ~/.zabob-memgraph/memgraph.log

# Test server endpoints
zabob-memgraph test
```

### Logs and Debugging

```bash
# View real-time logs
tail -f ~/.zabob/memgraph/memgraph.log

# Monitor server health
zabob-memgraph monitor

# Test all endpoints
zabob-memgraph test
```

## Performance Notes

- **SQLite Performance**: Excellent for read-heavy workloads with WAL mode
- **Docker Deployment**: Recommended for production with volume persistence
- **Memory Usage**: Low footprint suitable for resource-constrained environments
- **Scaling**: Scale horizontally with multiple instances on different ports

## Part of the Zabob Ecosystem

Zabob Memgraph is designed to work with other Zabob AI tools:

- **Zabob Core**: Main AI assistant framework
- **Zabob Memgraph**: Knowledge graph persistence (this project)
- **Zabob Tools**: Additional MCP tools and utilities

The `zabob-` prefix helps identify tools in this ecosystem while maintaining distinct, memorable names.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Use the development tools:

   ```bash
   ./zabob-memgraph-dev.py install
   ./zabob-memgraph-dev.py test
   ./zabob-memgraph-dev.py lint
   ```

4. Submit a pull request

## License

[License information]

---

**Getting Started**: `zabob-memgraph start`
**Need Help**: `zabob-memgraph --help`
**Issues**: [GitHub Issues](https://github.com/your-username/zabob-memgraph/issues)
