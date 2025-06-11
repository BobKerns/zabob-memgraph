# Knowledge Graph MCP Server

A Model Context Protocol (MCP) server that provides HTTP endpoints for knowledge graph visualization and interaction.

## Architecture

- **MCP Server**: Python-based server using FastMCP framework
- **HTTP Interface**: RESTful endpoints for knowledge graph data
- **Web Client**: D3.js-based interactive visualization
- **Data Source**: Integration with existing knowledge graph tools

## Features

- Real-time knowledge graph data via HTTP API
- Interactive D3.js force-directed visualization
- Full-text search across entities and observations
- Scalable architecture supporting unlimited entities
- CORS-enabled for local development

## Quick Start

```bash
# Install dependencies
pip install -e .

# Start the MCP server
python -m memgraph.server

# Open web client
open http://localhost:8080
```

## Development

This project integrates with the existing zabob MCP ecosystem while providing a lightweight HTTP interface for web-based knowledge graph visualization.

## Directory Structure

```
memgraph/
├── memgraph/          # Python package
│   ├── server.py      # MCP server with HTTP endpoints
│   ├── knowledge.py   # Knowledge graph data access
│   └── web/           # Static web assets
│       ├── index.html # D3.js visualization client
│       ├── graph.js   # Graph logic
│       └── style.css  # Styling
├── pyproject.toml     # Python project configuration
└── README.md          # This file
```
