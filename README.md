# Knowledge Graph MCP Server

A Model Context Protocol (MCP) server that provides HTTP endpoints for knowledge graph visualization and interaction. Features thread-safe multi-client support and can be deployed as either a standalone HTTP server or Docker container.

## Features

- **Thread-safe SQLite backend** - Prevents database locking issues with multiple clients
- **HTTP REST API** - JSON endpoints for programmatic access
- **Interactive D3.js visualization** - Web-based graph exploration
- **MCP protocol support** - Compatible with MCP clients
- **Docker deployment** - Containerized for easy deployment
- **Port management** - Automatic port assignment and process tracking
- **Database backups** - Automatic periodic backups
- **Full-text search** - Search across entities and observations

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd memgraph

# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f

# Access the web interface
open http://localhost:8080
```

### Option 2: Local Installation

#### Prerequisites

First, install the required tools:

```bash
# Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install git-lfs (for future large file support)
git lfs install
```

#### Installation

```bash
# Clone the repository
git clone <repository-url>
cd memgraph

# Install with uv
uv sync

# Run the launcher
uv run launcher.py
```

## Usage

### HTTP Server Mode (Recommended)

The launcher script automatically finds a free port and manages the server:

```bash
# Start server (auto-assigns port)
uv run launcher.py

# Start on specific port
uv run launcher.py --port 8080

# Check server status
uv run launcher.py --status

# Stop server
uv run launcher.py --stop
```

### STDIO Mode (Not recommended for production)

```bash
# Run as MCP stdio server (may have file locking issues)
uv run launcher.py --stdio
```

### Docker Volume Configuration

For production Docker deployments with persistent data:

```bash
# Create a named volume
docker volume create memgraph_data

# Run with volume mount
docker run -d \
  --name memgraph \
  -p 8080:8080 \
  -v memgraph_data:/root/.memgraph \
  memgraph:latest
```

**Note**: Docker volumes properly implement file locking and fsync, making them suitable for SQLite. However, write-ahead logging (WAL) mode may be limited due to shared memory constraints.

## Configuration

### Data Directory

By default, configuration and data are stored in `~/.memgraph/`:

```
~/.memgraph/
├── memgraph.log        # Application logs
├── port               # Current server port
├── pid                # Current server PID
├── server_info.json   # Combined server info
└── backup/            # Database backups
    ├── knowledge_graph_1234567890.db
    └── ...
```

Override with:
```bash
uv run launcher.py --data-dir /custom/path
```

### Database Backups

Backups are automatically created:
- On server startup
- Periodically (can be configured)
- Stored in `~/.memgraph/backup/`
- Keeps 5 most recent backups

## API Endpoints

### Core Endpoints

- `GET /` - Web visualization interface
- `GET /api/knowledge-graph` - Complete graph data in D3 format
- `GET /api/entities` - All entities
- `GET /api/search?q=query` - Search entities and observations
- `POST /api/entities` - Create new entities
- `POST /api/relations` - Create new relations
- `GET /health` - Health check

### Management Endpoints

- `POST /api/import-mcp` - Import data from MCP sources
- `GET /api/database-stats` - SQLite database statistics

### Example API Usage

```bash
# Get all graph data
curl http://localhost:8080/api/knowledge-graph

# Search for entities
curl "http://localhost:8080/api/search?q=project"

# Create new entities
curl -X POST http://localhost:8080/api/entities \
  -H "Content-Type: application/json" \
  -d '[{
    "name": "My Project",
    "entityType": "project", 
    "observations": ["Initial observation"]
  }]'
```

## Architecture

### Thread-Safe Design

The server uses SQLite with proper locking to handle multiple concurrent clients safely:

- **WAL mode**: Enables concurrent readers
- **Proper transactions**: Atomic operations prevent corruption
- **Connection pooling**: Efficient resource management
- **Automatic retries**: Handles temporary locking conflicts

### Backend Selection

The server automatically selects the best available backend:

1. **SQLite backend** (preferred) - Thread-safe persistent storage
2. **Docker MCP client** - Live integration with Docker MCP tools
3. **Stdio MCP client** - Direct MCP protocol communication
4. **File-based fallback** - Simple JSON storage

## Development

### Local Development Setup

```bash
# Install development dependencies
uv sync --group dev

# Run type checking
uv run mypy memgraph/

# Format code
uv run black memgraph/
uv run isort memgraph/

# Run tests
uv run pytest
```

### Building Docker Image

```bash
# Build image
docker build -t memgraph:latest .

# Run locally
docker run -p 8080:8080 memgraph:latest
```

## Troubleshooting

### Common Issues

**Database busy errors**:
- Use HTTP mode instead of STDIO mode
- Ensure only one server instance is running per database
- Check `~/.memgraph/pid` for stale processes

**Port conflicts**:
- Use `--port` to specify a different port
- Check running processes: `uv run launcher.py --status`
- Stop existing server: `uv run launcher.py --stop`

**Docker volume issues**:
- Ensure proper volume mounting
- Check file permissions
- Use named volumes for persistence

### Logs

Application logs are stored in:
- Local: `~/.memgraph/memgraph.log`
- Docker: View with `docker logs <container-name>`

### Process Management

```bash
# Check if server is running
uv run launcher.py --status

# View process info
ps aux | grep memgraph

# Kill stale processes (if needed)
kill $(cat ~/.memgraph/pid)
```

## Performance Notes

- **SQLite Performance**: Generally excellent for read-heavy workloads
- **Docker Volumes**: Perform well for database storage with proper fsync support
- **Memory Usage**: Low footprint, suitable for resource-constrained environments
- **Scaling**: Single-process design, scale horizontally with multiple instances

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with proper tests
4. Ensure type checking passes: `uv run mypy memgraph/`
5. Format code: `uv run black memgraph/ && uv run isort memgraph/`
6. Submit a pull request

## License

[License information]
