"""
Reusable database fixtures for SQLite testing.

Import in conftest.py:

    project_root = Path(__file__).parent
    # Add .dev-library to path
    sys.path.insert(0, str(project_root / ".dev-library"))

    from test_fixtures.pytest.database_fixtures import *  # noqa: E402
"""

import pytest
import sqlite3
import tempfile
import os
from pathlib import Path


@pytest.fixture
def temp_sqlite_db():
    """
    Create a temporary SQLite database that's automatically cleaned up.

    Scope: Function (new database per test)
    Yields: sqlite3.Connection

    Example:
        def test_feature(temp_sqlite_db):
            conn = temp_sqlite_db
            conn.execute("CREATE TABLE test (id INTEGER)")
            # Test with isolated database
    """
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    conn = sqlite3.connect(db_path)

    # Enable WAL mode for thread safety
    conn.execute("PRAGMA journal_mode=WAL")

    yield conn

    # Cleanup
    conn.close()
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def sqlite_connection():
    """
    In-memory SQLite connection with WAL mode.

    Scope: Function
    Yields: sqlite3.Connection

    Example:
        def test_query(sqlite_connection):
            conn = sqlite_connection
            result = conn.execute("SELECT 1").fetchone()
            assert result == (1,)
    """
    conn = sqlite3.connect(':memory:')
    conn.execute("PRAGMA journal_mode=WAL")
    yield conn
    conn.close()


@pytest.fixture
def sqlite_with_schema(temp_sqlite_db):
    """
    SQLite database with common test schema.

    Scope: Function
    Yields: sqlite3.Connection with schema

    Override create_schema() in your conftest.py for custom schema:
        @pytest.fixture
        def sqlite_with_schema(temp_sqlite_db):
            create_my_schema(temp_sqlite_db)
            yield temp_sqlite_db
    """
    conn = temp_sqlite_db

    # Basic schema - override in project conftest.py
    conn.execute('''
        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS observations (
            id INTEGER PRIMARY KEY,
            entity_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (entity_id) REFERENCES entities(id)
        )
    ''')

    conn.commit()
    yield conn


@pytest.fixture
def populated_db(sqlite_with_schema):
    """
    Database with test data.

    Scope: Function
    Yields: sqlite3.Connection with test data

    Override in project conftest.py for custom test data.
    """
    conn = sqlite_with_schema

    # Sample test data
    conn.execute(
        "INSERT INTO entities (name, entity_type) VALUES (?, ?)",
        ("Test Entity", "test")
    )
    entity_id = conn.lastrowid

    conn.execute(
        "INSERT INTO observations (entity_id, content) VALUES (?, ?)",
        (entity_id, "Test observation")
    )

    conn.commit()
    yield conn


@pytest.fixture(scope="session")
def test_data_dir():
    """
    Temporary directory for test data files.

    Scope: Session (shared across tests, cleaned up at end)
    Yields: Path to temporary directory

    Example:
        def test_file_operations(test_data_dir):
            file_path = test_data_dir / "test.txt"
            file_path.write_text("test data")
            # Directory cleaned up after session
    """
    temp_dir = tempfile.mkdtemp(prefix='test_data_')
    yield Path(temp_dir)

    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)
