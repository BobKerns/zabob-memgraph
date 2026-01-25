# Stage 1: Base system dependencies
# Tagged with: base-{SHA256 of this stage}
# Rarely changes - system packages only
FROM python:3.14-slim AS base-deps

# Install system dependencies
RUN apt-get update && \
    apt-get install -y curl libffi-dev build-essential && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
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
RUN uv sync --frozen --no-editable

# Install Node dependencies (don't build yet)
RUN pnpm install


# Stage 3: Build stage (transitory)
# Adds source code and builds web bundle
FROM python-node-deps AS builder

# Copy source code
COPY memgraph/ ./memgraph/

# Build web bundle
RUN pnpm run build:web


# Stage 4: Final runtime image
# Based on deps stage, copies only runtime artifacts from builder
FROM python-node-deps AS runtime

# Copy only the built web assets from builder
COPY --from=builder /app/memgraph/web /app/memgraph/web

# Copy pyproject.toml for metadata (already present but being explicit)
COPY pyproject.toml ./

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
