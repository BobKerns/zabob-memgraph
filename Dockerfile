# Stage 1: Base system dependencies
# Tagged with: base-{SHA256 of this stage}
# Rarely changes - system packages only
FROM python:3.14-slim AS base-deps

# Install system dependencies
# Pin Node.js version for reproducibility and security
ENV NODE_MAJOR=20
RUN apt-get update && \
    apt-get install -y curl libffi-dev build-essential ca-certificates gnupg && \
    mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_${NODE_MAJOR}.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list && \
    apt-get update && \
    apt-get install -y nodejs && \
    npm install -g pnpm && \
    pip install uv && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app


# Stage 2: Python and Node dependencies
# Tagged with: deps-{hash of pyproject.toml + uv.lock + package.json + pnpm-lock.yaml}
# Changes when dependencies change
FROM base-deps AS python-node-deps

# Copy only dependency files
COPY pyproject.toml uv.lock package.json pnpm-lock.yaml ./

# Install Python dependencies (non-editable)
# Force CPU-only PyTorch to avoid large CUDA dependencies (5GB+)
ENV PIP_INDEX_URL=https://download.pytorch.org/whl/cpu
ENV PIP_EXTRA_INDEX_URL=https://pypi.org/simple
RUN uv sync --frozen --no-editable
ENV PIP_INDEX_URL=
ENV PIP_EXTRA_INDEX_URL=

# Install Node dependencies (don't build yet)
RUN pnpm install

# Create data directory for database
RUN mkdir -p /data/.zabob/memgraph/data

# Set environment variables for virtual environment
ENV PATH=/app/.venv/bin:$PATH
ENV VIRTUAL_ENV=/app/.venv

# Set environment variables to indicate Docker container
ENV DOCKER_CONTAINER=1
ENV MEMGRAPH_HOST=0.0.0.0
ENV MEMGRAPH_PORT=6789
ENV MEMGRAPH_DATABASE_PATH=/data/knowledge_graph.db
ENV HOME=/data

# Stage 3: Build stage (transitory)
# Adds source code and builds web bundle
FROM python-node-deps AS builder

# Copy source code
COPY memgraph/ ./memgraph/

# Build web bundle
RUN pnpm run build:web


# Stage 3.5: Test environment (optional, used in CI and local testing)
# Includes dev dependencies for running quality checks and tests
FROM builder AS test

# Install dev dependencies (ruff, mypy, pytest, playwright)
RUN uv sync --extra dev

# Install Playwright browsers for UI tests
# Clean up after install to reduce image size
RUN uv run playwright install --with-deps chromium && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf /tmp/* && \
    find /data/.cache/ms-playwright -name '*.zip' -delete 2>/dev/null || true

# Copy test files and configuration
COPY tests/ ./tests/
COPY pyproject.toml ./
COPY check_types.py dev_utils.py ./

# Copy test runner script
COPY run-all-tests.sh /app/run-all-tests.sh
RUN chmod +x /app/run-all-tests.sh

# Set up environment for test execution
ENV PYTHONPATH=/app
WORKDIR /app

# Default command runs all quality checks and tests
# Override with: docker run --rm test-image uv run pytest -k test_name
CMD ["/app/run-all-tests.sh"]


# Stage 4: Final runtime image
# Based on deps stage, copies only runtime artifacts from builder
FROM python-node-deps AS runtime

# Copy only the built web assets from builder
COPY --from=builder /app/memgraph /app/memgraph

# Copy pyproject.toml for metadata (already present but being explicit)
COPY pyproject.toml ./

# Expose default port
EXPOSE 6789

# Set entrypoint and default command
ENTRYPOINT ["/app/.venv/bin/zabob-memgraph"]
CMD []

# Metadata labels
LABEL org.opencontainers.image.source=https://github.com/BobKerns/zabob-memgraph
LABEL org.opencontainers.image.title="Zabob Memgraph"
LABEL org.opencontainers.image.description="Zabob Memgraph MCP memory service with web interface\nZabob remembers the future so you don't have to."
LABEL org.opencontainers.image.licenses=MIT
