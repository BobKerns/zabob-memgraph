![zabob banner, AI Memory](../docs/images/zabob-banner.jpg)

# Zabob Memgraph Tests

This directory contains tests for the Zabob Memgraph knowledge graph server.

## Test Types

### Unit Tests
- **test_service_integration.py** - Integration tests for the MCP service layer
- **test_web_service.py** - Tests for the web service endpoints

### UI Tests (Playwright)
- **test_ui_playwright.py** - End-to-end browser tests for the D3.js visualization

## Running Tests

### All Tests
```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run with coverage
uv run pytest --cov=memgraph
```

### Specific Test Files
```bash
# Run only UI tests
uv run pytest tests/test_ui_playwright.py

# Run only service tests
uv run pytest tests/test_service_integration.py
```

### Specific Tests
```bash
# Run a specific test by name
uv run pytest tests/test_ui_playwright.py::test_page_loads -v

# Run tests matching a pattern
uv run pytest -k "zoom" -v
```

## Test Server Architecture

The Playwright UI tests automatically start their own test server with:
- **Isolated database**: Uses a temporary SQLite database that's cleaned up after tests
- **Dynamic port**: Finds a free port automatically to avoid conflicts
- **Session scope**: Server starts once per test session and is shared across tests
- **Automatic cleanup**: Server and database are cleaned up when tests complete

This ensures:
- ✅ Tests don't interfere with running production servers
- ✅ Tests can run in CI without port conflicts
- ✅ Each test run starts with a clean database state
- ✅ Tests can run in parallel without conflicts

### Test Server Configuration

The test server is configured via the `test_server` fixture in [conftest.py](conftest.py):

```python
@pytest.fixture(scope="session")
def test_server(port, tmp_path_factory):
    """Start a test server with temporary database on a free port"""
    # Creates temp database, starts server on free port
    # Returns: {"port": int, "base_url": str, "db_path": Path}
```

Environment variables used:
- `MEMGRAPH_PORT` - Dynamic free port
- `MEMGRAPH_HOST` - localhost
- `MEMGRAPH_DATABASE_PATH` - Temporary test database
- `MEMGRAPH_LOG_LEVEL` - WARNING (to reduce test noise)

## CI Integration

Tests run automatically in GitHub Actions on:
- Push to `main` or `develop` branches
- Pull requests to `main`

The CI workflow:
1. Installs Python and uv
2. Installs project dependencies with `uv sync --extra dev`
3. Installs Playwright browsers with `playwright install --with-deps chromium`
4. Runs all tests including UI tests

See [.github/workflows/ci-cd.yml](../.github/workflows/ci-cd.yml) for the full CI configuration.

## Playwright Browser Setup

### First Time Setup
```bash
# Install Playwright browsers (only needed once)
uv run playwright install chromium
```

### CI/CD
Browsers are automatically installed in the CI pipeline via:
```bash
uv run playwright install --with-deps chromium
```

## Test Output

Test artifacts are stored in `tests/out/<test-file>/<test-name>/`:
- Server logs
- Client logs
- Test artifacts
- Screenshots (on failure)

## Debugging Tests

### Run with Output
```bash
# Show server output
uv run pytest tests/test_ui_playwright.py -v -s

# Show browser (headed mode)
uv run pytest tests/test_ui_playwright.py --headed
```

### Check Logs
```bash
# Server logs are in test output directory
cat tests/out/test_ui_playwright/test_page_loads/service.log
```

### Manual Server Testing
The test server can also be started manually for debugging:
```bash
# Set test environment variables
export MEMGRAPH_PORT=9999
export MEMGRAPH_DATABASE_PATH=/tmp/test_db.sqlite
export MEMGRAPH_LOG_LEVEL=DEBUG

# Run server
python main.py
```

## Writing New Tests

### UI Tests
UI tests use Playwright for browser automation. Example:

```python
def test_new_feature(page: Page, base_url: str):
    """Test description"""
    page.goto(base_url)

    # Interact with page
    page.click("#my-button")

    # Assert results
    expect(page.locator("#result")).to_have_text("Expected")
```

The `base_url` fixture automatically provides the test server URL.

### Service Tests
Service tests can use the `test_server` fixture directly:

```python
def test_api_endpoint(test_server):
    """Test API endpoint"""
    import requests

    response = requests.get(f"{test_server['base_url']}/api/endpoint")
    assert response.status_code == 200
```

## Troubleshooting

**Port already in use**: Tests find a free port automatically, but if you see port conflicts:
```bash
# Kill any hanging test servers
pkill -f "python.*main.py"
```

**Playwright not found**: Install browsers:
```bash
uv run playwright install chromium
```

**Database locked errors**: Each test uses an isolated database. If you see locking errors, check that the test server fixture is properly cleaning up.

**CI failures**: Check the workflow logs in GitHub Actions. Common issues:
- Missing Playwright installation step
- Missing dependencies in pyproject.toml
- Port conflicts (shouldn't happen with dynamic ports)

