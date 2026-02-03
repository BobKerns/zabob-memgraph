# Test-Driven Development Skill

Cross-project testing best practices and patterns.

## Description

Comprehensive approach to testing that ensures code correctness, prevents regressions, and enables confident refactoring. Focuses on isolated, reproducible tests.

## When to Apply

- Developing new features
- Fixing bugs
- Refactoring existing code
- Integration work
- Anytime you change code

## Core Principles

### 1. Test Isolation

Each test should run independently without external dependencies:

```python
# Good: Isolated test with its own database
@pytest.fixture
def test_db():
    """Create temporary test database"""
    db_path = tempfile.mktemp(suffix='.db')
    conn = sqlite3.connect(db_path)
    # Setup schema...
    yield conn
    conn.close()
    os.unlink(db_path)

def test_feature(test_db):
    # Test uses isolated database
    result = query_database(test_db)
    assert result == expected
```

```python
# Bad: Tests depend on shared state
def test_feature():
    # Uses production database - not isolated!
    result = query_database(PRODUCTION_DB)
    assert result == expected
```

### 2. Test Server Architecture

UI tests need isolated server instances:

```python
# conftest.py - Pytest fixtures
@pytest.fixture(scope="session")
def test_server():
    """Start isolated test server on free port"""
    port = find_free_port()
    db_path = tempfile.mktemp(suffix='.db')

    # Set environment for test server
    os.environ['MEMGRAPH_PORT'] = str(port)
    os.environ['MEMGRAPH_DATABASE_PATH'] = db_path
    os.environ['MEMGRAPH_LOG_LEVEL'] = 'WARNING'

    # Start server in background
    process = subprocess.Popen([
        sys.executable, '-m', 'memgraph',
        '--port', str(port),
        '--database', db_path
    ])

    # Wait for server to be ready
    wait_for_server(f'http://localhost:{port}/health')

    yield f'http://localhost:{port}'

    # Cleanup
    process.terminate()
    process.wait()
    os.unlink(db_path)
```

**Benefits:**

- Tests don't interfere with running servers
- Can run multiple test sessions simultaneously
- Clean state for each test run
- No port conflicts

### 3. Comprehensive Test Coverage

Cover happy paths, edge cases, and error conditions:

```python
# Happy path
def test_search_finds_matches():
    """Search returns matching entities"""
    result = search("keyword")
    assert len(result) > 0
    assert "keyword" in result[0].name.lower()

# Edge case
def test_search_empty_query():
    """Empty search returns empty results"""
    result = search("")
    assert len(result) == 0

# Error condition
def test_search_invalid_characters():
    """Search handles special characters safely"""
    result = search("'; DROP TABLE entities; --")
    # Should not crash, returns safe results
    assert isinstance(result, list)
```

### 4. Run Tests as You Go

Don't wait until the end to test:

```bash
# After writing new code
pytest tests/test_new_feature.py -v

# After fixing a bug
pytest tests/test_bugfix.py -v

# Before committing
pytest -v
```

### 5. Verbose Output Always

Always run tests with verbose output to see actual failures:

```bash
# Good: See what actually failed
pytest tests/test_file.py -v --tb=short

# Better: More context on failures
pytest tests/test_file.py -v --tb=long

# Bad: No visibility into failures
pytest tests/test_file.py
```

## Test Patterns

### Pattern 1: Async Tests

```python
import pytest

@pytest.mark.asyncio
async def test_async_operation():
    """Test async function"""
    result = await async_function()
    assert result == expected
```

**Common pitfall:**

```python
# Wrong: Missing @pytest.mark.asyncio
async def test_async_operation():
    result = await async_function()  # Will fail!
```

### Pattern 2: Parametrized Tests

```python
@pytest.mark.parametrize("input,expected", [
    ("simple", ["simple"]),
    ("multi word", ["multi", "word"]),
    ("", []),
])
def test_tokenize(input, expected):
    """Test tokenization with various inputs"""
    assert tokenize(input) == expected
```

### Pattern 3: Fixture Composition

```python
@pytest.fixture
def database():
    """Provide test database"""
    db = create_test_db()
    yield db
    db.close()

@pytest.fixture
def populated_database(database):
    """Database with test data"""
    insert_test_data(database)
    return database

def test_with_data(populated_database):
    """Test uses pre-populated database"""
    result = query(populated_database)
    assert len(result) > 0
```

### Pattern 4: UI Testing with Playwright

```python
from playwright.sync_api import Page, expect

def test_ui_feature(page: Page, base_url: str):
    """Test UI functionality"""
    page.goto(base_url)

    # Interact with page
    page.fill("#search-input", "test query")
    page.click("#search-button")

    # Assert results
    expect(page.locator(".search-result")).to_be_visible()
    expect(page.locator(".result-title")).to_contain_text("test query")
```

**CSS Selector Tips:**

- Use specific classes: `.search-result` not just `.result`
- Avoid overly specific selectors that break easily
- Use data attributes for test hooks: `[data-testid="search-button"]`

## Real-World Example: Search Feature Testing

```python
# tests/test_search_nodes.py
import pytest

@pytest.mark.asyncio
async def test_entity_name_prioritization():
    """Entities with name matches should appear before observation matches"""
    # Setup: Create test entities
    backend = SqliteBackend(":memory:")
    await backend.initialize()

    await backend.create_entity("target-entity", "test")
    await backend.create_entity("other-entity", "test")
    await backend.add_observation("other-entity", "contains target keyword")

    # Execute: Search for "target"
    results = await backend.search_nodes("target")

    # Verify: Name match comes first
    assert len(results) == 2
    assert results[0]["name"] == "target-entity"  # Name match first
    assert results[1]["name"] == "other-entity"   # Observation match second

@pytest.mark.asyncio
async def test_observation_sorting_with_many_observations():
    """Matching observations should be sorted before non-matching"""
    backend = SqliteBackend(":memory:")
    await backend.initialize()

    await backend.create_entity("entity", "test")
    # Add observations in specific order
    await backend.add_observation("entity", "First without keyword")
    await backend.add_observation("entity", "Second with TARGET")
    await backend.add_observation("entity", "Third without keyword")

    results = await backend.search_nodes("TARGET")

    # Verify: Matching observation appears first
    assert len(results) == 1
    entity = results[0]
    assert entity["observations"][0] == "Second with TARGET"
    # Non-matching observations follow, in creation order
    assert entity["observations"][1] == "First without keyword"
    assert entity["observations"][2] == "Third without keyword"
```

## Common Pitfalls

### Sharing State Between Tests

❌ **Wrong:**

```python
# Global state causes tests to interfere
shared_db = create_database()

def test_a():
    insert_data(shared_db, "test")
    assert count(shared_db) == 1

def test_b():
    # Fails if test_a ran first!
    assert count(shared_db) == 0
```

✅ **Correct:**

```python
@pytest.fixture
def isolated_db():
    db = create_database()
    yield db
    db.close()

def test_a(isolated_db):
    insert_data(isolated_db, "test")
    assert count(isolated_db) == 1

def test_b(isolated_db):
    # Each test gets fresh database
    assert count(isolated_db) == 0
```

### Not Testing Edge Cases

❌ **Wrong:**

```python
def test_search():
    # Only tests happy path
    result = search("valid query")
    assert len(result) > 0
```

✅ **Correct:**

```python
def test_search_valid_query():
    result = search("valid query")
    assert len(result) > 0

def test_search_empty_query():
    result = search("")
    assert len(result) == 0

def test_search_special_characters():
    result = search("'; DROP TABLE;")
    assert isinstance(result, list)  # Doesn't crash

def test_search_unicode():
    result = search("émojis 🔍")
    assert isinstance(result, list)
```

### Brittle Selectors in UI Tests

❌ **Wrong:**

```python
# Breaks if styling changes
page.click("div > div > button:nth-child(3)")
```

✅ **Correct:**

```python
# Semantic selector using test IDs
page.click("[data-testid='search-button']")

# Or stable classes
page.click(".search-button")
```

## Test Organization

```text
tests/
├── conftest.py              # Shared fixtures
├── test_backend.py          # Backend unit tests
├── test_api.py              # API integration tests
├── test_ui_playwright.py    # UI end-to-end tests
└── README.md                # Testing documentation
```

**Fixture hierarchy:**

```python
# conftest.py - Session-scoped fixtures
@pytest.fixture(scope="session")
def test_server():
    # Start once per session
    pass

# Function-scoped fixtures
@pytest.fixture
def clean_database():
    # New database per test
    pass
```

## Quick Reference

**Run tests:**

```bash
pytest tests/test_file.py -v              # Single file
pytest tests/test_file.py::test_name -v   # Specific test
pytest -v                                  # All tests
pytest -v --tb=short                       # Less verbose tracebacks
pytest -vvv --tb=long                      # Maximum verbosity
```

**Async tests:**

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await async_call()
    assert result == expected
```

**Parametrized tests:**

```python
@pytest.mark.parametrize("input,expected", [
    (case1, result1),
    (case2, result2),
])
def test_cases(input, expected):
    assert function(input) == expected
```

**Fixtures:**

```python
@pytest.fixture
def resource():
    obj = create_resource()
    yield obj
    obj.cleanup()
```

**UI tests:**

```python
def test_ui(page: Page, base_url: str):
    page.goto(base_url)
    page.click(".button")
    expect(page.locator(".result")).to_be_visible()
```

## Integration with CI/CD

Tests should run automatically on every commit:

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install dependencies
        run: |
          uv sync
          playwright install chromium
      - name: Run tests
        run: uv run pytest -v
```

## Further Reading

- [Pytest Documentation](https://docs.pytest.org/)
- [Playwright Testing](https://playwright.dev/python/)
- [Python Async Testing](https://pytest-asyncio.readthedocs.io/)
