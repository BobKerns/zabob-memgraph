# Use Python 3.12 slim image
FROM python:3.12-slim

# Install uv
RUN pip install uv

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock ./
COPY memgraph/ ./memgraph/
COPY main.py ./

# Install dependencies
RUN uv sync --frozen

# Create directory for configuration and data
RUN mkdir -p /app/.zabob-memgraph

# Set environment variable to indicate Docker container
ENV DOCKER_CONTAINER=1
ENV MEMGRAPH_HOST=0.0.0.0
ENV MEMGRAPH_PORT=8080

# Expose default port
EXPOSE 8080

# Use main.py as entrypoint
CMD ["uv", "run", "main.py"]
