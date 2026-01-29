# Base Images Workflow

This document explains the base images system used to optimize Docker builds.

## Problem

The original multi-stage Dockerfile built everything from scratch on every PR:

- System packages and Node.js installation (~2 minutes)
- Playwright browser installation (~500MB, ~3-5 minutes)
- Python and Node dependencies (~2-3 minutes)
- Dev dependencies for testing (mypy, ruff, pytest)

This caused:

- Long build times (15-20 minutes per architecture)
- Disk space pressure on GitHub Actions runners
- Frequent timeout and out-of-disk failures
- Redundant work when only source code changed

## Solution

Split Docker builds into two workflows:

### 1. Base Images Workflow (`base-images.yml`)

**Trigger**: Manual (workflow_dispatch) when base dependencies change

**Builds and publishes**:

- `base-deps:vN` - Multi-arch (amd64/arm64) system packages
  - Python 3.14-slim
  - Node.js 20.x with pinned GPG keys
  - pnpm, uv
  - Playwright system dependencies (libglib, fonts, X11, etc.)

- `base-playwright:vN` - AMD64 only, adds Playwright
  - Based on `base-deps`
  - Python and Node dependencies
  - Playwright browsers (~500MB)
  - Aggressive cleanup to minimize layer size

- `base-test:vN` - AMD64 only, adds dev tools
  - Based on `base-playwright`
  - Dev dependencies (mypy, ruff, pytest, etc.)

**Usage**:

```bash
# Trigger manually from GitHub Actions UI
# Set version (e.g., v1, v2, v3)
# Optionally tag as "latest"
```

All images are pushed to GHCR: `ghcr.io/bobkerns/zabob-memgraph/base-*:vN`

### 2. Main Build Workflow (`docker-build.yml`)

**Trigger**: On every PR and release

**Uses pre-built base images**:

- Test image (amd64): `base-test:vN` + source code + web bundle
- Runtime images (multi-arch): `base-deps:vN` + dependencies + source + web bundle

**Benefits**:

- ✅ Builds complete in ~5-8 minutes (was 15-20 minutes)
- ✅ No Playwright installation during normal builds
- ✅ Minimal disk space usage (~2-3GB vs 8-10GB)
- ✅ Reliable - no more timeout failures
- ✅ Dependencies only rebuilt when they actually change

## Dockerfiles

Base images are built from dedicated Dockerfiles:

- `Dockerfile.base-deps` - System packages (Python, Node.js, uv, pnpm, Playwright system libs)
- `Dockerfile.base-playwright` - Adds Python/Node deps + Playwright browsers
- `Dockerfile.base-test` - Adds dev dependencies (mypy, ruff, pytest)

Main application Dockerfiles:

- `Dockerfile.test` - Test image using base-test
- `Dockerfile.runtime` - Final runtime image using base-deps

## When to Rebuild Base Images

Rebuild base images when:

- System dependencies change (Dockerfile.base-deps)
- Python or Node dependencies change (pyproject.toml, uv.lock, package.json, pnpm-lock.yaml)
- Playwright version changes (Dockerfile.base-playwright)
- Dev dependencies change (mypy, ruff, pytest versions in Dockerfile.base-test)
- Node.js version changes (Dockerfile.base-deps)

**Increment the version number** each time you rebuild.

## Updating Main Builds to Use New Base Images

After rebuilding base images with a new version:

1. Edit `.github/workflows/docker-build.yml`
2. Update the `BASE_IMAGE_VERSION` variable:

   ```yaml
   env:
     BASE_IMAGE_VERSION: v2  # Increment this
   ```

3. Commit and push

All subsequent builds will use the new base images.

## File Structure

```text
.github/workflows/
  base-images.yml           # Manual workflow to build base images
  docker-build.yml          # PR/release workflow using base images

Dockerfile.base-deps        # System packages (Python, Node.js, uv, pnpm)
Dockerfile.base-playwright  # Adds Python/Node deps + Playwright browsers
Dockerfile.base-test        # Adds dev dependencies (mypy, ruff, pytest)
Dockerfile.test             # Test image using base-test
Dockerfile.runtime          # Final runtime image using base-deps
```

## Trade-offs

**Pros**:

- Much faster PR builds
- More reliable (no resource limits)
- Clear separation of rarely-changing vs frequently-changing layers
- Smaller builds mean lower CI costs

**Cons**:

- Web bundle is built twice (once for test, once for runtime)
  - This is fast (~30 seconds) and worth the simplicity
- Must manually trigger base image rebuild when dependencies change
  - Could automate this with dependency file hash checking

## Implementation Details

### Base Images Workflow Implementation

1. **build-base-deps** (multi-arch)
   - Builds from Dockerfile.base-deps
   - Builds amd64 and arm64 in parallel
   - Pushes by digest for manifest merging

2. **merge-base-deps**
   - Creates multi-arch manifest
   - Tags with version (e.g., `v1`)
   - Optionally tags as `latest`

3. **build-base-playwright** (amd64 only)
   - Uses `base-deps:vN` as base
   - Adds Playwright and browsers
   - Single-arch only (Playwright is testing-specific)

4. **build-base-test** (amd64 only)
   - Uses `base-playwright:vN` as base
   - Adds dev dependencies
   - Ready for test execution

### Main Build Workflow

**Test Build (amd64)**:

```dockerfile
FROM ghcr.io/bobkerns/zabob-memgraph/base-test:v1
COPY memgraph/ ./memgraph/
RUN pnpm run build:web
COPY tests/ ./tests/
# Ready to run tests
```

**Runtime Build (multi-arch)**:

```dockerfile
FROM ghcr.io/bobkerns/zabob-memgraph/base-deps:v1
# Install Python/Node deps (lightweight)
COPY pyproject.toml uv.lock package.json pnpm-lock.yaml ./
RUN uv sync --frozen --no-editable
RUN pnpm install
# Add source and build
COPY memgraph/ ./memgraph/
RUN pnpm run build:web
```

## Monitoring and Maintenance

- Base images are versioned (v1, v2, v3, ...)
- Each base image push is logged in GitHub Actions
- Main builds reference specific versions (not `latest`)
- If main builds start failing, check if `BASE_IMAGE_VERSION` needs updating

## Future Improvements

- Auto-detect when base images need rebuilding (hash dependency files)
- Add workflow to automatically update `BASE_IMAGE_VERSION` in PRs
- Consider pushing base images to Docker Hub for public availability
- Add base image tags with dependency hashes for finer-grained caching
