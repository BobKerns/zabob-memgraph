#!/bin/bash
# Run all quality checks and tests in sequence
# This script is included in the Docker test stage and defines
# the canonical test execution order.

set -e  # Exit on first failure

echo "========================================="
echo "=== 1/4: Linting with ruff ==="
echo "========================================="
uv run ruff check memgraph/

echo ""
echo "========================================="
echo "=== 2/4: Type checking with mypy ==="
echo "========================================="
uv run mypy memgraph/

echo ""
echo "========================================="
echo "=== 3/4: Unit tests (parallel) ==="
echo "========================================="
uv run pytest -m 'not (ui_basic or ui_interactive)' -n auto -v

echo ""
echo "========================================="
echo "=== 4/4: UI tests (playwright) ==="
echo "========================================="
uv run pytest -m 'ui_basic or ui_interactive' -n 2 -v

echo ""
echo "========================================="
echo "=== ✅ All tests passed! ==="
echo "========================================="
