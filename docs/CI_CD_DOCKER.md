![Zabob Memory Holodeck](images/zabob-banner.jpg)

# CI/CD Docker Build Integration

This document explains how the optimized Docker build integrates with GitHub Actions CI/CD.

## Overview

The build uses a 4.5-stage Dockerfile with architecture-specific caching and integrated testing:

1. **Stage 1 (base-deps)**: System packages - rarely changes
2. **Stage 2 (python-node-deps)**: Dependencies - changes occasionally
3. **Stage 3 (builder)**: Source code + web bundle - always rebuilt
4. **Stage 3.5 (test)**: Test environment with dev tools - used in CI and locally
5. **Stage 4 (runtime)**: Final image - minimal runtime

## Test Environment Integration

### Why Test in Docker?

**Consistency**: Same environment locally and in CI - no "works on my machine" issues

**Simplicity**: No need to install Node.js, Python, Playwright, etc. separately in CI

**Speed**: Cached Docker layers mean faster test runs after first build

**Isolation**: Tests run in clean environment every time

### Test Stage Contents

The `test` stage includes:

- All source code and built web bundle (from `builder`)
- Dev dependencies: `ruff`, `mypy`, `pytest`, `pytest-playwright`
- Playwright browsers (chromium)
- Test files and configuration
- Dev utilities (`dev_utils.py`, `check_types.py`)

### Local Testing with Docker

```bash
# Run all tests
./docker-test.sh

# Run specific test suites
TEST_TARGET=lint ./docker-test.sh       # Just linting
TEST_TARGET=typecheck ./docker-test.sh  # Just type checking
TEST_TARGET=unit ./docker-test.sh       # Unit tests only
TEST_TARGET=ui ./docker-test.sh         # UI tests only

# Run custom command
TEST_TARGET="uv run pytest tests/test_specific.py::test_name -v" ./docker-test.sh
```

```text
base-{dockerfile-hash}-amd64
base-{dockerfile-hash}-arm64
deps-{lockfiles-hash}-amd64
deps-{lockfiles-hash}-arm64

```

## Workflow Integration

### ci.yml - Test Workflow

The `ci.yml` workflow now uses Docker for all testing. The test execution logic lives in `run-all-tests.sh`, which is built into the Docker test stage:

```yaml
- name: Build test image with caching
  uses: docker/build-push-action@v6
  with:
    target: test
    cache-from: type=gha
    cache-to: type=gha,mode=max
    load: true

- name: Run all quality checks and tests
  run: docker run --rm zabob-memgraph-test:latest
```

**Benefits**:

- Test execution logic lives in the Docker image (`/app/run-all-tests.sh`)
- Single command execution (fastest possible)
- Same test sequence locally (`./docker-test.sh`) and in CI
- Fails fast on first error (`set -e` in script)
- Clear progress output with section headers
- No CI-specific test orchestration logic
- Consistent between all environments

**Test Script** (`run-all-tests.sh`):

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

echo "=== ✅ All tests passed! ==="
```

### docker-build.yml - Build Workflow

The main build workflow (`.github/workflows/docker-build.yml`) uses matrix builds:

```yaml
strategy:
  matrix:
    include:
      - platform: linux/amd64
        runner: ubuntu-latest
      - platform: linux/arm64
        runner: ubuntu-24.04-arm
```

Each platform builds independently with its own cache:

```yaml
cache-from: |
  type=registry,ref=ghcr.io/${{ repo }}:base-cache-${{ arch }}
  type=registry,ref=ghcr.io/${{ repo }}:deps-cache-${{ arch }}
cache-to: |
  type=registry,ref=ghcr.io/${{ repo }}:base-cache-${{ arch }},mode=max
  type=registry,ref=ghcr.io/${{ repo }}:deps-cache-${{ arch }},mode=max
```

### Build Flow

1. **Parallel Builds**: AMD64 and ARM64 build simultaneously
   - Each pulls architecture-specific cache layers
   - Each builds and pushes by digest to GHCR
   - Each exports digest for manifest creation

2. **Merge**: Combines digests into multi-arch manifest
   - Creates manifest list with both architectures
   - Tags with version, branch, or PR number
   - Pushes to GHCR

3. **Verify**: Tests multi-arch image
   - Pulls manifest on both architectures
   - Verifies correct arch selected
   - Runs basic functionality tests

4. **Publish** (optional): Pushes to Docker Hub
   - Only for tagged releases
   - Production (v*) or test (test-v*) tags

## Cache Efficiency

### First Build (No Cache)

- Stage 1: ~5-10 minutes (system packages)
- Stage 2: ~5-10 minutes (dependencies)
- Stage 3: ~1-2 minutes (build web bundle)
- Stage 4: <1 minute (copy artifacts)
- **Total: ~12-20 minutes per architecture**

### Subsequent Builds (Full Cache)

When only source code changes:

- Stage 1: <10 seconds (cached)
- Stage 2: <10 seconds (cached)
- Stage 3: ~1-2 minutes (rebuild)
- Stage 4: <1 minute (copy)
- **Total: ~2-3 minutes per architecture**

### Dependency Update

When dependencies change:

- Stage 1: <10 seconds (cached)
- Stage 2: ~5-10 minutes (rebuild)
- Stage 3: ~1-2 minutes (rebuild)
- Stage 4: <1 minute (copy)
- **Total: ~7-12 minutes per architecture**

## Cache Management

### Automatic Cache Population

The CI workflow automatically populates registry cache:

- Base cache pushed after Stage 1 build
- Deps cache pushed after Stage 2 build
- Both tagged with hash + architecture

### Cache Invalidation

Caches are invalidated when:

- **Stage 1**: Dockerfile base-deps section changes (rare)
- **Stage 2**: Lock files change (occasional)
- **Stage 3**: Always rebuilt (no cache)

### Manual Cache Cleanup

To clean old cache images:

```bash
# List cache images
gh api "/orgs/{org}/packages/container/{package}/versions" \
  --jq '.[] | select(.metadata.container.tags[] | contains("cache")) | .id'

# Delete specific version
gh api -X DELETE "/orgs/{org}/packages/container/{package}/versions/{id}"
```

Or via GitHub UI: Packages → zabob-memgraph → Versions → Delete old `-cache-` tags

## Troubleshooting

### Build Fails to Pull Cache

**Symptom**: Warning about importing cache manifest

**Cause**: Cache image doesn't exist yet (first build)

**Solution**: Normal - build will continue without cache

### Wrong Architecture Cached

**Symptom**: Build downloads wrong arch packages

**Cause**: Cache tag doesn't include architecture

**Solution**: Verify cache tags include `-amd64` or `-arm64` suffix

### Builds Taking Too Long

**Symptom**: Builds not using cache

**Cause**:

- Cache tags changed (hash mismatch)
- Cache expired or deleted
- Cache pull failed (network/permissions)

**Solution**:

- Check if lock files changed (new deps hash)
- Verify GHCR permissions
- Check GitHub Actions logs for cache status

### Out of Disk Space

**Symptom**: Build fails with "no space left on device"

**Cause**: Old cache images accumulating

**Solution**: Clean up old cache tags (see Cache Management above)

## Best Practices

1. **Don't delete base cache**: Changes rarely, saves 5-10 min/build
2. **Keep recent deps cache**: Even if dependencies updated
3. **Monitor cache usage**: Watch for disk space in GHCR
4. **Test cache changes**: Verify builds work without cache first
5. **Document changes**: Update this file when modifying build process

## References

- [Dockerfile](../Dockerfile) - Multi-stage build definition
- [docker-build.sh](../docker-build.sh) - Local build script
- [DOCKER_BUILD.md](DOCKER_BUILD.md) - Comprehensive build documentation
- [.github/workflows/docker-build.yml](../.github/workflows/docker-build.yml) - CI workflow
