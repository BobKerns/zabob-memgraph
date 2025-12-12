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
Docker container entrypoint.
Handles database operations, backups, and configuration that
shouldn't be in the launcher.
"""

import json
import logging
import os
import shutil
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


def main():
    """Main entry point with environment configuration support"""
    # Load configuration
    config = load_config()

    # Override with environment variables (useful for Docker)
    host = os.getenv('MEMGRAPH_HOST', config['host'])
    port = int(os.getenv('MEMGRAPH_PORT', str(config['port'])))
    log_level = os.getenv('MEMGRAPH_LOG_LEVEL', config['log_level'])
    static_dir = os.getenv('MEMGRAPH_STATIC_DIR', 'memgraph/web')

    # Setup logging
    setup_logging(log_level)

    # For Docker, bind to all interfaces
    if os.getenv('DOCKER_CONTAINER') or host == '0.0.0.0':
        host = '0.0.0.0'

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

    # Start the server
    try:
        run_server(host=host, port=port, static_dir=static_dir)

    except KeyboardInterrupt:
        logging.info("Server stopped by user")
    except Exception as e:
        logging.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
