"""
Knowledge Graph MCP HTTP Server

Provides HTTP endpoints for knowledge graph data while maintaining MCP compatibility.
Serves static web assets for D3.js visualization client.
"""

from memgraph.backup import backup_database
from memgraph.config import load_config, save_config, default_config_dir
from memgraph.launcher import (
    find_free_port,
    get_server_info,
    is_dev_environment,
    is_port_available,
    is_server_running,
    start_docker_server,
    start_local_server,
)
from memgraph.service import create_unified_app, run_server as run_server
from memgraph.__version__ import __version__, __distribution__

__all__ = [
    'backup_database',
    'create_unified_app',
    'find_free_port',
    'default_config_dir',
    'get_server_info',
    'is_dev_environment',
    'is_port_available',
    'is_server_running',
    'load_config',
    'run_server',
    'save_config',
    'start_docker_server',
    'start_local_server',
    '__version__',
    '__distribution__',
]
