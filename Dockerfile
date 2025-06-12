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

# Install dependencies and create venv
RUN uv sync --frozen

# Create data directory for database
RUN mkdir -p /data

# Create startup script
RUN echo '#!/bin/bash\n\nsource .venv/bin/activate\nexec python main.py "$@"' > /app/start.sh && \
    chmod +x /app/start.sh

# Set environment variables to indicate Docker container
ENV DOCKER_CONTAINER=1
ENV MEMGRAPH_HOST=0.0.0.0
ENV MEMGRAPH_PORT=8080
ENV MEMGRAPH_DATABASE_PATH=/data/knowledge_graph.db

# Expose default port
EXPOSE 8080

# Use startup script as entrypoint
CMD ["/app/start.sh"]
