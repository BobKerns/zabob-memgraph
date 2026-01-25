![Zabob Memory Holodeck](images/zabob-banner.jpg)

# Optimized Docker Build Strategy

This directory contains an optimized multi-stage Docker build that minimizes rebuild times by caching layers independently.

## Build Stages

### Stage 1: Base System Dependencies (`base-deps`)

- **Content**: System packages (curl, build-essential, Node.js, pnpm, uv)
- **Cache Key**: SHA256 of the stage's Dockerfile content (first 12 chars)
- **Tag Pattern**: `base-{hash}`
- **Rebuild Trigger**: Only when system dependencies change
- **Typical Frequency**: Rarely (weeks/months)

### Stage 2: Python & Node Dependencies (`python-node-deps`)

- **Content**: Python packages (.venv) and Node modules (node_modules)
- **Cache Key**: SHA256 of `pyproject.toml + uv.lock + package.json + pnpm-lock.yaml`
- **Tag Pattern**: `deps-{hash}`
- **Rebuild Trigger**: When dependency lock files change
- **Typical Frequency**: Occasionally (days/weeks)

### Stage 3: Builder (transitory)

- **Content**: Source code + built web bundle
- **Cache Key**: Timestamp (always rebuilt)
- **Tag Pattern**: `builder-{timestamp}`
- **Rebuild Trigger**: Every build
- **Purpose**: Build artifacts without caching source
- **Cleanup**: Automatically removed after build

### Stage 3.5: Test Environment (optional)

- **Content**: Builder + dev dependencies (ruff, mypy, pytest, playwright)
- **Target Name**: `test`
- **Purpose**: Run quality checks and tests in consistent environment
- **Usage**: CI/CD and local testing
- **Benefits**: Same environment locally and in CI

### Stage 4: Final Runtime Image

- **Content**: Dependencies from Stage 2 + built artifacts from Stage 3
- **Tag Pattern**: `latest`, `v{version}`, custom tags
- **Size**: Minimal - only runtime requirements
- **Purpose**: Production-ready image

## Usage

### Basic Build

```bash
./docker-build.sh
```

This builds the image as `bobkerns/zabob-memgraph:latest`, automatically:

- Checking for cached base and dependency layers
- Building only what changed
- Cleaning up transitory images

### Running Tests in Docker

```bash
# Run all tests (lint, typecheck, unit, UI)
./docker-test.sh

# Run specific test suite
TEST_TARGET=lint ./docker-test.sh
TEST_TARGET=typecheck ./docker-test.sh
TEST_TARGET=unit ./docker-test.sh
TEST_TARGET=ui ./docker-test.sh

# Run custom command
TEST_TARGET="uv run pytest tests/test_specific.py" ./docker-test.sh
```

**Benefits of Docker Testing**:

- Same environment locally and in CI
- No need to install Node.js, Python, Playwright separately
- Cached dependencies speed up repeated test runs
- Isolated from system packages

### Build with Version Tag

```bash
VERSION=v0.1.23 ./docker-build.sh
```

### Push Cache Layers (for CI/CD)

```bash
PUSH_CACHE=true ./docker-build.sh
```

This pushes the `base-{hash}` and `deps-{hash}` images to the registry, allowing:

- CI/CD systems to reuse cached layers
- Team members to share build caches
- Faster builds across different machines

### Custom Image Name

```bash
IMAGE_NAME=myregistry/my-memgraph ./docker-build.sh
```

### Multiple Tags

```bash
ADDITIONAL_TAGS="stable v1.0" ./docker-build.sh
```

Creates: `latest`, `stable`, and `v1.0` tags

## Build Time Optimization

### Typical Scenarios

1. **No changes** (cache hit on all stages): ~10-30 seconds
2. **Source code only changed**: ~1-2 minutes (rebuild web bundle)
3. **Dependencies changed**: ~5-10 minutes (reinstall packages)
4. **System packages changed**: ~10-15 minutes (full rebuild)

### Cache Strategy

The build script uses Docker layer caching with `--cache-from`:

```bash
docker build --target python-node-deps \
    --cache-from base-{hash} \
    --cache-from deps-{hash} \
    ...
```

This allows Docker to:

- Skip unchanged layers
- Reuse intermediate build artifacts
- Pull cached layers from registry if available

## CI/CD Integration

### GitHub Actions Example

The optimized build is integrated into our CI/CD pipeline with architecture-specific caching:

```yaml
- name: Build with optimized caching
  uses: docker/build-push-action@v6
  with:
    context: .
    platforms: ${{ matrix.platform }}
    push: true
    # Architecture-specific cache to prevent collisions
    cache-from: |
      type=registry,ref=ghcr.io/${{ github.repository }}:base-cache-${{ matrix.arch }}
      type=registry,ref=ghcr.io/${{ github.repository }}:deps-cache-${{ matrix.arch }}
    cache-to: |
      type=registry,ref=ghcr.io/${{ github.repository }}:base-cache-${{ matrix.arch }},mode=max
      type=registry,ref=ghcr.io/${{ github.repository }}:deps-cache-${{ matrix.arch }},mode=max
    build-args: |
      BUILDKIT_INLINE_CACHE=1
```

### Cache Strategy in CI/CD

**Stage 1 & 2 Caching**: Architecture-specific cache tags prevent collision:

- `base-{hash}-amd64` - AMD64 base dependencies
- `base-{hash}-arm64` - ARM64 base dependencies
- `deps-{hash}-amd64` - AMD64 Python/Node dependencies
- `deps-{hash}-arm64` - ARM64 Python/Node dependencies

**Stage 3 (Builder)**: Not cached in registry (always rebuilt from source)

**Stage 4 (Runtime)**: Final multi-arch manifest created after both architectures build

### Benefits in CI

- **Faster builds**: Reuse cached layers across workflow runs
- **Reduced costs**: Less compute time = lower CI costs
- **Reliability**: Less time in build = fewer random cancellations
- **Bandwidth**: Only download/upload changed layers
- **No collisions**: Architecture-specific tags keep AMD64 and ARM64 separate

```bash
# List all cache images
docker images bobkerns/zabob-memgraph --format "{{.Repository}}:{{.Tag}}" | grep -E '(base-|deps-)'

# Remove specific hash
docker rmi bobkerns/zabob-memgraph:base-abc123def456

# Clean all dangling images
docker image prune -f
```

### Force Rebuild

To force rebuild of all stages:

```bash
docker build --no-cache --target runtime -t bobkerns/zabob-memgraph:latest .
```

## Troubleshooting

### "Cannot connect to Docker daemon"

Ensure Docker is running:

```bash
docker info
```

### Cache Not Working

Check if BuildKit is enabled:

```bash
export DOCKER_BUILDKIT=1
./docker-build.sh
```

### Pull Failed

If pulling cache images fails, the build will continue building from scratch. This is normal for first builds or when cache images don't exist yet.

## Technical Details

### Why This Structure?

1. **Stage 1 (base-deps)**: System packages change rarely but take longest to install
2. **Stage 2 (python-node-deps)**: Dependencies change occasionally and are large
3. **Stage 3 (builder)**: Source code changes frequently but builds quickly
4. **Stage 4 (runtime)**: Minimal final image without build tools

### Layer Ordering

Docker builds layers sequentially. By putting:

- Slowest/rarest changes first (system packages)
- Medium changes second (dependencies)
- Fastest/frequent changes last (source code)

We maximize cache hits and minimize rebuild time.

### Multi-Stage Benefits

- **Smaller final image**: Build tools not included in runtime
- **Better caching**: Each stage can be cached independently
- **Parallel builds**: Docker can parallelize some stages
- **Cleaner**: Source code not needed in final image

## See Also

- [Dockerfile](../Dockerfile) - The actual multi-stage build definition
- [docker-compose.yml](../docker-compose.yml) - Local development setup
- [DEPLOYMENT.md](../DEPLOYMENT.md) - Deployment documentation
