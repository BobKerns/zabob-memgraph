#!/usr/bin/env -Suv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "aiofiles",
#     "fastapi",
#     "fastmcp",
#     "jinja2",
#     "mcp",
#     "memgraph",
#     "pydantic",
#     "uvicorn[standard]",
# ]
# ///
"""
Main entry point for the Zabob Memgraph Knowledge Graph Server

This serves as both the standalone script entry point and the
Docker container entrypoint. Supports both HTTP server mode and
stdio mode for MCP protocol.

Handles database operations, backups, and configuration that
shouldn't be in the launcher.
"""

import json
import logging
import os
import shutil
import socket
import sys
import time
from pathlib import Path

from memgraph.service import main as run_server


def setup_logging(log_level: str = "INFO") -> None:
    """Setup logging configuration"""
    config_dir = get_config_dir()
    log_file = config_dir / "memgraph.log"

    # Ensure log directory exists
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )


def get_config_dir() -> Path:
    """Get configuration directory from environment or default

    This directory is shared between host and container for daemon
    coordination, enabling write-ahead-logging and simultaneous
    read/write access across processes.
    """
    config_dir = os.getenv('MEMGRAPH_CONFIG_DIR',
                           str(Path.home() / '.zabob-memgraph'))
    return Path(config_dir)


def get_database_path() -> Path:
    """Get database path from environment or default"""
    db_path = os.getenv('MEMGRAPH_DATABASE_PATH')
    if db_path:
        return Path(db_path)

    # Default to config directory data folder
    config_dir = get_config_dir()
    return config_dir / "data" / "knowledge_graph.db"


def backup_database() -> None:
    """Create a backup of the database if it exists"""
    config_dir = get_config_dir()
    db_file = get_database_path()
    backup_dir = config_dir / "backup"
    backup_dir.mkdir(exist_ok=True)

    # Ensure the database directory exists
    db_file.parent.mkdir(parents=True, exist_ok=True)

    if db_file.exists():
        timestamp = int(time.time())
        backup_file = backup_dir / f"knowledge_graph_{timestamp}.db"

        try:
            shutil.copy2(db_file, backup_file)
            logging.info(f"Database backed up to {backup_file}")

            # Keep only the 5 most recent backups
            backups = sorted(backup_dir.glob("knowledge_graph_*.db"),
                             key=lambda x: x.stat().st_mtime, reverse=True)
            for old_backup in backups[5:]:
                old_backup.unlink()
                logging.info(f"Removed old backup {old_backup}")

        except Exception as e:
            logging.warning(f"Could not create backup: {e}")
    else:
        logging.info("No existing database to backup")


def load_config() -> dict:
    """Load configuration from file or return defaults"""
    config_dir = get_config_dir()
    config_file = config_dir / "config.json"

    defaults = {
        "host": "localhost",
        "port": 6789,
        "log_level": "INFO",
        "backup_on_start": True,
        "max_backups": 5,
        "data_dir": str(config_dir / "data")
    }

    if config_file.exists():
        try:
            with open(config_file) as f:
                user_config = json.load(f)
                defaults.update(user_config)
        except Exception as e:
            logging.warning(f"Could not load config file: {e}")

    return defaults


def save_config(config: dict) -> None:
    """Save configuration to file"""
    config_dir = get_config_dir()
    config_file = config_dir / "config.json"

    try:
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        logging.warning(f"Could not save config: {e}")


def find_free_port(start_port: int = 6789) -> int:
    """Find a free port starting from start_port"""
    for port in range(start_port, start_port + 100):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"Could not find a free port in range {start_port}-{start_port + 100}")


def is_port_available(port: int, host: str = 'localhost') -> bool:
    """Check if a port is available"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, port))
            return True
    except OSError:
        return False


def main():
    """Main entry point with environment configuration support
    
    Supports two modes:
    - HTTP server mode (default): Runs HTTP/SSE server on specified port
    - stdio mode: Runs MCP stdio transport for Claude Desktop integration
    
    Mode is determined by:
    1. Command line argument: 'stdio' or 'server'
    2. Environment variable: MEMGRAPH_MODE=stdio|server
    3. Default: server mode
    """
    # Check for stdio mode
    mode = os.getenv('MEMGRAPH_MODE', 'server')
    if len(sys.argv) > 1 and sys.argv[1] == 'stdio':
        mode = 'stdio'
    
    # Load configuration
    config = load_config()

    # Override with environment variables (useful for Docker)
    host = os.getenv('MEMGRAPH_HOST', config['host'])
    requested_port = int(os.getenv('MEMGRAPH_PORT', str(config['port'])))
    log_level = os.getenv('MEMGRAPH_LOG_LEVEL', config['log_level'])
    static_dir = os.getenv('MEMGRAPH_STATIC_DIR', 'memgraph/web')

    # Setup logging
    setup_logging(log_level)

    # For Docker, bind to all interfaces
    if os.getenv('DOCKER_CONTAINER') or host == '0.0.0.0':
        host = '0.0.0.0'

    # Find an available port if the requested one is busy
    port = requested_port
    if not is_port_available(port, host):
        logging.warning(f"Port {port} is not available, finding a free port...")
        port = find_free_port(requested_port)
        logging.info(f"Using port {port} instead")

        # Save the new port to config so future starts use it
        config['port'] = port
        save_config(config)
        logging.info(f"Saved port {port} to configuration for future use")

    logging.info(f"Starting Zabob Memgraph server on {host}:{port}")
    logging.info(f"Configuration directory: {get_config_dir()}")
    logging.info(f"Database path: {get_database_path()}")
    logging.info(f"Web interface: http://{host}:{port}")

    # Create database backup if enabled
    if config.get('backup_on_start', True):
        backup_database()

    # Ensure data directory exists
    data_dir = Path(config['data_dir'])
    data_dir.mkdir(parents=True, exist_ok=True)

    # Start the server in the appropriate mode
    try:
        if mode == 'stdio':
            logging.info("Starting in stdio mode for MCP protocol")
            # Note: HTTP server still runs for web UI access
            # stdio is handled by the MCP service internally
            run_server(host=host, port=port, static_dir=static_dir, mode='stdio')
        else:
            run_server(host=host, port=port, static_dir=static_dir)

    except KeyboardInterrupt:
        logging.info("Server stopped by user")
    except Exception as e:
        logging.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
