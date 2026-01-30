![Zabob Banner](../docs-assets/images/zabob-banner-library.jpg)

# Test Fixtures

Reusable test fixtures and utilities for Zabob projects.

## Overview

This directory contains common testing patterns and fixtures that can be imported into project test suites. These fixtures follow pytest conventions and are designed for easy integration.

## Structure

```text
test-fixtures/
├── pytest/
│   ├── async_fixtures.py       # Async test utilities
│   ├── server_fixtures.py      # Test server patterns
│   └── database_fixtures.py    # Database test fixtures
└── playwright/
    ├── page_fixtures.py        # Playwright page fixtures
    └── test_helpers.js         # Browser-side test utilities
```

## Usage

### Pytest Fixtures

Import fixtures in your `conftest.py`:

```python
# tests/conftest.py
import sys
from pathlib import Path

# Add dev-library to path
dev_lib = Path(__file__).parent.parent / '.dev-library'
sys.path.insert(0, str(dev_lib))

# Import fixtures
from test_fixtures.pytest.async_fixtures import *
from test_fixtures.pytest.server_fixtures import *
from test_fixtures.pytest.database_fixtures import *
```

Then use in your tests:

```python
# tests/test_feature.py
def test_with_temp_db(temp_sqlite_db):
    """Uses temp database fixture"""
    conn = temp_sqlite_db
    # Test with isolated database
```

### Playwright Fixtures

Configure in `conftest.py`:

```python
from test_fixtures.playwright.page_fixtures import *

# Fixtures automatically available:
# - base_url (test server URL)
# - authenticated_page (logged-in page)
```

## Available Fixtures

### Async Fixtures (`pytest/async_fixtures.py`)

- **`async_client`** - AsyncClient for testing FastAPI apps
- **`event_loop`** - Properly configured event loop
- **`async_context`** - Async context manager for cleanup

### Server Fixtures (`pytest/server_fixtures.py`)

- **`test_server`** - Isolated test server on free port
- **`base_url`** - URL of test server
- **`wait_for_server`** - Utility to wait for server startup

### Database Fixtures (`pytest/database_fixtures.py`)

- **`temp_sqlite_db`** - Temporary SQLite database
- **`sqlite_connection`** - Connection with WAL mode enabled
- **`populated_db`** - Database with test data

### Playwright Fixtures (`playwright/page_fixtures.py`)

- **`browser_context`** - Isolated browser context
- **`page`** - Clean page for each test
- **`authenticated_page`** - Pre-authenticated page

## Best Practices

1. **Isolation**: Each fixture should create isolated resources
2. **Cleanup**: Use `yield` to ensure cleanup happens
3. **Composition**: Build complex fixtures from simple ones
4. **Documentation**: Document fixture scope and cleanup behavior

## Example: Custom Fixture

```python
# project-specific conftest.py
import pytest
from .dev_library.test_fixtures.pytest.database_fixtures import temp_sqlite_db

@pytest.fixture
def app_with_db(temp_sqlite_db):
    """Application instance with test database"""
    from myapp import create_app

    app = create_app(database=temp_sqlite_db)
    yield app
    app.cleanup()
```

## Contributing

When adding fixtures to this library:

1. Make them generic and reusable
2. Document scope and cleanup behavior
3. Include usage examples
4. Test across multiple projects
