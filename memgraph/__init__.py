"""
Knowledge Graph MCP HTTP Server

Provides HTTP endpoints for knowledge graph data while maintaining MCP compatibility.
Serves static web assets for D3.js visualization client.
"""

from memgraph.backup import backup_database
from memgraph.config import get_config_dir, get_database_path, load_config, save_config
from memgraph.service import create_unified_app, main as run_server

__version__ = "0.1.0"
__all__ = [
    'backup_database',
    'create_unified_app',
    'get_config_dir',
    'get_database_path',
    'load_config',
    'run_server',
    'save_config',
]
