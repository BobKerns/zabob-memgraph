"""Configuration management for Zabob Memgraph"""

import json
import logging
import os
from pathlib import Path


def get_config_dir() -> Path:
    """Get configuration directory from environment or default

    This directory is shared between host and container for daemon
    coordination, enabling write-ahead-logging and simultaneous
    read/write access across processes.
    """
    config_dir = os.getenv(
        'MEMGRAPH_CONFIG_DIR', str(Path.home() / '.zabob' / 'memgraph')
    )
    return Path(config_dir)


def get_database_path() -> Path:
    """Get database path from environment or default"""
    db_path = os.getenv('MEMGRAPH_DATABASE_PATH')
    if db_path:
        return Path(db_path)

    # Default to config directory data folder
    config_dir = get_config_dir()
    return config_dir / "data" / "knowledge_graph.db"


def load_config() -> dict[str, str | int | bool]:
    """Load configuration from file or return defaults"""
    config_dir = get_config_dir()
    config_file = config_dir / "config.json"

    defaults: dict[str, str | int | bool] = {
        "host": "localhost",
        "port": 6789,
        "log_level": "INFO",
        "backup_on_start": True,
        "max_backups": 5,
        "data_dir": str(config_dir / "data"),
    }

    if config_file.exists():
        try:
            with open(config_file) as f:
                user_config = json.load(f)
                defaults.update(user_config)
        except Exception as e:
            logging.warning(f"Could not load config file: {e}")

    return defaults


def save_config(config: dict[str, str | int | bool]) -> None:
    """Save configuration to file"""
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "config.json"

    try:
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        logging.warning(f"Could not save config: {e}")
