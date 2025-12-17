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

from memgraph.config import (
    CONFIG_DIR, load_config, save_config, IN_DOCKER,
)
from memgraph.launcher import (
    ServerStatus, server_status,
    cleanup_server_info,
    find_free_port,
    get_server_info,
    get_one_server_info,
    is_dev_environment,
    is_port_available,
    is_server_running,
    start_docker_server,
    start_local_server,
)
from memgraph.service import run_server as run_server


console = Console()


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
@click.option("--log-level", default=None, help="Logging level")
@click.option("--access-log", type=bool, default=None, help="Enable access logging")
@click.option("--docker", is_flag=True, default=False, help="Run using Docker")
@click.option("--name", type=str, default=None, help="Docker container name")
@click.option("--image", type=str, default=':latest', help="Docker image name and/or label")
@click.option('--database-path', type=Path, default=None, help='Path to the database file')
@click.option("--detach", "-d", is_flag=True, default=False, help="Run in background (Docker only)")
@click.pass_context
def start(
    ctx: click.Context,
    port: int | None,
    host: str,
    log_level: str | None,
    access_log: bool | None,
    name: str,
    image: str,
    database_path: Path | None,
    docker: bool = False,
    detach: bool = False,
) -> None:
    """Start the Zabob Memgraph server"""
    # In Docker, 'start' behaves like 'run' (foreground)
    if IN_DOCKER:
        ctx.invoke(run,
                   port=port,
                   host=host,
                   reload=False,
                   config_dir=ctx.obj['config_dir'],
                   database_path=database_path)
        return
    config_dir: Path = ctx.obj['config_dir']

    if database_path is not None and not database_path.is_absolute():
        database_path = database_path.resolve()

    config = load_config(config_dir,
                         host=host,
                         port=port,
                         container_name=name,
                         image=image,
                         database_path=database_path,
                         log_level=log_level,
                         access_log=access_log,
                         )

    database_path = Path(config['database_path']).resolve()

    # Check if server is already running
    info = get_one_server_info(config_dir,
                               port=port,
                               host=host,
                               name=name,
                               image=image,
                               database_path=database_path)
    status = server_status(info)
    match status, info:
        case ServerStatus.GONE, _:
            pass
        case ServerStatus.RUNNING, {'port': int() as port, 'pid': int() as pid}:
            console.print(f"❌ Server already running on port {port} (PID: {pid})")
            exit(1)
        case ServerStatus.RUNNING, {'docker_container': str() as container, 'container_id': str() as container_id}:
            console.print(f"❌ Server already running in Docker container {container} (ID: {container_id[:12]})")
            exit(1)
        case ServerStatus.RUNNING, {'docker_container': str() as container}:
            console.print(f"❌ Server already running in Docker container {container}")
            exit(1)
        case ServerStatus.RUNNING, _:
            console.print("❌ Server already running")
            exit(1)
        case ServerStatus.STOPPED, {'docker_container': str() as name, 'container_id': str() as cid}:
            console.print(f"✅ Starting stopped Docker container {name} ({cid[:12]})...")
            subprocess.run(['docker', 'start', name], check=True)
            exit(0)
        case ServerStatus.STOPPED, {'docker_container': str() as c_name}:
            console.print(f"✅ Starting stopped Docker container {c_name}")
            subprocess.run(['docker', 'start', '--detach', c_name], check=True)
            exit(0)
        case status, _:
            console.print(f"⚠️  Server process found but not working: {status}")
            console.print("Please stop it first using 'zabob-memgraph stop'")
            exit(1)

    if docker:
        start_docker_server(config,
                            console=console,
                            explicit_port=port,
                            detach=detach,
                            )
    else:
        start_local_server(config,
                           console=console,
                           explicit_port=port)


@click.command()
@click.pass_context
@click.option("--port", type=int, help="Specific port the server is running on")
@click.option("--pid", type=int, help="Specific PID of the server process")
def stop(ctx: click.Context, port: int | None, pid: int | None) -> None:
    """Stop the Zabob Memgraph server"""
    config_dir: Path = ctx.obj['config_dir']

    servers = get_server_info(config_dir, port=port, pid=pid)
    if not servers:
        console.print("❌ No matching server found to stop")
        return
    for info in servers:
        pid = pid or info['pid']
        match info:
            case {"docker_container": str() as container}:
                # Stop Docker container
                try:
                    subprocess.run(
                        ['docker', 'stop', container],
                        check=True,
                        capture_output=True,
                    )
                    console.print(f"✅ Stopped Docker container {info['docker_container']}")
                    cleanup_server_info(config_dir, docker_container=container)
                except subprocess.CalledProcessError as e:
                    console.print(f"❌ Failed to stop Docker container: {e}")
                    continue
            case {'pid': int() as this_pid, 'port': int() as this_port}:
                # Stop local process
                process = None
                try:
                    process = psutil.Process(this_pid)
                    process.terminate()
                    process.wait(timeout=10)
                    console.print(f"✅ Server stopped (PID: {this_pid}, port: {this_port})")

                    cleanup_server_info(config_dir, pid=this_pid, port=this_port)
                    continue
                except psutil.NoSuchProcess:
                    console.print(f"❌ Process {this_pid} (port {this_port}), not found")
                    cleanup_server_info(config_dir, pid=this_pid, port=this_port)
                    continue
                except psutil.TimeoutExpired:
                    console.print(f"⚠️  Process {this_pid} (port {this_port}) didn't stop gracefully, killing...")
                    if process is not None:
                        process.kill()
                        console.print(f"✅ Process {this_pid} (port {this_port})  forcefully killed")
                        cleanup_server_info(config_dir, pid=this_pid, port=this_port)
                    continue
                except Exception as e:
                    console.print(f"❌ Failed to stop server (pid {this_pid}, port {this_port}): {e}")
                    continue


@click.command()
@click.option("--port", type=int, default=None, help="Specific port to use")
@click.option("--host", default=None, help="Host to bind to")
@click.option("--docker", is_flag=True, help="Run using Docker")
@click.option("--name", type=str, default=None, help="Docker container name")
@click.option("--image", type=str, default=':latest', help="Docker image name and/or label")
@click.option('--database-path', type=Path, default=None, help='Path to the database file')
@click.option('--log-level', type=str, default=None, help='Logging level')
@click.option('--access-log/--no-access-log', default=None, help='Enable or disable access log')
@click.option("--detach", "-d", is_flag=True, help="Run in background (Docker only)")
@click.pass_context
def restart(
    ctx: click.Context,
    port: int | None,
    host: str | None,
    docker: bool,
    name: str | None,
    image: str,
    database_path: Path | None,
    log_level: str | None,
    access_log: bool | None, detach: bool
) -> None:
    """
    Restart the Zabob Memgraph server

    Stops the server if running, then starts it again.

    The options act as a filter to select which server to stop,
    and as configuration for the new server instance.
    """
    config_dir: Path = ctx.obj['config_dir']
    config = load_config(config_dir,
                         port=port,
                         host=host,
                         container_name=name,
                         database_path=database_path,
                         log_level=log_level,
                         access_log=access_log)
    database_path = Path(config['database_path']).resolve()

    server_info = get_one_server_info(config_dir,
                                      port=port,
                                      host=host,
                                      name=name,
                                      database_path=database_path)
    if server_info and is_server_running(server_info):
        ctx.invoke(stop,
                   port=port,
                   pid=server_info.get('pid'),
                   docker=docker,
                   name=name,
                   image=image,
                   database_path=database_path)

        console.print("⏳ Waiting for server to stop...")
        time.sleep(2)

    ctx.invoke(start,
               port=port,
               host=host,
               docker=docker,
               name=name,
               image=image,
               database_path=database_path,
               log_level=log_level,
               access_log=access_log,
               detach=detach)


@click.command()
@click.pass_context
def open_browser(ctx: click.Context) -> None:
    """Open browser to the knowledge graph interface"""
    if IN_DOCKER:
        console.print("❌ Browser opening not available in Docker container")
        console.print("Access the web UI from your host machine")
        sys.exit(1)

    config_dir: Path = ctx.obj['config_dir']
    servers = get_server_info(config_dir)

    match len(servers):
        case 0:
            console.print("❌ No server running")
            console.print("Start the server first with: zabob-memgraph start")
            sys.exit(1)
        case 1:
            info = servers[0]
            url = f"http://{info.get('host', 'localhost')}:{info['port']}"

            console.print(f"🌐 Opening {url} in your browser...")
            webbrowser.open(url)
        case _:
            console.print("❌ Multiple servers running, please specify which to open:")
            for server in servers:
                console.print(
                    f"- PID: {server.get('pid', 'N/A')}, Port: {server.get('port', 'N/A')}, "
                    f"Container: {server.get('docker_container', 'N/A')}"
                )
            sys.exit(1)


@click.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Check server status"""
    config_dir: Path = ctx.obj['config_dir']

    servers = get_server_info(config_dir)
    if servers:
        for info in servers:
            status = server_status(info)
            match status:
                case ServerStatus.RUNNING:
                    status_lines = ["Server Status: [green]RUNNING[/green]"]
                case ServerStatus.NOT_RESPONDING | ServerStatus.ERROR:
                    status_lines = ["Server Status: [red]NOT RESPONDING[/red]"]
                case ServerStatus.STOPPED:
                    status_lines = ["Server Status: [yellow]STOPPED[/yellow]"]
                case ServerStatus.GONE | ServerStatus.NOT_RUNNING:
                    status_lines = ["Server Status: [bold][dark_blue]NOT RUNNING[/dark_blue][/bold]"]
                case _:
                    status_lines = [f"Server Status: [red]{status}[/red]"]
            status_lines.append(f"Launched by: {info.get('launched_by', 'N/A')}")

            if info.get('docker_container'):
                status_lines.append(f"Container: {info['docker_container']}")
                container_id = info.get('container_id')
                if container_id:
                    status_lines.append(f"Container ID: {container_id[:12]}")
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


@click.command()
@click.option("--interval", default=5, help="Check interval in seconds")
@click.pass_context
def monitor(ctx: click.Context, interval: int) -> None:
    """Monitor server health"""
    config_dir: Path = ctx.obj['config_dir']
    header = True
    while True:
        servers = get_server_info(config_dir)
        match len(servers):
            case 0:
                console.print("❌ No server running")
                sys.exit(1)
            case _:
                for info in servers:
                    base_url = f"http://localhost:{info['port']}"
                    if header:
                        console.print(
                            Panel(
                                f"Monitoring server at {base_url} (Ctrl+C to stop)",
                                title="📡 Server Monitor",
                            )
                        )
                    else:
                        try:
                            response = requests.get(f"{base_url}/health", timeout=3)
                            if response.status_code == 200:
                                timestamp = time.strftime("%H:%M:%S")
                                console.print(f"[green]{timestamp}[/green] ✅ Server healthy at {base_url}")
                            else:
                                timestamp = time.strftime("%H:%M:%S")
                                console.print(
                                    f"[red]{timestamp}[/red] ❌ Server unhealthy at {base_url} - "
                                    f"HTTP {response.status_code}"
                                )
                        except requests.RequestException:
                            timestamp = time.strftime("%H:%M:%S")
                            console.print(f"[red]{timestamp}[/red] ❌ Server unreachable at {base_url}")
                        except KeyboardInterrupt:
                            console.print("\n👋 Monitoring stopped")
                            break
        if header:
            header = False
        else:
            time.sleep(interval)


@click.command()
@click.option("--port", type=int, default=None, help="Port listening on")
@click.option("--pid", type=int, default=None, help="Server main process PID")
@click.option("--name", type=str, default=None, help="Docker container name")
@click.pass_context
def test(ctx: click.Context, port: int | None, pid: int | None, name: str | None) -> None:
    """Test server endpoints"""
    config_dir: Path = ctx.obj['config_dir']

    info = get_one_server_info(config_dir, port=port, pid=pid, name=name)
    if info is None:
        console.print("❌ No server running")
        console.print("Start the server first with: zabob-memgraph start")
        sys.exit(1)
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
@click.option('--config-dir', type=Path, default=None, help='Configuration directory')
@click.option('--docker', is_flag=True, help='Run using Docker')
@click.option('--name', type=str, default=None, help='Docker container name')
@click.option('--docker-image', type=str, default=':latest', help='Docker image name and/or label')
@click.option('--database-path', type=Path, default=None, help='Path to the database file')
@click.option('--log-level', type=str, default=None, help='Logging level')
@click.option('--access-log/--no-access-log', default=None, help='Enable or disable access log')
@click.pass_context
def run(ctx: click.Context,
        port: int | None,
        host: str | None,
        reload: bool,
        config_dir: Path | None,
        docker: bool,
        name: str | None,
        docker_image: str,
        database_path: Path | None,
        log_level: str | None,
        access_log: bool | None) -> None:
    """Run server in foreground (for stdio mode or development)

    Unlike 'start', this runs the server in the foreground and blocks.
    Use this for:
    - stdio mode with AI assistants
    - Development with --reload
    - Docker containers (doesn't spawn background process)

    For background daemon, use 'start' instead.
    """
    config_dir = config_dir or Path(ctx.obj.get('config_dir', CONFIG_DIR))
    config_dir.mkdir(parents=True, exist_ok=True)
    config = load_config(config_dir,
                         port=port,
                         host=host,
                         reload=reload,
                         container_name=name,
                         docker_image=docker_image,
                         database_path=database_path,
                         log_level=log_level,
                         access_log=access_log,
                         )

    # Default host: 0.0.0.0 in Docker, localhost otherwise
    host = config['host']
    if host is None:
        host = '0.0.0.0' if IN_DOCKER else 'localhost'
    if IN_DOCKER:
        host = '0.0.0.0'

    # If port explicitly specified, disable auto port finding
    if port is not None:
        console.print(f"🔒 Port explicitly set to {port} (auto-finding disabled)")
    else:
        port = config['port']
        if not is_port_available(port, host):
            port = find_free_port(port)
            config['port'] = port
            save_config(config_dir, config)
            console.print(f"📍 Using available port {port}")

    console.print(f"🚀 Starting server on {host}:{port}")
    if reload:
        console.print("🔄 Auto-reload enabled")

    try:
        run_server(config=config)
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


@click.command("config")
@click.option('--port', type=int, default=None, help='Port the server is running on')
@click.option('--host', default=None, help='Host the server is binding to')
@click.option('--name', type=str, default=None, help='Docker container name')
@click.option('--image', type=str, default=None, help='Docker image name and/or label')
@click.option('--database-path', type=Path, default=None, help='Path to the database file')
@click.option('--log-level', type=str, default=None, help='Logging level')
@click.option('--access-log/--no-access-log', default=None, help='Enable or disable access log')
@click.option('--update', is_flag=True, default=False, help='Update configuration file with shown values')
@click.pass_context
def show_config(ctx: click.Context,
                port: int | None,
                host: str | None,
                name: str | None,
                image: str | None,
                log_level: str | None,
                access_log: bool | None,
                database_path: Path | None,
                update: bool) -> None:
    """
    Show current configuration

    With options, shows the configuration that would be used to start the server.
    with those options.
    """
    config_dir: Path = ctx.obj['config_dir']
    config = load_config(config_dir,
                         port=port,
                         host=host,
                         container_name=name,
                         docker_image=image,
                         database_path=database_path,
                         log_level=log_level,
                         access_log=access_log,
                         )
    lines = [
        f"[bold]{key}:[/bold] {value}"
        for key, value in config.items()
    ]
    panel = Panel("\n".join(lines), title="🛠️ Current Configuration")
    console.print(panel)
    if update:
        save_config(config_dir, config)


# Add commands to the CLI group
cli.add_command(show_config)
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
