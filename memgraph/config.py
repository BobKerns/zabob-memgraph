"""Configuration management for Zabob Memgraph"""

import json
import logging
import os
from pathlib import Path
from typing import NotRequired, TypedDict, Literal, cast


DEFAULT_PORT: Literal[6789] = 6789
CONFIG_DIR: Path = Path.home() / ".zabob" / "memgraph"
DOCKER_IMAGE: str = "bobkerns/zabob-memgraph:latest"
DEFAULT_CONTAINER_NAME: str = "zabob-memgraph"


class Config(TypedDict, total=True):
    """Configuration structure for Zabob Memgraph"""
    port: int
    host: str
    docker_image: NotRequired[str | None]
    container_name: NotRequired[str | None]
    log_level: str
    backup_on_start: bool
    max_backups: int
    data_dir: Path
    database_path: Path
    config_dir: Path
    config_file: NotRequired[Path | None]


def default_config_dir() -> Path:
    """Get configuration directory from environment or default

    This directory is shared between host and container for daemon
    coordination, enabling write-ahead-logging and simultaneous
    read/write access across processes.
    """
    config_dir = os.getenv(
        'MEMGRAPH_CONFIG_DIR', str(Path.home() / '.zabob' / 'memgraph')
    )
    return Path(config_dir)


def load_config(config_dir: Path, **settings: None | int | str | Path | bool) -> Config:
    """Load launcher configuration from file or return defaults"""
    config_file = config_dir / "config.json"

    defaults: Config = {
        "port": DEFAULT_PORT,
        "host": "localhost",
        "docker_image": DOCKER_IMAGE,
        "container_name": DEFAULT_CONTAINER_NAME,
        "log_level": "INFO",
        "backup_on_start": True,
        "max_backups": 5,
        "config_dir": config_dir,
        "data_dir": config_dir / "data",
        "database_path": config_dir / "data" / "knowledge_graph.db",
    }

    settings = {k: v for k, v in settings.items() if v is not None}

    if config_file.exists():
        try:
            with open(config_file) as f:
                raw_user_config = json.load(f)
                user_config = {
                    k: (Path(v) if isinstance(defaults[k], Path) else v)
                    for k, v in raw_user_config.items()
                    if v is not None
                    and k in defaults
                }
                return cast(Config, {
                    **defaults,
                    **user_config,
                    **settings,
                    # Not settable by config file
                    "config_file": config_file,
                    "config_dir": config_dir,
                })
        except Exception:
            pass

    return cast(Config, {
        **defaults,
        **settings,
        # Not settable by config file
        "config_dir": config_dir,
    })


def save_config(config_dir: Path, config: Config) -> None:
    """Save configuration to file"""
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "config.json"
    json_config = {
        k: (str(v.resolve()) if isinstance(v, Path) else v)
        for k, v in config.items()
        if k != "config_file"
    }

    try:
        with open(config_file, 'w') as f:
            json.dump(json_config, f, indent=2)
    except Exception as e:
        logging.warning(f"Could not save config: {e}")
