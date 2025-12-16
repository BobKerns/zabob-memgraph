"""Configuration management for Zabob Memgraph"""

from collections.abc import Callable
import json
import logging
import os
from pathlib import Path
from typing import Any, NotRequired, TypedDict, Literal, cast, overload


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
    access_log: bool
    backup_on_start: bool
    min_backups: int
    backup_age_days: int
    reload: bool
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


# T = TypeVar('T')


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
    if isinstance(value, expected_type):
        return value
    constructor = cast(Callable[[Any], T], expected_type)
    return constructor(value)


def load_config(config_dir: Path, **settings: None | int | str | Path | bool) -> Config:
    """Load launcher configuration from file or return defaults"""
    config_file = config_dir / "config.json"

    defaults: Config = {
        "port": DEFAULT_PORT,
        "host": "localhost",
        "docker_image": DOCKER_IMAGE,
        "container_name": DEFAULT_CONTAINER_NAME,
        "log_level": "INFO",
        "access_log": True,  # For now.
        "backup_on_start": True,
        "min_backups": 5,
        "backup_age_days": 30,
        "reload": False,
        "config_dir": config_dir,
        "data_dir": config_dir / "data",
        "database_path": Path(os.getenv("MEMGRAPH_DATABASE_PATH", config_dir / "data" / "knowledge_graph.db")),
    }

    settings = {k: v for k, v in settings.items() if v is not None}

    if config_file.exists():
        try:
            with open(config_file) as f:
                raw_user_config = json.load(f)
                user_config = {
                    k: match_type(v, type(defaults[k]))  # type: ignore[literal-required]
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
