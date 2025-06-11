# Use Python 3.12 slim image
FROM python:3.12-slim

# Install system dependencies including git and git-lfs
RUN apt-get update && apt-get install -y \
    curl \
    git \
    git-lfs \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock ./
COPY memgraph/ ./memgraph/
COPY launcher.py ./

# Install dependencies
RUN uv sync --frozen

# Create memgraph directory for config and data
RUN mkdir -p /root/.memgraph/backup

# Expose default port (will be overridden by launcher)
EXPOSE 8080

# Use launcher script as entrypoint
ENTRYPOINT ["uv", "run", "launcher.py"]
