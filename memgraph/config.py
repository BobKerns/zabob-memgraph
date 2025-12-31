"""Configuration management for Zabob Memgraph"""

from collections.abc import Callable
import json
import logging
import os
from pathlib import Path, PosixPath
import sys
from typing import Any, TypedDict, Literal, cast, overload
from functools import cache

import click

# Configuration
IN_DOCKER = os.environ.get("DOCKER_CONTAINER") == "1"
DEFAULT_PORT: Literal[6789] = 6789
CONFIG_DIR: Path = Path.home() / ".zabob" / "memgraph"
DOCKER_IMAGE: str = "bobkerns/zabob-memgraph:latest"
DEFAULT_CONTAINER_NAME: str = "zabob-memgraph"


class HostInfo(TypedDict):
    """
    Host information structure for Zabob Memgraph
    This holds information about the host system
    or how the container is configured, such as the
    original host and port, or database path.
    """

    os: str
    architecture: str
    cpu_count: int
    total_memory_gb: float
    memgraph_version: str
    database_path: Path
    data_dir: Path
    host: str
    port: int
    container_name: str


class Config(TypedDict, total=True):
    """Configuration structure for Zabob Memgraph"""

    name: str
    port: int
    host: str
    docker_image: str
    container_name: str
    log_level: str
    access_log: bool
    backup_on_start: bool
    min_backups: int
    backup_age_days: int
    reload: bool
    data_dir: Path
    database_path: Path
    static_dir: Path
    config_dir: Path
    log_file: Path
    config_file: Path
    real_port: int
    real_host: str
    real_data_dir: Path
    real_database_path: Path


def default_config_dir() -> Path:
    """Get configuration directory from environment or default

    This directory is shared between host and container for daemon
    coordination, enabling write-ahead-logging and simultaneous
    read/write access across processes.
    """
    config_dir = os.getenv("MEMGRAPH_CONFIG_DIR", str(Path.home() / ".zabob" / "memgraph"))
    return Path(config_dir)


DEFAULT_CONFIG: Config = Config(
    name="",  # Defaulted later
    port=int(os.getenv("MEMGRAPH_PORT", DEFAULT_PORT)),
    host=os.getenv("MEMGRAPH_HOST", "localhost"),
    docker_image=os.getenv("MEMGRAPH_DOCKER_IMAGE", DOCKER_IMAGE),
    container_name=os.getenv("MEMGRAPH_CONTAINER_NAME", DEFAULT_CONTAINER_NAME),
    log_level=os.getenv("MEMGRAPH_LOG_LEVEL", "INFO"),
    access_log=True,  # For now.
    backup_on_start=True,
    min_backups=5,
    backup_age_days=30,
    reload=False,
    config_dir=default_config_dir(),
    static_dir=Path(__file__).parent / "web",
    data_dir=Path(os.getenv("MEMGRAPH_DATA_DIR", default_config_dir() / "data")),
    database_path=Path(os.getenv("MEMGRAPH_DATABASE_PATH", default_config_dir() / "data" / "knowledge_graph.db")),
    log_file=Path(os.getenv("MEMGRAPH_LOG_FILE", default_config_dir() / "memgraph.log")),
    # The following are set at runtime and not stored in config file
    config_file=Path(),
    real_port=0,
    real_host="TBD",
    real_data_dir=Path(),
    real_database_path=Path(),
)


@overload
def match_type[T](value: None, expected_type: type[T]) -> None: ...


@overload
def match_type[T](value: object, expected_type: type[T]) -> T: ...


def match_type[T](value: object, expected_type: type[T]) -> T | None:
    """
    Helper to match and cast types for TypedDicts.

    The expected_type should be a type object like `int`, `str`, etc,
    that can act as a type constructor.

    Args:
        value: The value to check
        expected_type: The expected type
    """
    # We won't get None in the current usage, but keep the overload for clarity
    # type checkers and future-proofing.
    if value is None:
        return None
    if expected_type is bool:
        # Special case for bool since bool("false") is True
        if isinstance(value, bool):
            return cast(T, value)
        if isinstance(value, str):
            lowered = value.lower()
            if lowered in ("true", "1", "yes"):
                return True  # type: ignore[return-value]
            if lowered in ("false", "0", "no"):
                return False  # type: ignore[return-value]
        # This shouldn't arise in practice, but fall back to standard conversion,
        # including the __bool__ method.
        return cast(T, bool(value))
    if isinstance(value, expected_type):
        return value
    constructor = cast(Callable[[Any], T], expected_type)
    return constructor(value)


@cache
def load_config(config_dir: Path, /, *, docker: bool = False, **settings: None | int | str | Path | bool) -> Config:
    """
    Load launcher configuration from file or return defaults

    Args:
        config_dir: Directory where configuration file is stored
        docker: Whether to adjust configuration for Docker usage
        settings: Override settings to apply on top of loaded configuration

    Returns:
        Config: Loaded configuration
    """

    def compute_config() -> Config:
        """
        Compute the configs before adjusting for docker.
        """
        config_file = config_dir / "config.json"

        filtered = {k: v for k, v in settings.items() if v is not None and k in DEFAULT_CONFIG}

        if config_file.exists():
            try:
                with open(config_file) as f:
                    raw_user_config = json.load(f)
                    user_config = {
                        k: match_type(v, type(DEFAULT_CONFIG[k]))  # type: ignore[literal-required]
                        for k, v in raw_user_config.items()
                        if v is not None and k in DEFAULT_CONFIG
                    }
                    return cast(
                        Config,
                        {
                            **DEFAULT_CONFIG,
                            **user_config,
                            **filtered,
                            # Not settable by config file
                            "config_file": config_file,
                            "config_dir": config_dir,
                        },
                    )
            except Exception:
                pass

        return cast(
            Config,
            {
                **DEFAULT_CONFIG,
                **filtered,
                # Not settable by config file
                "config_dir": config_dir,
            },
        )

    def default_name(config: Config) -> Config:
        name = config["name"].strip()
        if not name:
            if config["real_port"] != DEFAULT_PORT:
                name = f"zabob-memgraph-{config['real_port']}"
            else:
                name = "zabob-memgraph"
        config["name"] = name
        return config

    if docker:
        config = compute_config()
        host = config["host"]
        port = config["port"]
        data_dir = config["data_dir"]
        database_path = config["database_path"]
        # Adjust host for Docker usage
        config["host"] = "0.0.0.0"
        config["port"] = DEFAULT_PORT
        if database_path.is_file():
            db_dir = database_path.parent
            db_name = database_path.name
            # The path inside the container
            database_path = PosixPath("/data") / db_name
            config["database_path"] = database_path
            # The host path to mount
            config["data_dir"] = db_dir
        elif database_path.is_dir():
            config["database_path"] = PosixPath("/data") / "knowledge_graph.db"
            config["data_dir"] = database_path
        elif database_path.suffix == ".db":
            db_dir = database_path.parent
            config["database_path"] = PosixPath("/data") / database_path.name
            config["data_dir"] = db_dir
            try:
                db_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                click.echo(f"Could not create database directory {db_dir}: {e}")
                sys.exit(2)
        else:
            config["database_path"] = PosixPath("/data") / "knowledge_graph.db"
            config["data_dir"] = database_path
            database_path.mkdir(parents=True, exist_ok=True)
        if IN_DOCKER:
            host_info_file = PosixPath("/host/host_info.json")
            with host_info_file.open("r") as f:
                host_info = cast(HostInfo, json.load(f))
                config["real_port"] = host_info["port"]
                config["real_host"] = host_info["host"]
                config["real_data_dir"] = host_info["data_dir"]
                config["real_database_path"] = host_info["database_path"]
        else:
            config["real_port"] = port
            config["real_host"] = host
            config["real_data_dir"] = data_dir
            config["real_database_path"] = database_path
        return default_name(config)

    config = compute_config()
    config["real_port"] = config["port"]
    config["real_host"] = config["host"]
    config["real_data_dir"] = config["data_dir"]
    config["real_database_path"] = config["database_path"]
    return default_name(config)


def save_config(config_dir: Path, config: Config) -> None:
    """Save configuration to file"""
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "config.json"
    json_config = {k: (str(v.resolve()) if isinstance(v, Path) else v) for k, v in config.items() if k != "config_file"}

    try:
        with config_file.open("w") as f:
            json.dump(json_config, f, indent=2)
    except Exception as e:
        logging.warning(f"Could not save config: {e}")
