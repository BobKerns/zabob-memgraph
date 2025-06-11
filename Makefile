# Memgraph Development Makefile

.PHONY: help install dev build run run-docker stop status clean lint test docker-build docker-run

# Default target
help:
	@echo "Memgraph Knowledge Graph Server"
	@echo ""
	@echo "Available targets:"
	@echo "  install       Install dependencies with uv"
	@echo "  dev           Install development dependencies"
	@echo "  run           Start the server (auto-assign port)"
	@echo "  run-port      Start server on specific port (make run-port PORT=8080)"
	@echo "  status        Check server status"
	@echo "  stop          Stop running server"
	@echo "  clean         Clean up processes and temporary files"
	@echo ""
	@echo "Docker targets:"
	@echo "  docker-build  Build Docker image"
	@echo "  docker-run    Run with Docker Compose"
	@echo "  docker-stop   Stop Docker services"
	@echo "  docker-logs   View Docker logs"
	@echo ""
	@echo "Development targets:"
	@echo "  lint          Run code formatting and type checking"
	@echo "  test          Run tests"
	@echo "  format        Format code with black and isort"
	@echo ""

# Installation
install:
	uv sync

dev:
	uv sync --group dev

# Running
run:
	uv run launcher.py

run-port:
	uv run launcher.py --port $(PORT)

status:
	uv run launcher.py --status

stop:
	uv run launcher.py --stop

clean:
	uv run launcher.py --stop 2>/dev/null || true
	rm -rf __pycache__ */__pycache__ */*/__pycache__
	rm -rf .pytest_cache
	rm -rf *.egg-info
	rm -f *.log

# Docker targets
docker-build:
	docker build -t memgraph:latest .

docker-run:
	docker-compose up -d

docker-stop:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-clean:
	docker-compose down -v
	docker system prune -f

# Development targets
lint:
	uv run mypy memgraph/
	uv run black --check memgraph/
	uv run isort --check-only memgraph/

format:
	uv run black memgraph/
	uv run isort memgraph/

test:
	uv run pytest

# Utility targets
reset-db:
	rm -f knowledge_graph.db
	rm -rf ~/.memgraph/backup/*.db

backup:
	mkdir -p ~/.memgraph/backup
	cp knowledge_graph.db ~/.memgraph/backup/manual_backup_$(shell date +%s).db 2>/dev/null || true

restore:
	@echo "Available backups:"
	@ls -la ~/.memgraph/backup/*.db 2>/dev/null || echo "No backups found"
	@echo "To restore: cp ~/.memgraph/backup/BACKUP_FILE knowledge_graph.db"

# Installation verification
check-deps:
	@echo "Checking dependencies..."
	@which uv > /dev/null || (echo "❌ uv not installed. Run: curl -LsSf https://astral.sh/uv/install.sh | sh" && exit 1)
	@which git > /dev/null || (echo "❌ git not installed" && exit 1)
	@git lfs version > /dev/null 2>&1 || echo "⚠️  git-lfs not installed (recommended: git lfs install)"
	@echo "✅ Dependencies check complete"

# Quick setup for new installations
setup: check-deps install
	@echo "🚀 Setup complete! Run 'make run' to start the server"
