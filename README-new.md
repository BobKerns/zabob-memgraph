![Zabob Memgraph - Knowledge Graph Server](docs/images/zabob-memgraph-banner.jpg)

# Zabob Memgraph - Knowledge Graph Server

A Model Context Protocol (MCP) server that provides HTTP endpoints for knowledge graph visualization and interaction. Part of the Zabob AI assistant ecosystem, designed for thread-safe multi-client support with Docker deployment.

## Features

- **Thread-safe SQLite backend** - Prevents database locking issues with multiple clients
- **HTTP REST API** - JSON endpoints for programmatic access
- **Interactive D3.js visualization** - Web-based graph exploration
- **MCP protocol support** - Compatible with MCP clients and Claude Desktop
- **Docker deployment** - Containerized for easy deployment
- **Intelligent port management** - Automatic port assignment and process tracking
- **Database backups** - Automatic periodic backups with rotation
- **Full-text search** - Search across entities and observations
- **Click-based CLI** - Modern command-line interface with rich output

## Quick Start

### Simple Installation

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Download and install zabob-memgraph
curl -LsSf https://raw.githubusercontent.com/your-username/zabob-memgraph/main/zabob-memgraph-install.py | uv run --script -

# Start the server
zabob-memgraph start

# Check status
zabob-memgraph status
```

### Docker Usage

```bash
# Download launcher
curl -LO https://raw.githubusercontent.com/your-username/zabob-memgraph/main/zabob-memgraph-launcher.py
chmod +x zabob-memgraph-launcher.py

# Start with Docker
./zabob-memgraph-launcher.py start --docker

# Monitor the server
./zabob-memgraph-launcher.py monitor
```

## Usage

### Basic Commands

```bash
# Start the server (auto-assigns port)
zabob-memgraph start

# Start on specific port
zabob-memgraph start --port 8080

# Run in Docker
zabob-memgraph start --docker --detach

# Check server status
zabob-memgraph status

# Monitor server health
zabob-memgraph monitor

# Test all endpoints
zabob-memgraph test

# Stop server
zabob-memgraph stop
```

### Development Commands

If you're developing or contributing to the project:

```bash
# Clone the repository
git clone <repository-url>
cd zabob-memgraph

# Set up development environment
./zabob-memgraph-dev.py install

# Run in development mode with auto-reload
./zabob-memgraph-dev.py run --reload

# Build Docker image
./zabob-memgraph-dev.py build

# Run tests
./zabob-memgraph-dev.py test

# Format code
./zabob-memgraph-dev.py format

# Clean up
./zabob-memgraph-dev.py clean
```

## Configuration

### Data Directory

Configuration and data are stored in `~/.zabob-memgraph/`:

```
~/.zabob-memgraph/
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
  "default_port": 8080,
  "default_host": "localhost",
  "log_level": "INFO",
  "backup_on_start": true,
  "max_backups": 5,
  "data_dir": "~/.zabob-memgraph/data"
}
```

### Environment Variables

For Docker or advanced deployments:

```bash
export MEMGRAPH_HOST=0.0.0.0
export MEMGRAPH_PORT=8080
export MEMGRAPH_LOG_LEVEL=DEBUG
export MEMGRAPH_CONFIG_DIR=/custom/path
```

## API Endpoints

### Core Endpoints

- `GET /` - Web visualization interface
- `GET /api/knowledge-graph` - Complete graph data in D3 format
- `GET /api/entities` - All entities
- `GET /api/search?q=query` - Search entities and observations
- `POST /api/entities` - Create new entities
- `POST /api/relations` - Create new relations
- `GET /health` - Health check

### Example API Usage

```bash
# Get all graph data
curl http://localhost:8080/api/knowledge-graph

# Search for entities
curl "http://localhost:8080/api/search?q=project"

# Create new entities
curl -X POST http://localhost:8080/api/entities \\
  -H "Content-Type: application/json" \\
  -d '[{
    "name": "My Project",
    "entityType": "project", 
    "observations": ["Initial observation"]
  }]'
```

## MCP Integration

### Claude Desktop Configuration

Add to your MCP configuration:

```json
{
  "mcpServers": {
    "zabob-memgraph": {
      "command": "zabob-memgraph",
      "args": ["start", "--port", "8080"],
      "env": {
        "MEMGRAPH_HOST": "localhost"
      }
    }
  }
}
```

### Server Mode

For network-based MCP access:

```bash
# Start server that both MCP clients and HTTP clients can access
zabob-memgraph start --host 0.0.0.0 --port 8080
```

## Architecture

### Thread-Safe Design

The server uses SQLite with proper locking for concurrent access:

- **WAL mode**: Enables concurrent readers
- **Proper transactions**: Atomic operations prevent corruption
- **Connection pooling**: Efficient resource management
- **Automatic retries**: Handles temporary locking conflicts

### Component Structure

```
zabob-memgraph/
├── zabob-memgraph-launcher.py    # Main launcher (process management)
├── zabob-memgraph-dev.py         # Development commands
├── zabob-memgraph-install.py     # Installation script
├── main.py                       # Server entrypoint
├── memgraph/                     # Core package
│   ├── server.py                 # FastAPI application
│   ├── knowledge.py              # Data access layer
│   └── ...
└── install-uv.sh                 # uv installation helper
```

## Development

### Setting Up Development Environment

```bash
# Clone repository
git clone <repository-url>
cd zabob-memgraph

# Install dependencies
./zabob-memgraph-dev.py install

# Run in development mode
./zabob-memgraph-dev.py run --reload --port 8080

# Run tests
./zabob-memgraph-dev.py test

# Lint code
./zabob-memgraph-dev.py lint
```

### Docker Development

```bash
# Build development image
./zabob-memgraph-dev.py build

# Run with Docker Compose
./zabob-memgraph-dev.py docker-run

# View logs
./zabob-memgraph-dev.py logs

# Stop services
./zabob-memgraph-dev.py docker-stop
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
tail -f ~/.zabob-memgraph/memgraph.log

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
