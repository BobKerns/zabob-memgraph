#!/usr/bin/env uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click>=8.3.1",
#     "psutil>=7.1.3",
#     "requests>=2.32.5",
#     "rich>=14.2.0",
# ]
# ///
"""
Zabob Memgraph CLI

Command-line interface for the Zabob Memgraph knowledge graph server.
"""

import os
import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

import click
import psutil
import requests
from rich.console import Console
from rich.panel import Panel

from memgraph.launcher import (
    cleanup_server_info,
    find_free_port,
    get_server_info,
    is_dev_environment,
    is_port_available,
    is_server_running,
    load_launcher_config,
    save_launcher_config,
    start_docker_server,
    start_local_server,
    DEFAULT_PORT,
    CONFIG_DIR,
    DEFAULT_CONTAINER_NAME,
)

console = Console()

# Configuration
IN_DOCKER = os.environ.get('DOCKER_CONTAINER') == '1'


@click.group()
@click.version_option()
@click.option(
    "--config-dir",
    type=click.Path(path_type=Path),
    default=CONFIG_DIR,
    help="Configuration directory",
)
@click.pass_context
def cli(ctx: click.Context, config_dir: Path) -> None:
    """Zabob Memgraph - Knowledge Graph Server"""
    ctx.ensure_object(dict)
    ctx.obj['config_dir'] = config_dir
    config_dir.mkdir(exist_ok=True)


@click.command()
@click.option("--port", type=int, help="Specific port to use")
@click.option("--host", default="localhost", help="Host to bind to")
@click.option("--docker", is_flag=True, help="Run using Docker")
@click.option("--name", type=str, default=DEFAULT_CONTAINER_NAME, help="Docker container name")
@click.option("--image", type=str, default=':latest', help="Docker image name and/or label")
@click.option("--detach", "-d", is_flag=True, help="Run in background (Docker only)")
@click.pass_context
def start(
    ctx: click.Context, port: int | None, host: str, docker: bool, detach: bool,
    name: str, image: str
) -> None:
    """Start the Zabob Memgraph server"""
    # In Docker, 'start' behaves like 'run' (foreground)
    if IN_DOCKER:
        ctx.invoke(run, port=port, host=host, reload=False)
        return
    config_dir: Path = ctx.obj['config_dir']

    # Check if server is already running
    if is_server_running(config_dir):
        info = get_server_info(config_dir)
        console.print(
            f"❌ Server already running on port {info['port']} (PID: {info.get('pid', 'N/A')})"
        )
        console.print("Use 'zabob-memgraph stop' to stop it first")
        sys.exit(1)

    if docker:
        start_docker_server(config_dir=config_dir, port=port, host=host, detach=detach,
                            console=console, docker_image=image, container_name=name)
    else:
        start_local_server(config_dir=config_dir, port=port, host=host, console=console)


@click.command()
@click.pass_context
def stop(ctx: click.Context) -> None:
    """Stop the Zabob Memgraph server"""
    config_dir: Path = ctx.obj['config_dir']

    if not is_server_running(config_dir):
        console.print("❌ No server running")
        sys.exit(1)

    info = get_server_info(config_dir)

    if info.get('docker_container'):
        # Stop Docker container
        try:
            subprocess.run(
                ['docker', 'stop', info['docker_container']],
                check=True,
                capture_output=True,
            )
            console.print(f"✅ Stopped Docker container {info['docker_container']}")
        except subprocess.CalledProcessError as e:
            console.print(f"❌ Failed to stop Docker container: {e}")
            sys.exit(1)
    else:
        # Stop local process
        process = None
        try:
            pid = info.get('pid')
            if pid:
                process = psutil.Process(pid)
                process.terminate()
                process.wait(timeout=10)
                console.print(f"✅ Server stopped (PID: {pid})")
            else:
                console.print("❌ No PID found in server info")
                sys.exit(1)
        except psutil.NoSuchProcess:
            console.print("❌ Process not found")
        except psutil.TimeoutExpired:
            console.print("⚠️  Process didn't stop gracefully, killing...")
            if process is not None:
                process.kill()
                console.print("✅ Server killed")
        except Exception as e:
            console.print(f"❌ Failed to stop server: {e}")
            sys.exit(1)

    cleanup_server_info(config_dir)


@click.command()
@click.option("--port", type=int, help="Specific port to use")
@click.option("--host", default="localhost", help="Host to bind to")
@click.option("--docker", is_flag=True, help="Run using Docker")
@click.option("--detach", "-d", is_flag=True, help="Run in background (Docker only)")
@click.pass_context
def restart(
    ctx: click.Context, port: int | None, host: str, docker: bool, detach: bool
) -> None:
    """Restart the Zabob Memgraph server"""
    config_dir: Path = ctx.obj['config_dir']

    if is_server_running(config_dir):
        ctx.invoke(stop)
        console.print("⏳ Waiting for server to stop...")
        time.sleep(2)

    ctx.invoke(start, port=port, host=host, docker=docker, detach=detach)


@click.command()
@click.pass_context
def open_browser(ctx: click.Context) -> None:
    """Open browser to the knowledge graph interface"""
    if IN_DOCKER:
        console.print("❌ Browser opening not available in Docker container")
        console.print("Access the web UI from your host machine")
        sys.exit(1)

    config_dir: Path = ctx.obj['config_dir']

    if not is_server_running(config_dir):
        console.print("❌ No server running")
        console.print("Start the server first with: zabob-memgraph start")
        sys.exit(1)

    info = get_server_info(config_dir)
    url = f"http://{info.get('host', 'localhost')}:{info['port']}"

    console.print(f"🌐 Opening {url} in your browser...")
    webbrowser.open(url)


@click.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Check server status"""
    config_dir: Path = ctx.obj['config_dir']

    if is_server_running(config_dir):
        info = get_server_info(config_dir)

        status_lines = ["Server Status: [green]RUNNING[/green]"]

        if info.get('docker_container'):
            status_lines.append(f"Container: {info['docker_container']}")
            if info.get('container_id'):
                status_lines.append(f"Container ID: {info['container_id'][:12]}")
        else:
            status_lines.append(f"PID: {info.get('pid', 'N/A')}")

        status_lines.append(f"Port: {info.get('port', 'N/A')}")
        status_lines.append(f"Host: {info.get('host', 'localhost')}")
        status_lines.append(
            f"Web Interface: http://{info.get('host', 'localhost')}:{info['port']}"
        )

        console.print(
            Panel("\n".join(status_lines), title="Zabob Memgraph Server")
        )
    else:
        console.print(
            Panel(
                "Server Status: [red]NOT RUNNING[/red]",
                title="Zabob Memgraph Server",
            )
        )
        sys.exit(1)


@click.command()
@click.option("--interval", default=5, help="Check interval in seconds")
@click.pass_context
def monitor(ctx: click.Context, interval: int) -> None:
    """Monitor server health"""
    config_dir: Path = ctx.obj['config_dir']

    if not is_server_running(config_dir):
        console.print("❌ No server running to monitor")
        sys.exit(1)

    info = get_server_info(config_dir)
    base_url = f"http://localhost:{info['port']}"

    console.print(
        Panel(
            f"Monitoring server at {base_url} (Ctrl+C to stop)",
            title="📡 Server Monitor",
        )
    )

    try:
        while True:
            try:
                response = requests.get(f"{base_url}/health", timeout=3)
                if response.status_code == 200:
                    timestamp = time.strftime("%H:%M:%S")
                    console.print(f"[green]{timestamp}[/green] ✅ Server healthy")
                else:
                    timestamp = time.strftime("%H:%M:%S")
                    console.print(
                        f"[red]{timestamp}[/red] ❌ Server unhealthy - "
                        f"HTTP {response.status_code}"
                    )
            except requests.RequestException:
                timestamp = time.strftime("%H:%M:%S")
                console.print(f"[red]{timestamp}[/red] ❌ Server unreachable")

            time.sleep(interval)
    except KeyboardInterrupt:
        console.print("\n👋 Monitoring stopped")


@click.command()
@click.pass_context
def test(ctx: click.Context) -> None:
    """Test server endpoints"""
    config_dir: Path = ctx.obj['config_dir']

    if not is_server_running(config_dir):
        console.print("❌ No server running to test")
        sys.exit(1)

    info = get_server_info(config_dir)
    base_url = f"http://localhost:{info['port']}"

    console.print(Panel("Testing server endpoints...", title="🧪 Endpoint Tests"))

    # Test endpoints
    endpoints = [
        ("/", "Web UI"),
        ("/health", "Health check"),
        ("/mcp", "MCP endpoint"),
    ]

    all_passed = True

    for path, description in endpoints:
        url = f"{base_url}{path}"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                console.print(f"✅ {description}: {url}")
            else:
                console.print(
                    f"❌ {description}: {url} - HTTP {response.status_code}"
                )
                all_passed = False
        except requests.RequestException as e:
            console.print(f"❌ {description}: {url} - {e}")
            all_passed = False

    if all_passed:
        console.print("\n✅ All tests passed!")
    else:
        console.print("\n❌ Some tests failed")
        sys.exit(1)


# Development commands
@click.command()
@click.option('--port', type=int, default=None, help='Port to run on')
@click.option('--host', default=None, help='Host to bind to')
@click.option(
    '--reload', is_flag=True, help='Enable auto-reload on code changes (dev only)'
)
@click.pass_context
def run(ctx: click.Context, port: int | None, host: str | None, reload: bool) -> None:
    """Run server in foreground (for stdio mode or development)

    Unlike 'start', this runs the server in the foreground and blocks.
    Use this for:
    - stdio mode with AI assistants
    - Development with --reload
    - Docker containers (doesn't spawn background process)

    For background daemon, use 'start' instead.
    """
    config_dir: Path = ctx.obj['config_dir']
    config_dir.mkdir(parents=True, exist_ok=True)

    # Load config
    config = load_launcher_config(config_dir)

    # Default host: 0.0.0.0 in Docker, localhost otherwise
    if host is None:
        host = '0.0.0.0' if IN_DOCKER else 'localhost'

    # If port explicitly specified, disable auto port finding
    if port is not None:
        console.print(f"🔒 Port explicitly set to {port} (auto-finding disabled)")
    else:
        port_value = config.get('port', DEFAULT_PORT)
        port = port_value if isinstance(port_value, int) else DEFAULT_PORT
        if not is_port_available(port, host):
            port = find_free_port(port)
            config['port'] = port
            save_launcher_config(config_dir, config)
            console.print(f"📍 Using available port {port}")

    console.print(f"🚀 Starting server on {host}:{port}")
    if reload:
        console.print("🔄 Auto-reload enabled")

    # Build command - use the memgraph.service module
    cmd = ['uvicorn', 'memgraph.service:app', f'--host={host}', f'--port={port}']
    if reload:
        cmd.append('--reload')

    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        console.print("\n👋 Server stopped")


@click.command()
@click.option('--tag', default='zabob-memgraph:latest', help='Docker image tag')
@click.option('--no-cache', is_flag=True, help='Build without cache')
def build(tag: str, no_cache: bool) -> None:
    """Build Docker image"""
    project_root = Path(__file__).parent.parent
    cmd = ['docker', 'build', '-t', tag]
    if no_cache:
        cmd.append('--no-cache')
    cmd.append(str(project_root))

    console.print(f"🐳 Building Docker image: {tag}")
    if no_cache:
        console.print("♻️  Building without cache")

    try:
        subprocess.run(cmd, check=True)
        console.print(f"✅ Image built successfully: {tag}")
    except subprocess.CalledProcessError as e:
        console.print(f"❌ Build failed: {e}")
        sys.exit(1)


@click.command()
def lint() -> None:
    """Run linting checks (ruff, mypy)"""
    project_root = Path(__file__).parent.parent
    console.print("🔍 Running linters...")

    # Run ruff
    console.print("\n📝 Checking with ruff...")
    result = subprocess.run(['uv', 'run', 'ruff', 'check', 'memgraph/'], cwd=project_root)

    # Run mypy
    console.print("\n🔬 Checking with mypy...")
    result2 = subprocess.run(
        ['uv', 'run', 'mypy', '--strict', 'memgraph/'], cwd=project_root
    )

    if result.returncode == 0 and result2.returncode == 0:
        console.print("✅ All checks passed!")
    else:
        sys.exit(1)


@click.command(name="format")
def format_code() -> None:
    """Format code with ruff"""
    project_root = Path(__file__).parent.parent
    console.print("✨ Formatting code with ruff...")

    result = subprocess.run(
        ['uv', 'run', 'ruff', 'format', '.'], cwd=project_root, check=False
    )

    if result.returncode == 0:
        console.print("✅ Code formatted successfully!")
    else:
        console.print("❌ Formatting failed")
        sys.exit(1)


@click.command()
def clean() -> None:
    """Clean build artifacts and cache"""
    project_root = Path(__file__).parent.parent
    console.print("🧹 Cleaning build artifacts...")

    patterns = [
        '**/__pycache__',
        '**/*.pyc',
        '**/*.pyo',
        '**/*.egg-info',
        'dist',
        'build',
        '.pytest_cache',
        '.mypy_cache',
        '.ruff_cache',
    ]

    count = 0
    for pattern in patterns:
        for path in project_root.glob(pattern):
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            count += 1

    console.print(f"✅ Cleaned {count} items")


# Add commands to the CLI group
cli.add_command(start)
cli.add_command(run)  # Available in all modes (stdio, development, production)

# Don't add process management commands in Docker
if not IN_DOCKER:
    cli.add_command(stop)
    cli.add_command(restart)
    cli.add_command(status)
    cli.add_command(monitor)
    cli.add_command(test)
    cli.add_command(open_browser, name="open")

# Add development commands only in local dev environment
# (Not in Docker - no source code to operate on)
if is_dev_environment() and not IN_DOCKER:
    cli.add_command(build)
    cli.add_command(lint)
    cli.add_command(format_code)
    cli.add_command(clean)


if __name__ == "__main__":
    cli()
