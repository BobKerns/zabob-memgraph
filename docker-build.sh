#!/bin/bash
# Optimized Docker build with layer caching
# Each stage is built and cached separately based on content hashes

set -e

# Color output
# RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Zabob Memgraph Optimized Docker Build ===${NC}\n"

# Image name and registry
IMAGE_NAME="${IMAGE_NAME:-bobkerns/zabob-memgraph}"
REGISTRY="${REGISTRY:-docker.io}"

# Architecture detection (for multi-arch support)
# Can be overridden with ARCH environment variable
if [ -z "${ARCH}" ]; then
    ARCH=$(uname -m)
    case "${ARCH}" in
        x86_64)
            ARCH="amd64"
            ;;
        aarch64|arm64)
            ARCH="arm64"
            ;;
    esac
fi
ARCH_SUFFIX="${ARCH}"

echo "Building for architecture: ${ARCH}"

# Calculate hash for base dependencies stage (Stage 1)
# Hash the Dockerfile lines for the base-deps stage
BASE_HASH=$(sed -n '/^# Stage 1:/,/^# Stage 2:/p' Dockerfile | sha256sum | cut -d' ' -f1 | cut -c1-12)
BASE_TAG="${REGISTRY}/${IMAGE_NAME}:base-${BASE_HASH}-${ARCH_SUFFIX}"

echo -e "${YELLOW}Stage 1: Base System Dependencies${NC}"
echo "Tag: ${BASE_TAG}"

# Check if base image exists
BASE_CACHE_ARGS=""
if docker pull "${BASE_TAG}" 2>/dev/null; then
    echo -e "${GREEN}✓ Using cached base image${NC}\n"
    BASE_CACHE_ARGS="--cache-from ${BASE_TAG}"
else
    echo "Building base image (no cache available)..."
    docker build --target base-deps \
        --tag "${BASE_TAG}" \
        .
    echo -e "${GREEN}✓ Base image built${NC}\n"

    # Optionally push to registry for sharing
    if [ "${PUSH_CACHE}" = "true" ]; then
        echo "Pushing base image to registry..."
        docker push "${BASE_TAG}"
    fi
fi

# Calculate hash for dependencies stage (Stage 2)
# Hash the dependency lock files
DEPS_HASH=$(cat pyproject.toml uv.lock package.json pnpm-lock.yaml | sha256sum | cut -d' ' -f1 | cut -c1-12)
DEPS_TAG="${REGISTRY}/${IMAGE_NAME}:deps-${DEPS_HASH}-${ARCH_SUFFIX}"

echo -e "${YELLOW}Stage 2: Python & Node Dependencies${NC}"
echo "Tag: ${DEPS_TAG}"

# Check if deps image exists
DEPS_CACHE_ARGS=""
if docker pull "${DEPS_TAG}" 2>/dev/null; then
    echo -e "${GREEN}✓ Using cached dependencies image${NC}\n"
    DEPS_CACHE_ARGS="--cache-from ${DEPS_TAG}"
else
    echo "Building dependencies image (no cache available)..."
    # Only use base cache if it exists
    CACHE_ARGS="${BASE_CACHE_ARGS}"
    # shellcheck disable=SC2086
    docker build --target python-node-deps \
        --tag "${DEPS_TAG}" \
        ${CACHE_ARGS} \
        --build-arg BUILDKIT_INLINE_CACHE=1 \
        .
    echo -e "${GREEN}✓ Dependencies image built${NC}\n"

    # Optionally push to registry for sharing
    if [ "${PUSH_CACHE}" = "true" ]; then
        echo "Pushing dependencies image to registry..."
        docker push "${DEPS_TAG}"
    fi
    # Now that we built it, we can use it as cache
    DEPS_CACHE_ARGS="--cache-from ${DEPS_TAG}"
fi

# Build transitory builder stage (Stage 3)
# This stage includes source code and is always rebuilt
BUILDER_TAG="${REGISTRY}/${IMAGE_NAME}:builder-$(date +%s)-${ARCH_SUFFIX}"

echo -e "${YELLOW}Stage 3: Builder (with source code)${NC}"
echo "Tag: ${BUILDER_TAG}"
echo "Building builder image with source code..."
# Use all available cache layers
BUILDER_CACHE_ARGS="${BASE_CACHE_ARGS} ${DEPS_CACHE_ARGS}"
# shellcheck disable=SC2086
docker build --target builder \
    --tag "${BUILDER_TAG}" \
    ${BUILDER_CACHE_ARGS} \
    --build-arg BUILDKIT_INLINE_CACHE=1 \
    .
echo -e "${GREEN}✓ Builder image created${NC}\n"

# Build final runtime image (Stage 4)
FINAL_TAG="${IMAGE_NAME}:latest"
if [ -n "${VERSION}" ]; then
    FINAL_TAG="${IMAGE_NAME}:${VERSION}"
fi

echo -e "${YELLOW}Stage 4: Final Runtime Image${NC}"
echo "Tag: ${FINAL_TAG}"
echo "Building final runtime image..."
# Use all available cache layers
RUNTIME_CACHE_ARGS="${BASE_CACHE_ARGS} ${DEPS_CACHE_ARGS} --cache-from ${BUILDER_TAG}"
# shellcheck disable=SC2086
docker build --target runtime \
    --tag "${FINAL_TAG}" \
    ${RUNTIME_CACHE_ARGS} \
    --build-arg BUILDKIT_INLINE_CACHE=1 \
    .
echo -e "${GREEN}✓ Final image built: ${FINAL_TAG}${NC}\n"

# Also tag with additional tags if specified
if [ -n "${ADDITIONAL_TAGS}" ]; then
    for tag in ${ADDITIONAL_TAGS}; do
        echo "Tagging as: ${IMAGE_NAME}:${tag}"
        docker tag "${FINAL_TAG}" "${IMAGE_NAME}:${tag}"
    done
fi

# Clean up transitory builder image
echo "Cleaning up transitory builder image..."
docker rmi "${BUILDER_TAG}" 2>/dev/null || true

echo -e "\n${GREEN}=== Build Complete ===${NC}"
echo "Final image: ${FINAL_TAG}"
echo "Architecture: ${ARCH}"
echo ""
echo "Cached layers:"
echo "  Base:         ${BASE_TAG}"
echo "  Dependencies: ${DEPS_TAG}"
echo ""
echo "Local usage:"
echo "  docker run -p 6789:6789 ${FINAL_TAG}"
echo ""
echo "CI/CD usage:"
echo "  The GitHub Actions workflow uses architecture-specific cache tags"
echo "  to prevent collisions between amd64 and arm64 builds."
echo ""
echo "To push cache layers for CI/CD, run:"
echo "  PUSH_CACHE=true ./docker-build.sh"
echo ""
echo "To build with version tag:"
echo "  VERSION=v1.0.0 ./docker-build.sh"
echo ""
echo "To build for specific architecture:"
echo "  ARCH=arm64 ./docker-build.sh"
