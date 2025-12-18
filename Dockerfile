# Build stage
FROM python:3.14-slim AS builder
#FROM python:3.12-bookworm AS builder

# Install build dependencies
RUN apt-get update && \
    apt-get install -y curl libffi-dev build-essential && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g pnpm && \
    pip install uv && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock package.json pnpm-lock.yaml index.js ./
COPY memgraph/ ./memgraph/

# Install Python dependencies (non-editable)
RUN uv sync --frozen --no-editable

# Build web bundle
RUN pnpm install && pnpm run build:web

# Runtime stage
FROM python:3.14-slim
# FROM python:3.12-bookworm

WORKDIR /app

# Copy only the virtual environment and built web assets
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/memgraph/web /app/memgraph/web
COPY --from=builder /app/pyproject.toml /app/pyproject.toml

# Create data directory for database
RUN mkdir -p /data/.zabob/memgraph/data

# Set environment variables for virtual environment and define our entrypoint
ENV PATH=/app/.venv/bin:$PATH
ENV VIRTUAL_ENV=/app/.venv
ENTRYPOINT ["/app/.venv/bin/zabob-memgraph"]

# Set environment variables to indicate Docker container
ENV DOCKER_CONTAINER=1
ENV MEMGRAPH_HOST=0.0.0.0
ENV MEMGRAPH_PORT=6789
ENV MEMGRAPH_DATABASE_PATH=/data/knowledge_graph.db
ENV HOME=/data

# Expose default port
EXPOSE 6789

# Use startup script as entrypoint
CMD []
