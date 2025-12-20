"""Unit tests for configuration loading and defaulting logic"""

import json
from pathlib import Path, PosixPath
from typing import Any
import pytest

from memgraph.config import (
    load_config,
    save_config,
    DEFAULT_PORT,
    DEFAULT_CONFIG,
    Config,
)


@pytest.fixture
def clean_config_dir(tmp_path: Path) -> Path:
    """Provide a clean temporary config directory"""
    config_dir = tmp_path / "test_config"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


@pytest.fixture
def config_file_with_values(clean_config_dir: Path) -> tuple[Path, dict[str, Any]]:
    """Create a config file with test values"""
    config_file = clean_config_dir / "config.json"
    test_values = {
        "name": "test-server",
        "port": 7890,
        "host": "test.example.com",
        "log_level": "DEBUG",
        "access_log": False,
        "container_name": "test-container",
    }
    with open(config_file, 'w') as f:
        json.dump(test_values, f)
    return clean_config_dir, test_values


@pytest.fixture
def mock_in_docker(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock IN_DOCKER environment"""
    monkeypatch.setenv('DOCKER_CONTAINER', '1')
    # Need to reimport to pick up the new env var
    import memgraph.config
    monkeypatch.setattr(memgraph.config, 'IN_DOCKER', True)


class TestConfigDefaulting:
    """Test configuration defaulting with various sources"""

    def test_defaults_no_file_no_args(self, clean_config_dir: Path) -> None:
        """Test: No config file, no arguments -> pure defaults"""
        # Clear cache to ensure fresh load
        load_config.cache_clear()

        config = load_config(clean_config_dir)

        # Should get defaults for all values
        assert config['port'] == DEFAULT_CONFIG['port']
        assert config['host'] == DEFAULT_CONFIG['host']
        assert config['log_level'] == DEFAULT_CONFIG['log_level']
        assert config['access_log'] == DEFAULT_CONFIG['access_log']
        assert config['container_name'] == DEFAULT_CONFIG['container_name']
        assert config['config_dir'] == clean_config_dir

        # Real values should match non-docker values
        assert config['real_port'] == config['port']
        assert config['real_host'] == config['host']
        assert config['real_data_dir'] == config['data_dir']
        assert config['real_database_path'] == config['database_path']

        # Name should be defaulted
        assert config['name'] == "zabob-memgraph"

    def test_defaults_with_file_no_args(self, config_file_with_values: tuple[Path, dict[str, Any]]) -> None:
        """Test: Config file present, no arguments -> file values override defaults"""
        load_config.cache_clear()
        config_dir, file_values = config_file_with_values

        config = load_config(config_dir)

        # Should get values from file
        assert config['name'] == file_values['name']
        assert config['port'] == file_values['port']
        assert config['host'] == file_values['host']
        assert config['log_level'] == file_values['log_level']
        assert config['access_log'] == file_values['access_log']
        assert config['container_name'] == file_values['container_name']

        # Real values should match
        assert config['real_port'] == file_values['port']
        assert config['real_host'] == file_values['host']

    def test_defaults_no_file_with_args(self, clean_config_dir: Path) -> None:
        """Test: No config file, arguments provided -> arguments override defaults"""
        load_config.cache_clear()

        config = load_config(
            clean_config_dir,
            name="arg-server",
            port=8901,
            host="arg.example.com",
            log_level="WARNING",
            access_log=False,
        )

        # Should get values from arguments
        assert config['name'] == "arg-server"
        assert config['port'] == 8901
        assert config['host'] == "arg.example.com"
        assert config['log_level'] == "WARNING"
        assert config['access_log'] is False

        # Real values should match
        assert config['real_port'] == 8901
        assert config['real_host'] == "arg.example.com"

    def test_defaults_with_file_and_args(self, config_file_with_values: tuple[Path, dict[str, Any]]) -> None:
        """Test: Config file + arguments -> arguments override file and defaults"""
        load_config.cache_clear()
        config_dir, file_values = config_file_with_values

        config = load_config(
            config_dir,
            name="override-name",
            port=9012,
            # Don't override host - should come from file
            log_level="ERROR",
        )

        # Arguments should override file
        assert config['name'] == "override-name"
        assert config['port'] == 9012
        assert config['log_level'] == "ERROR"

        # File values that weren't overridden
        assert config['host'] == file_values['host']
        assert config['access_log'] == file_values['access_log']

        # Real values should match overridden values
        assert config['real_port'] == 9012


class TestDockerConfigDefaulting:
    """Test configuration defaulting in Docker mode"""

    def test_docker_no_file_no_args(self, clean_config_dir: Path) -> None:
        """Test: Docker mode, no config file, no arguments"""
        load_config.cache_clear()

        config = load_config(clean_config_dir, docker=True)

        # Docker should force host to 0.0.0.0 and port to DEFAULT_PORT
        assert config['host'] == '0.0.0.0'
        assert config['port'] == DEFAULT_PORT

        # Database path should be adjusted to /data mount
        assert str(config['database_path']).startswith('/data')

        # Real values should reflect original config
        assert config['real_port'] == DEFAULT_CONFIG['port']
        assert config['real_host'] == DEFAULT_CONFIG['host']

    def test_docker_with_file_no_args(self, config_file_with_values: tuple[Path, dict[str, Any]]) -> None:
        """Test: Docker mode, config file present, no arguments"""
        load_config.cache_clear()
        config_dir, file_values = config_file_with_values

        config = load_config(config_dir, docker=True)

        # Docker should force host to 0.0.0.0 and port to DEFAULT_PORT
        assert config['host'] == '0.0.0.0'
        assert config['port'] == DEFAULT_PORT

        # Database path should be adjusted
        assert str(config['database_path']).startswith('/data')

        # Real values should reflect file config
        assert config['real_port'] == file_values['port']
        assert config['real_host'] == file_values['host']

        # Other file values should be preserved
        assert config['log_level'] == file_values['log_level']
        assert config['access_log'] == file_values['access_log']

    def test_docker_no_file_with_args(self, clean_config_dir: Path) -> None:
        """Test: Docker mode, no config file, arguments provided"""
        load_config.cache_clear()

        config = load_config(
            clean_config_dir,
            docker=True,
            name="docker-arg-server",
            port=8901,
            host="arg.example.com",
            log_level="WARNING",
        )

        # Docker should force host to 0.0.0.0 and port to DEFAULT_PORT
        assert config['host'] == '0.0.0.0'
        assert config['port'] == DEFAULT_PORT

        # Real values should reflect arguments
        assert config['real_port'] == 8901
        assert config['real_host'] == "arg.example.com"

        # Other arguments should be preserved
        assert config['name'] == "docker-arg-server"
        assert config['log_level'] == "WARNING"

    def test_docker_with_file_and_args(self, config_file_with_values: tuple[Path, dict[str, Any]]) -> None:
        """Test: Docker mode, config file + arguments"""
        load_config.cache_clear()
        config_dir, file_values = config_file_with_values

        config = load_config(
            config_dir,
            docker=True,
            name="docker-override",
            port=9012,
            log_level="ERROR",
        )

        # Docker should force host to 0.0.0.0 and port to DEFAULT_PORT
        assert config['host'] == '0.0.0.0'
        assert config['port'] == DEFAULT_PORT

        # Real values should reflect arguments
        assert config['real_port'] == 9012

        # Arguments should override file
        assert config['name'] == "docker-override"
        assert config['log_level'] == "ERROR"

        # File values that weren't overridden
        assert config['access_log'] == file_values['access_log']


class TestConfigNameDefaulting:
    """Test name defaulting special cases"""

    def test_name_defaults_to_zabob_memgraph_on_default_port(self, clean_config_dir: Path) -> None:
        """Test: Empty name on default port -> 'zabob-memgraph'"""
        load_config.cache_clear()

        config = load_config(clean_config_dir, name="", port=DEFAULT_PORT)

        assert config['name'] == "zabob-memgraph"

    def test_name_defaults_with_port_suffix_on_non_default_port(self, clean_config_dir: Path) -> None:
        """Test: Empty name on non-default port -> 'zabob-memgraph-{port}'"""
        load_config.cache_clear()

        config = load_config(clean_config_dir, name="", port=7890)

        assert config['name'] == "zabob-memgraph-7890"

    def test_name_preserved_when_provided(self, clean_config_dir: Path) -> None:
        """Test: Explicit name is preserved regardless of port"""
        load_config.cache_clear()

        config = load_config(clean_config_dir, name="custom-name", port=7890)

        assert config['name'] == "custom-name"

    def test_name_whitespace_stripped_and_defaulted(self, clean_config_dir: Path) -> None:
        """Test: Whitespace-only name is treated as empty"""
        load_config.cache_clear()

        config = load_config(clean_config_dir, name="   ", port=DEFAULT_PORT)

        assert config['name'] == "zabob-memgraph"


class TestConfigDatabasePathHandling:
    """Test database path handling in Docker mode"""

    def test_docker_database_path_file(self, clean_config_dir: Path, tmp_path: Path) -> None:
        """Test: Docker mode with database_path pointing to a file"""
        load_config.cache_clear()

        # Create a fake database file
        db_file = tmp_path / "custom.db"
        db_file.touch()

        config = load_config(clean_config_dir, docker=True, database_path=db_file)

        # Should map to /data/custom.db inside container
        assert config['database_path'] == PosixPath('/data/custom.db')
        assert config['data_dir'] == db_file.parent

    def test_docker_database_path_directory(self, clean_config_dir: Path, tmp_path: Path) -> None:
        """Test: Docker mode with database_path pointing to a directory"""
        load_config.cache_clear()

        # Create a directory
        db_dir = tmp_path / "db_dir"
        db_dir.mkdir()

        config = load_config(clean_config_dir, docker=True, database_path=db_dir)

        # Should use default filename in /data
        assert config['database_path'] == PosixPath('/data/knowledge_graph.db')
        assert config['data_dir'] == db_dir

    def test_docker_database_path_nonexistent_db_suffix(self, clean_config_dir: Path, tmp_path: Path) -> None:
        """Test: Docker mode with nonexistent path ending in .db"""
        load_config.cache_clear()

        db_path = tmp_path / "data" / "new.db"

        config = load_config(clean_config_dir, docker=True, database_path=db_path)

        # Should map to /data/new.db
        assert config['database_path'] == PosixPath('/data/new.db')
        assert config['data_dir'] == db_path.parent


class TestConfigSaveLoad:
    """Test save and load round-trip"""

    def test_save_and_load_preserves_values(self, clean_config_dir: Path) -> None:
        """Test: Save config, then load it back"""
        load_config.cache_clear()

        # Create config with custom values
        original_config = load_config(
            clean_config_dir,
            name="save-test",
            port=8888,
            host="save.test.com",
            log_level="DEBUG",
        )

        # Save it
        save_config(clean_config_dir, original_config)

        # Clear cache and load again
        load_config.cache_clear()
        loaded_config = load_config(clean_config_dir)

        # Values should match
        assert loaded_config['name'] == original_config['name']
        assert loaded_config['port'] == original_config['port']
        assert loaded_config['host'] == original_config['host']
        assert loaded_config['log_level'] == original_config['log_level']
