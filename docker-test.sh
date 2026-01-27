#!/bin/bash
# Run tests inside Docker test environment
# This provides consistency between local and CI testing

set -e

# Color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

IMAGE_NAME="${IMAGE_NAME:-zabob-memgraph-test}"
TEST_TARGET="${TEST_TARGET:-all}"

echo -e "${GREEN}=== Docker Test Runner ===${NC}\n"

# Build test image if needed
echo -e "${YELLOW}Building test image...${NC}"
docker build --target test \
    --tag "${IMAGE_NAME}:latest" \
    --cache-from "${IMAGE_NAME}:latest" \
    .
echo -e "${GREEN}✓ Test image built${NC}\n"

# Run tests based on target
case "${TEST_TARGET}" in
    lint)
        echo -e "${YELLOW}Running linters...${NC}"
        docker run --rm "${IMAGE_NAME}:latest" \
            uv run ruff check memgraph/
        ;;

    typecheck)
        echo -e "${YELLOW}Running type checker...${NC}"
        docker run --rm "${IMAGE_NAME}:latest" \
            uv run mypy memgraph/
        ;;

    unit)
        echo -e "${YELLOW}Running unit and integration tests...${NC}"
        docker run --rm "${IMAGE_NAME}:latest" \
            uv run pytest -m "not (ui_basic or ui_interactive)" -n auto -v
        ;;

    ui)
        echo -e "${YELLOW}Running UI tests...${NC}"
        docker run --rm "${IMAGE_NAME}:latest" \
            uv run pytest -m "ui_basic or ui_interactive" -n 2 -v
        ;;

    all)
        echo -e "${YELLOW}Running all quality checks and tests...${NC}"
        docker run --rm "${IMAGE_NAME}:latest"
        ;;

    *)
        echo -e "${YELLOW}Running custom test command: ${TEST_TARGET}${NC}"
        docker run --rm "${IMAGE_NAME}:latest" "${TEST_TARGET}"
        ;;
esac

echo -e "\n${GREEN}=== All tests completed successfully ===${NC}"
