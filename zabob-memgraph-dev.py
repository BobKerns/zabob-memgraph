#!/usr/bin/env uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click>=8.1.0",
#     "psutil>=6.1.0",
#     "requests>=2.32.0",
#     "rich>=13.9.0",
# ]
# ///
"""
Zabob Memgraph Development Commands

Replaces Makefile functionality with Python/Click commands for better 
cross-platform compatibility and maintainability.
"""

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import click
import psutil
import requests
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

PROJECT_DIR = Path(__file__).parent
DOCKER_IMAGE = "zabob-memgraph:latest"
DOCKER_COMPOSE_FILE = PROJECT_DIR / "docker-compose.yml"


@click.group()
@click.version_option()
def dev():
    """Zabob Memgraph Development Commands"""
    pass


@click.command()
@click.option("--force", is_flag=True, help="Force reinstall even if already installed")
def install(force: bool):
    """Install development dependencies and setup environment"""
    console.print("🔧 Setting up development environment...")
    
    # Check if uv is available
    if not shutil.which("uv"):
        console.print("❌ uv not found. Please install uv first:")
        console.print("  curl -LsSf https://astral.sh/uv/install.sh | sh")
        sys.exit(1)
    
    # Install Python dependencies
    console.print("📦 Installing Python dependencies...")
    try:
        subprocess.run(["uv", "sync"], cwd=PROJECT_DIR, check=True)
        console.print("✅ Python dependencies installed")
    except subprocess.CalledProcessError:
        console.print("❌ Failed to install Python dependencies")
        sys.exit(1)
    
    # Check Docker
    if not shutil.which("docker"):
        console.print("⚠️  Docker not found. Docker is optional but recommended.")
        console.print("   Install from: https://docs.docker.com/get-docker/")
    else:
        console.print("✅ Docker available")
    
    # Create config directory
    config_dir = Path.home() / ".zabob-memgraph"
    config_dir.mkdir(exist_ok=True)
    console.print(f"✅ Config directory: {config_dir}")
    
    console.print("🎉 Development environment setup complete!")


@click.command()
@click.option("--port", type=int, default=8080, help="Port to run on")
@click.option("--host", default="localhost", help="Host to bind to")
@click.option("--reload", is_flag=True, help="Enable auto-reload for development")
def run(port: int, host: str, reload: bool):
    """Run the development server"""
    console.print(f"🚀 Starting development server on {host}:{port}")
    
    if reload:
        console.print("🔄 Auto-reload enabled")
    
    # Set environment variables
    env = os.environ.copy()
    env['MEMGRAPH_HOST'] = host
    env['MEMGRAPH_PORT'] = str(port)
    env['MEMGRAPH_ENV'] = 'development'
    
    # Run with uvicorn for development
    cmd = ["uv", "run", "uvicorn", "memgraph.server:app", 
           "--host", host, "--port", str(port)]
    
    if reload:
        cmd.extend(["--reload", "--reload-dir", "memgraph"])
    
    try:
        subprocess.run(cmd, cwd=PROJECT_DIR, env=env, check=True)
    except KeyboardInterrupt:
        console.print("\\n👋 Development server stopped")
    except subprocess.CalledProcessError as e:
        console.print(f"❌ Server failed: {e}")
        sys.exit(1)


@click.command()
@click.option("--tag", default=DOCKER_IMAGE, help="Docker image tag")
@click.option("--no-cache", is_flag=True, help="Build without cache")
def build(tag: str, no_cache: bool):
    """Build Docker image"""
    console.print(f"🐳 Building Docker image: {tag}")
    
    if not shutil.which("docker"):
        console.print("❌ Docker not found")
        sys.exit(1)
    
    cmd = ["docker", "build", "-t", tag]
    
    if no_cache:
        cmd.append("--no-cache")
    
    cmd.append(".")
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Building Docker image...", total=None)
            
            process = subprocess.Popen(
                cmd, 
                cwd=PROJECT_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            
            for line in process.stdout:
                # Show important build steps
                if any(keyword in line.lower() for keyword in ["step", "copying", "error"]):
                    console.print(f"    {line.strip()}")
            
            process.wait()
            progress.remove_task(task)
        
        if process.returncode == 0:
            console.print(f"✅ Docker image built successfully: {tag}")
        else:
            console.print("❌ Docker build failed")
            sys.exit(1)
            
    except subprocess.CalledProcessError as e:
        console.print(f"❌ Docker build failed: {e}")
        sys.exit(1)


@click.command()
@click.option("--port", type=int, default=8080, help="Port to run on")
@click.option("--detach", "-d", is_flag=True, help="Run in background")
def docker_run(port: int, detach: bool):
    """Run using Docker Compose"""
    if not DOCKER_COMPOSE_FILE.exists():
        console.print("❌ docker-compose.yml not found")
        sys.exit(1)
    
    console.print(f"🐳 Starting with Docker Compose on port {port}")
    
    # Update port in environment
    env = os.environ.copy()
    env['MEMGRAPH_PORT'] = str(port)
    
    cmd = ["docker", "compose", "up"]
    if detach:
        cmd.append("-d")
    
    try:
        subprocess.run(cmd, cwd=PROJECT_DIR, env=env, check=True)
        if detach:
            console.print(f"✅ Started in background on http://localhost:{port}")
    except subprocess.CalledProcessError as e:
        console.print(f"❌ Failed to start with Docker Compose: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\\n👋 Stopping containers...")
        subprocess.run(["docker", "compose", "down"], cwd=PROJECT_DIR)


@click.command()
def docker_stop():
    """Stop Docker Compose services"""
    console.print("🛑 Stopping Docker Compose services...")
    try:
        subprocess.run(["docker", "compose", "down"], 
                      cwd=PROJECT_DIR, check=True)
        console.print("✅ Services stopped")
    except subprocess.CalledProcessError as e:
        console.print(f"❌ Failed to stop services: {e}")
        sys.exit(1)


@click.command()
def clean():
    """Clean up build artifacts and caches"""
    console.print("🧹 Cleaning up...")
    
    # Clean Python cache
    for cache_dir in PROJECT_DIR.rglob("__pycache__"):
        shutil.rmtree(cache_dir, ignore_errors=True)
        console.print(f"   Removed {cache_dir}")
    
    for cache_file in PROJECT_DIR.rglob("*.pyc"):
        cache_file.unlink(missing_ok=True)
    
    # Clean .pytest_cache
    pytest_cache = PROJECT_DIR / ".pytest_cache"
    if pytest_cache.exists():
        shutil.rmtree(pytest_cache)
        console.print("   Removed .pytest_cache")
    
    # Clean dist/build directories
    for build_dir in ["dist", "build", "*.egg-info"]:
        for path in PROJECT_DIR.glob(build_dir):
            if path.is_dir():
                shutil.rmtree(path)
                console.print(f"   Removed {path}")
    
    console.print("✅ Cleanup complete")


@click.command()
def test():
    """Run tests"""
    console.print("🧪 Running tests...")
    
    try:
        subprocess.run(["uv", "run", "pytest", "-v"], 
                      cwd=PROJECT_DIR, check=True)
        console.print("✅ All tests passed")
    except subprocess.CalledProcessError:
        console.print("❌ Some tests failed")
        sys.exit(1)


@click.command()
def lint():
    """Run linting and formatting checks"""
    console.print("🔍 Running linting...")
    
    # Check if tools are available
    tools = []
    
    # Try ruff first (modern, fast)
    if shutil.which("ruff"):
        tools.append(("ruff", ["uv", "run", "ruff", "check", "."]))
    elif shutil.which("flake8"):
        tools.append(("flake8", ["uv", "run", "flake8", "memgraph/"]))
    
    if shutil.which("black"):
        tools.append(("black", ["uv", "run", "black", "--check", "."]))
    
    if not tools:
        console.print("⚠️  No linting tools found. Install ruff or flake8+black")
        return
    
    failed = False
    for name, cmd in tools:
        try:
            console.print(f"   Running {name}...")
            subprocess.run(cmd, cwd=PROJECT_DIR, check=True, 
                          capture_output=True)
            console.print(f"   ✅ {name} passed")
        except subprocess.CalledProcessError:
            console.print(f"   ❌ {name} failed")
            failed = True
    
    if failed:
        console.print("❌ Linting failed")
        sys.exit(1)
    else:
        console.print("✅ All linting passed")


@click.command()
def format_code():
    """Format code with black/ruff"""
    console.print("✨ Formatting code...")
    
    if shutil.which("ruff"):
        try:
            subprocess.run(["uv", "run", "ruff", "format", "."], 
                          cwd=PROJECT_DIR, check=True)
            console.print("✅ Code formatted with ruff")
        except subprocess.CalledProcessError:
            console.print("❌ Formatting failed")
            sys.exit(1)
    elif shutil.which("black"):
        try:
            subprocess.run(["uv", "run", "black", "."], 
                          cwd=PROJECT_DIR, check=True)
            console.print("✅ Code formatted with black")
        except subprocess.CalledProcessError:
            console.print("❌ Formatting failed")
            sys.exit(1)
    else:
        console.print("⚠️  No formatter found. Install ruff or black")


@click.command()
@click.option("--url", default="http://localhost:8080", help="Server URL to check")
def health():
    """Check server health"""
    console.print(f"🏥 Checking server health at {url}")
    
    try:
        response = requests.get(f"{url}/health", timeout=5)
        if response.status_code == 200:
            console.print("✅ Server is healthy")
            
            # Show some basic stats if available
            try:
                data = response.json()
                if isinstance(data, dict):
                    for key, value in data.items():
                        console.print(f"   {key}: {value}")
            except:
                pass
        else:
            console.print(f"❌ Server unhealthy: HTTP {response.status_code}")
            sys.exit(1)
    except requests.RequestException as e:
        console.print(f"❌ Server unreachable: {e}")
        sys.exit(1)


@click.command()
def logs():
    """Show Docker Compose logs"""
    console.print("📋 Showing logs...")
    try:
        subprocess.run(["docker", "compose", "logs", "-f"], 
                      cwd=PROJECT_DIR, check=True)
    except KeyboardInterrupt:
        console.print("\\n👋 Stopped following logs")
    except subprocess.CalledProcessError as e:
        console.print(f"❌ Failed to show logs: {e}")


# Add all commands to the group
dev.add_command(install)
dev.add_command(run)
dev.add_command(build)
dev.add_command(docker_run)
dev.add_command(docker_stop)
dev.add_command(clean)
dev.add_command(test)
dev.add_command(lint)
dev.add_command(format_code)
dev.add_command(health)
dev.add_command(logs)


if __name__ == "__main__":
    dev()
