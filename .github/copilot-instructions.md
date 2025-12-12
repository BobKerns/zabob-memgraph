# Copilot Coding Agent Instructions

## Project Overview

**Zabob Memgraph** is a Model Context Protocol (MCP) server that provides HTTP endpoints for knowledge graph visualization and interaction. It's part of the Zabob AI assistant ecosystem and designed for thread-safe multi-client support with Docker deployment.

- **Primary Language**: Python 3.12+
- **Framework**: FastAPI with uvicorn
- **Database**: SQLite with WAL mode for thread-safety
- **Visualization**: D3.js web interface
- **Package Manager**: uv (modern Python package manager)
- **Development Tools**: pytest, mypy, ruff, black, isort

## Project Structure

```
zabob-memgraph/
├── .github/                      # GitHub configuration
│   ├── workflows/                # CI/CD workflows
│   └── copilot-instructions.md   # This file
├── memgraph/                     # Core package
│   ├── server.py                 # FastAPI application
│   ├── sqlite_backend.py         # Thread-safe SQLite backend
│   ├── knowledge_live.py         # Knowledge graph data layer
│   ├── *_mcp_client.py           # MCP client implementations (docker, stdio, subprocess, real, etc.)
│   ├── simple_mcp_bridge.py      # Simple MCP bridge implementation
│   ├── fastmcp_client.py         # FastMCP client
│   ├── mcp_protocol_client.py    # MCP protocol client
│   └── web/                      # Static web assets for visualization
├── tests/                        # Test suite
├── docs/                         # Documentation and images
├── main.py                       # Server entrypoint
├── zabob-memgraph-dev.py         # Development CLI tool
├── zabob-memgraph-launcher.py    # Process management launcher
├── zabob-memgraph-install.py     # Installation script
├── pyproject.toml                # Project configuration
├── uv.lock                       # uv lock file
├── Dockerfile                    # Docker image definition
└── docker-compose.yml            # Docker Compose configuration
```

## Standards and Conventions

### Code Style

- **Python Version**: Requires Python 3.12+
- **Formatting**: Use Black with line length 88
- **Import Sorting**: Use isort with Black profile (line length 88)
- **Linting**: Use ruff with line length 120, target version py312
- **Type Checking**: Use mypy with strict mode enabled (Python 3.12)
- **Configuration Note**: Black is configured for line length 88, while ruff allows up to 120 characters. Follow Black's 88 character limit when formatting code to maintain consistency.
- **Docstrings**: Use triple-quoted docstrings for modules, classes, and functions
- **String Quotes**: Prefer double quotes for strings (Black default)
- **Naming Conventions**:
  - `snake_case` for functions, variables, and module names
  - `PascalCase` for class names
  - `UPPER_CASE` for constants
  - Prefix private attributes/methods with single underscore `_`

### File Organization

- Keep module files focused on a single responsibility
- Place all application code in the `memgraph/` package
- Store tests in `tests/` directory matching the package structure
- Use `__init__.py` to expose public APIs from packages
- Static web assets go in `memgraph/web/`

### Documentation

- Add docstrings to all public functions, classes, and modules
- Use inline comments sparingly, only when logic is non-obvious
- Keep README.md up to date with feature changes
- Document API endpoints and their parameters

### Dependencies

- Use uv for dependency management (`uv add <package>`)
- Pin dependencies with version constraints in `pyproject.toml`
- Separate dev dependencies in `[project.optional-dependencies]`
- Only add dependencies if absolutely necessary
- Prefer standard library when possible

## Build and Test Commands

### Development Setup

```bash
# Install dependencies
./zabob-memgraph-dev.py install

# Run in development mode with auto-reload
./zabob-memgraph-dev.py run --reload --port 8080
```

### Quality Checks

```bash
# Run type checking and linting (runs both mypy and ruff check)
./check_types.py
# Or run individually:
uv run mypy --strict memgraph/
uv run ruff check memgraph/

# Format code
./zabob-memgraph-dev.py format
# Or: uv run ruff format .

# Run tests (uses isolated test server with temp database)
./zabob-memgraph-dev.py test
# Or: uv run pytest -v

# Run specific test file
uv run pytest tests/test_ui_playwright.py -v

# Run specific test
uv run pytest tests/test_ui_playwright.py::test_page_loads -v
```

### Docker

```bash
# Build Docker image
./zabob-memgraph-dev.py build

# Run with Docker
./zabob-memgraph-dev.py docker-run --detach

# Stop Docker containers
./zabob-memgraph-dev.py docker-stop
```

## Expected Behavior and Architecture

### Thread-Safety Requirements

- **Critical**: All database operations must be thread-safe
- Use SQLite with WAL mode enabled for concurrent reads
- Properly handle connection pooling and retries for locked databases
- Avoid shared mutable state without proper locking

### Backend Selection Pattern

The server uses a fallback pattern to select the best available backend:
1. SQLite backend (preferred, production)
2. Docker MCP client
3. Stdio MCP client
4. Simple MCP bridge
5. Real MCP client
6. Direct MCP client

This ensures graceful degradation if certain backends are unavailable.

### API Design

- All endpoints should return JSON responses
- Use FastAPI's built-in validation with Pydantic models
- Include proper HTTP status codes
- Add appropriate CORS headers for web client access
- Follow REST conventions for endpoint naming

### Configuration

- Store runtime data in `~/.zabob-memgraph/`
- Use environment variables for Docker/deployment configs:
  - `MEMGRAPH_HOST`, `MEMGRAPH_PORT`, `MEMGRAPH_LOG_LEVEL`, `MEMGRAPH_CONFIG_DIR`
- Support both config file (`config.json`) and environment variables
- Provide sensible defaults

### Database Management

- Always create backups before operations that modify schema
- Keep only the 5 most recent backups (configurable via `max_backups`)
- Use automatic backup rotation
- Log all database operations

## Testing Guidelines

### Test Structure

- Write tests using pytest
- Place tests in `tests/` directory
- Use descriptive test names: `test_<feature>_<scenario>_<expected_result>`
- Mock external dependencies (MCP clients, network calls)
- Test thread-safety for concurrent database operations
- Include edge cases and error conditions
- Maintain existing test structure and patterns

### Test Server Architecture

**Important**: Playwright UI tests automatically start their own isolated test server:
- **Isolated Database**: Uses a temporary SQLite database in a temp directory
- **Dynamic Port**: Finds a free port automatically to avoid conflicts
- **Session Scope**: Server starts once and is shared across all tests in a session
- **Automatic Cleanup**: Server and database are cleaned up after tests complete

This ensures:
- Tests don't interfere with running production servers on port 8080
- Tests can run in CI/CD without port conflicts
- Each test run starts with a clean database state
- Multiple test runs can execute simultaneously

### Test Environment Variables

The test server fixture sets these environment variables:
- `MEMGRAPH_PORT` - Dynamic free port (e.g., 50123)
- `MEMGRAPH_HOST` - localhost
- `MEMGRAPH_DATABASE_PATH` - Temporary test database path
- `MEMGRAPH_LOG_LEVEL` - WARNING (reduces log noise)

### Writing UI Tests

UI tests use the `base_url` fixture which automatically provides the test server URL:

```python
def test_new_feature(page: Page, base_url: str):
    """Test description"""
    page.goto(base_url)  # Uses test server, not production

    # Interact with page
    page.click("#my-button")

    # Assert results
    expect(page.locator("#result")).to_have_text("Expected")
```

### First-Time Playwright Setup

Before running UI tests for the first time:
```bash
# Install Playwright browsers (only needed once)
uv run playwright install chromium
```

### CI/CD Integration

The CI pipeline automatically:
1. Installs Playwright browsers: `playwright install --with-deps chromium`
2. Runs all tests including UI tests with isolated test servers
3. No manual server management required

## Security Considerations

- Never commit database files (`.db`, `.db-shm`, `.db-wal`)
- Never commit secrets or API keys
- Validate and sanitize all user inputs
- Use parameterized SQL queries to prevent injection
- Set appropriate CORS origins in production (not `"*"`)
- Review all changes that handle user data

## Common Patterns

### Error Handling

```python
try:
    # Operation
    result = perform_operation()
except SpecificException as e:
    logger.error(f"Operation failed: {e}")
    raise HTTPException(status_code=500, detail=str(e))
```

### Logging

```python
import logging
logger = logging.getLogger(__name__)

# Use appropriate levels
logger.debug("Detailed diagnostic info")
logger.info("General informational messages")
logger.warning("Warning messages")
logger.error("Error messages")
```

### FastAPI Route Definition

```python
@app.get("/api/endpoint")
async def endpoint_name() -> ResponseType:
    """Brief description of what this endpoint does"""
    # Implementation
    return response
```

## What NOT to Do

- ❌ Don't modify working code without a specific reason
- ❌ Don't remove or modify existing tests unless they're broken
- ❌ Don't add unnecessary dependencies
- ❌ Don't use `from module import *`
- ❌ Don't commit commented-out code (use git history instead)
- ❌ Don't mix formatting changes with functional changes
- ❌ Don't break thread-safety guarantees
- ❌ Don't bypass the existing backend selection logic
- ❌ Don't modify the launcher or installer scripts without careful testing

## External Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [SQLite WAL Mode](https://www.sqlite.org/wal.html)
- [uv Documentation](https://docs.astral.sh/uv/)
- [Project README](../README.md)

## Additional Notes

- This is part of the Zabob ecosystem - maintain compatibility with other Zabob tools
- The `zabob-` prefix is intentional for ecosystem identification
- Prioritize backward compatibility when making changes
- When in doubt about implementation details, ask for clarification via issue comments
- Always test Docker deployments after making server changes
- Verify thread-safety for any changes to database operations
- **Line Length**: Black enforces 88 characters, ruff allows up to 120. Prefer Black's formatting (88 chars) for consistency.

## Questions or Clarifications

If you need clarification on any aspect of the codebase that isn't covered here:
1. Check the README.md and docs/ directory first
2. Look for similar existing implementations in the codebase
3. Ask for clarification via issue comments
4. Review related test files for usage examples
