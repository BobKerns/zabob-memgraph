![Zabob Memory Holodeck](images/zabob-banner.jpg)

# Docker-Based Testing

This project uses Docker for all quality checks and tests, ensuring consistency between local development and CI/CD.

## Quick Start

```bash
# Run all tests (lint, typecheck, unit, UI)
./docker-test.sh

# Or run the Docker image directly
docker run --rm zabob-memgraph-test:latest

# Run specific test suite
TEST_TARGET=lint ./docker-test.sh
TEST_TARGET=unit ./docker-test.sh
```

## Why Docker for Testing?

✅ **Consistent environment** - Same setup locally and in CI
✅ **No manual setup** - No need to install Python, Node.js, Playwright
✅ **Fast iteration** - Docker layer caching speeds up repeated runs
✅ **Isolated** - Clean environment every time
✅ **Single source of truth** - Test logic lives in `run-all-tests.sh` inside the image

## Test Execution Script

The Docker test stage includes `run-all-tests.sh`, which defines the canonical test sequence:

```bash
#!/bin/bash
set -e  # Exit on first failure

echo "=== 1/4: Linting with ruff ==="
uv run ruff check memgraph/

echo "=== 2/4: Type checking with mypy ==="
uv run mypy memgraph/

echo "=== 3/4: Unit tests (parallel) ==="
uv run pytest -m 'not (ui_basic or ui_interactive)' -n auto -v

echo "=== 4/4: UI tests (playwright) ==="
uv run pytest -m 'ui_basic or ui_interactive' -n 2 -v
```

This script is the default CMD for the test stage, so running the container without arguments executes all tests.

## Test Stages

### Stage 3.5: Test Environment

The `test` stage in the Dockerfile includes:

- Built web bundle
- Dev dependencies (ruff, mypy, pytest, playwright)
- Test files and configuration
- Playwright browsers (chromium)
- **Test execution script** (`/app/run-all-tests.sh`)

Build it once, run tests many times:

```bash
# Build test image
docker build --target test -t zabob-memgraph-test .

# Run all tests (default command)
docker run --rm zabob-memgraph-test

# Run specific test suites
docker run --rm zabob-memgraph-test uv run ruff check memgraph/
docker run --rm zabob-memgraph-test uv run mypy memgraph/
docker run --rm zabob-memgraph-test uv run pytest -v
```

## Available Test Targets

| Target | Command | Description |
| -------- | --------- | ------------- |
| `all` | `./docker-test.sh` or `docker run --rm zabob-memgraph-test` | Runs lint, typecheck, unit, and UI tests via `run-all-tests.sh` |
| `lint` | `TEST_TARGET=lint ./docker-test.sh` | Runs ruff linter |
| `typecheck` | `TEST_TARGET=typecheck ./docker-test.sh` | Runs mypy type checker |
| `unit` | `TEST_TARGET=unit ./docker-test.sh` | Runs unit and integration tests |
| `ui` | `TEST_TARGET=ui ./docker-test.sh` | Runs Playwright UI tests |
| custom | `TEST_TARGET="..." ./docker-test.sh` | Runs custom command |

## CI/CD Integration

The GitHub Actions workflow (`.github/workflows/ci.yml`) uses the same Docker test environment:

```yaml
- name: Build test image
  run: docker build --target test -t test:latest .

- name: Run tests
  run: docker run --rm test:latest uv run pytest -v
```

This means:

- CI tests run in the exact same environment as local tests
- No drift between local and CI environments
- Faster CI (Docker layer caching)
- Simpler workflow configuration

## Local Development

### First Time Setup

```bash
# Build test image (takes 5-10 minutes first time)
docker build --target test -t zabob-memgraph-test .
```

### Running Tests

```bash
# Quick: run all tests
./docker-test.sh

# Or manually with docker
docker run --rm zabob-memgraph-test uv run pytest -v

# Run specific test
docker run --rm zabob-memgraph-test \
  uv run pytest tests/test_search_nodes.py::test_specific -v

# Interactive shell for debugging
docker run --rm -it zabob-memgraph-test /bin/bash
```

### Rebuilding After Changes

The test image is cached, so rebuilds are fast:

```bash
# Only rebuilds changed layers (usually just source code)
docker build --target test -t zabob-memgraph-test .
```

## Traditional Testing (Without Docker)

You can still run tests the traditional way:

```bash
# Install dependencies
uv sync --extra dev

# Install Node dependencies and build web bundle
pnpm install && pnpm run build:web

# Install Playwright browsers
uv run playwright install --with-deps chromium

# Run tests
uv run ruff check memgraph/
uv run mypy memgraph/
uv run pytest -v
```

But the Docker approach is simpler and more reliable.

## Troubleshooting

### "Out of disk space"

Clean up old Docker images:

```bash
docker system prune -a
```

### "Tests fail in Docker but pass locally"

Ensure you're testing the same code:

```bash
# Rebuild test image to include latest changes
docker build --target test --no-cache -t zabob-memgraph-test .
```

### "Build is too slow"

First build takes time (5-15 minutes). Subsequent builds are much faster due to caching:

- Stage 1 (system packages): Cached unless Dockerfile changes
- Stage 2 (dependencies): Cached unless lock files change
- Stage 3 (source code): Always rebuilds (fast, ~1-2 min)

### "Can't see test output"

Add `-v` to pytest command:

```bash
docker run --rm zabob-memgraph-test uv run pytest -v
```

Or run interactively:

```bash
docker run --rm -it zabob-memgraph-test /bin/bash
# Inside container:
uv run pytest -vvs
```

## See Also

- [DOCKER_BUILD.md](docs/DOCKER_BUILD.md) - Comprehensive Docker build documentation
- [CI_CD_DOCKER.md](docs/CI_CD_DOCKER.md) - CI/CD integration details
- [Dockerfile](Dockerfile) - Multi-stage build definition
- [docker-test.sh](docker-test.sh) - Test runner script
