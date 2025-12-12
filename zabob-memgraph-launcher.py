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
Zabob Memgraph Launcher

A launcher script for the Zabob Memgraph knowledge graph server.
Handles port management, process tracking, and Docker integration.
"""

import json
import os
import shutil
import socket
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

console = Console()

# Configuration
DEFAULT_PORT = 6789
CONFIG_DIR = Path.home() / ".zabob-memgraph"
DOCKER_IMAGE = "zabob-memgraph:latest"


@click.group()
@click.version_option()
@click.option("--config-dir", type=click.Path(path_type=Path),
              default=CONFIG_DIR, help="Configuration directory")
@click.pass_context
def cli(ctx, config_dir: Path):
    """Zabob Memgraph - Knowledge Graph Server"""
    ctx.ensure_object(dict)
    ctx.obj['config_dir'] = config_dir
    config_dir.mkdir(exist_ok=True)


@click.command()
@click.option("--port", type=int, help="Specific port to use")
@click.option("--host", default="localhost", help="Host to bind to")
@click.option("--docker", is_flag=True, help="Run using Docker")
@click.option("--detach", "-d", is_flag=True, help="Run in background (Docker only)")
@click.pass_context
def start(ctx, port: int | None, host: str, docker: bool, detach: bool):
    """Start the Zabob Memgraph server"""
    config_dir = ctx.obj['config_dir']

    # Check if server is already running
    if is_server_running(config_dir):
        info = get_server_info(config_dir)
        console.print(f"❌ Server already running on port {info['port']} (PID: {info['pid']})")
        console.print("Use 'zabob-memgraph stop' to stop it first")
        sys.exit(1)

    if docker:
        start_docker_server(config_dir, port, host, detach)
    else:
        start_local_server(config_dir, port, host)


@click.command()
@click.pass_context
def stop(ctx):
    """Stop the Zabob Memgraph server"""
    config_dir = ctx.obj['config_dir']

    if not is_server_running(config_dir):
        console.print("❌ No server running")
        sys.exit(1)

    info = get_server_info(config_dir)

    if info.get('docker_container'):
        # Stop Docker container
        try:
            subprocess.run(['docker', 'stop', info['docker_container']],
                           check=True, capture_output=True)
            console.print(f"✅ Stopped Docker container {info['docker_container']}")
        except subprocess.CalledProcessError as e:
            console.print(f"❌ Failed to stop Docker container: {e}")
            sys.exit(1)
    else:
        # Stop local process
        try:
            psutil.Process(info['pid']).terminate()
            console.print(f"✅ Stopped server (PID: {info['pid']})")
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            console.print(f"❌ Failed to stop server: {e}")

    # Clean up server info
    cleanup_server_info(config_dir)


@click.command()
@click.pass_context
@click.option("--port", type=int, default=None, help="Port to run on")
@click.option("--host", default="localhost", help="Host to bind to")
@click.option("--docker", is_flag=True, help="Use Docker")
@click.option("--detach", is_flag=True, default=True, help="Run in background")
def restart(ctx, port: int | None, host: str, docker: bool, detach: bool):
    """Restart the Zabob Memgraph server"""
    config_dir = ctx.obj['config_dir']
    
    # Stop if running
    if is_server_running(config_dir):
        console.print("🛑 Stopping existing server...")
        ctx.invoke(stop)
        time.sleep(1)
    
    # Start server
    console.print("🚀 Starting server...")
    ctx.invoke(start, port=port, host=host, docker=docker, detach=detach)


@click.command()
@click.pass_context
def open_browser(ctx):
    """Open browser to the knowledge graph visualization"""
    config_dir = ctx.obj['config_dir']
    
    if not is_server_running(config_dir):
        console.print("❌ No server running. Start with 'zabob-memgraph start'")
        sys.exit(1)
    
    info = get_server_info(config_dir)
    
    # Check if running in Docker
    if info.get('docker_container'):
        port = info.get('port', 6789)
        host = info.get('host', 'localhost')
        url = f"http://{host}:{port}"
        console.print("⚠️  Server is running in Docker container")
        console.print(f"   Open browser manually to: {url}")
        sys.exit(0)
    
    port = info.get('port', 6789)
    host = info.get('host', 'localhost')
    url = f"http://{host}:{port}"
    
    console.print(f"🌐 Opening browser to {url}")
    try:
        webbrowser.open(url)
        console.print("✅ Browser opened")
    except Exception as e:
        console.print(f"⚠️  Could not open browser: {e}")
        console.print(f"   Please open manually: {url}")


@click.command()
@click.pass_context
def status(ctx):
    """Check server status"""
    config_dir = ctx.obj['config_dir']

    if is_server_running(config_dir):
        info = get_server_info(config_dir)
        console.print(Panel(f"""
Server Status: [green]RUNNING[/green]
Port: {info['port']}
PID: {info.get('pid', 'N/A')}
Docker: {info.get('docker_container', 'No')}
Started: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(info.get('timestamp', time.time())))}

Web Interface: http://localhost:{info['port']}
""", title="Zabob Memgraph Server"))
    else:
        console.print(Panel("Server Status: [red]NOT RUNNING[/red]", title="Zabob Memgraph Server"))
        sys.exit(1)


@click.command()
@click.option("--interval", default=5, help="Check interval in seconds")
@click.pass_context
def monitor(ctx, interval: int):
    """Monitor server health"""
    config_dir = ctx.obj['config_dir']

    if not is_server_running(config_dir):
        console.print("❌ No server running to monitor")
        sys.exit(1)

    info = get_server_info(config_dir)
    base_url = f"http://localhost:{info['port']}"

    console.print(Panel(f"Monitoring server at {base_url} (Ctrl+C to stop)",
                        title="📡 Server Monitor"))

    try:
        while True:
            try:
                response = requests.get(f"{base_url}/health", timeout=3)
                if response.status_code == 200:
                    timestamp = time.strftime("%H:%M:%S")
                    console.print(f"[green]{timestamp}[/green] ✅ Server healthy")
                else:
                    timestamp = time.strftime("%H:%M:%S")
                    console.print(f"[red]{timestamp}[/red] ❌ Server unhealthy "
                                  "- HTTP {response.status_code}")
            except requests.RequestException:
                timestamp = time.strftime("%H:%M:%S")
                console.print(f"[red]{timestamp}[/red] ❌ Server unreachable")

            time.sleep(interval)
    except KeyboardInterrupt:
        console.print("\\n👋 Monitoring stopped")


@click.command()
@click.pass_context
def test(ctx):
    """Test server endpoints"""
    config_dir = ctx.obj['config_dir']

    if not is_server_running(config_dir):
        console.print("❌ No server running to test")
        sys.exit(1)

    info = get_server_info(config_dir)
    base_url = f"http://localhost:{info['port']}"

    console.print(Panel(f"Testing server at {base_url}", title="🧪 Server Test"))

    tests_passed = 0
    total_tests = 4

    # Test health endpoint
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            console.print("✅ Health check passed")
            tests_passed += 1
        else:
            console.print(f"❌ Health check failed: {response.status_code}")
    except requests.RequestException as e:
        console.print(f"❌ Health check error: {e}")

    # Test knowledge graph endpoint
    try:
        response = requests.get(f"{base_url}/api/knowledge-graph", timeout=10)
        if response.status_code == 200:
            data = response.json()
            console.print(f"✅ Knowledge graph OK - {len(data.get('nodes', []))} entities")
            tests_passed += 1
        else:
            console.print(f"❌ Knowledge graph failed: {response.status_code}")
    except requests.RequestException as e:
        console.print(f"❌ Knowledge graph error: {e}")

    # Test search endpoint
    try:
        response = requests.get(f"{base_url}/api/search?q=test", timeout=5)
        if response.status_code == 200:
            console.print("✅ Search endpoint working")
            tests_passed += 1
        else:
            console.print(f"❌ Search failed: {response.status_code}")
    except requests.RequestException as e:
        console.print(f"❌ Search error: {e}")

    # Test entity creation
    test_entity = {
        "name": f"Test Entity {int(time.time())}",
        "entityType": "test",
        "observations": ["Created by launcher test"]
    }

    try:
        response = requests.post(f"{base_url}/api/entities", json=[test_entity], timeout=5)
        if response.status_code == 200:
            console.print("✅ Entity creation working")
            tests_passed += 1
        else:
            console.print(f"❌ Entity creation failed: {response.status_code}")
    except requests.RequestException as e:
        console.print(f"❌ Entity creation error: {e}")

    console.print(f"\\n🎯 Tests passed: {tests_passed}/{total_tests}")

    if tests_passed == total_tests:
        console.print("🎉 All tests passed!")
    else:
        sys.exit(1)


def find_free_port(start_port: int = DEFAULT_PORT) -> int:
    """Find a free port starting from start_port"""
    for port in range(start_port, start_port + 100):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"Could not find a free port in range {start_port}-{start_port + 100}")


def is_server_running(config_dir: Path) -> bool:
    """Check if server is running"""
    info_file = config_dir / "server_info.json"
    if not info_file.exists():
        return False

    try:
        info = json.loads(info_file.read_text())

        if info.get('docker_container'):
            # Check Docker container
            cmd = ['docker', 'inspect', '-f', '{{.State.Running}}', info['docker_container']]
            result = subprocess.run(cmd,
                                    capture_output=True, text=True)
            return bool(result.stdout.strip())
        else:
            # Check local process
            return psutil.pid_exists(info['pid']) and psutil.Process(info['pid']).is_running()
    except (json.JSONDecodeError, KeyError, psutil.NoSuchProcess):
        return False


def get_server_info(config_dir: Path) -> dict:
    """Get server information"""
    info_file = config_dir / "server_info.json"
    if info_file.exists():
        return json.loads(info_file.read_text())
    return {}


def save_server_info(config_dir: Path, **info) -> None:
    """Save server information"""
    info_file = config_dir / "server_info.json"
    info['timestamp'] = time.time()
    info_file.write_text(json.dumps(info, indent=2))


def cleanup_server_info(config_dir: Path) -> None:
    """Clean up server info files"""
    for file in ['server_info.json', 'port', 'pid']:
        (config_dir / file).unlink(missing_ok=True)


def start_local_server(config_dir: Path, port: int | None, host: str) -> None:
    """Start local server using main.py"""
    if not port:
        port = find_free_port()

    console.print(f"🚀 Starting Zabob Memgraph server on {host}:{port}")

    # Check if main.py exists
    main_py = Path("main.py")
    if not main_py.exists():
        console.print("❌ main.py not found. Are you in the correct directory?")
        sys.exit(1)

    # Start server process
    try:
        env = os.environ.copy()
        env['MEMGRAPH_PORT'] = str(port)
        env['MEMGRAPH_HOST'] = host
        env['MEMGRAPH_CONFIG_DIR'] = str(config_dir)

        process = subprocess.Popen(
            ['uv', 'run', 'main.py'],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )

        # Wait a moment for startup
        time.sleep(2)

        if process.poll() is None:  # Process is still running
            save_server_info(config_dir, port=port, pid=process.pid, host=host)
            console.print("✅ Server started successfully!")
            console.print(f"📝 PID: {process.pid}")
            console.print(f"🌐 Web interface: http://{host}:{port}")
            console.print(f"📁 Config: {config_dir}")
        else:
            console.print("❌ Server failed to start")
            if process.stdout:
                output = process.stdout.read().decode()
                console.print(f"Output: {output}")
            sys.exit(1)

    except Exception as e:
        console.print(f"❌ Failed to start server: {e}")
        sys.exit(1)


def start_docker_server(config_dir: Path, port: int | None, host: str, detach: bool) -> None:
    """Start server using Docker"""
    if not port:
        port = find_free_port()

    console.print(f"🐳 Starting Zabob Memgraph server in Docker on {host}:{port}")

    # Check if Docker is available
    if not shutil.which("docker"):
        console.print("❌ Docker not found. Please install Docker first.")
        sys.exit(1)

    # Check if image exists
    result = subprocess.run(['docker', 'images', '-q', DOCKER_IMAGE],
                            capture_output=True, text=True)
    if not result.stdout.strip():
        console.print(f"❌ Docker image {DOCKER_IMAGE} not found.")
        console.print("Please build the image first with: docker build -t zabob-memgraph .")
        sys.exit(1)

    # Generate container name
    container_name = f"zabob-memgraph-{port}"

    # Start container
    cmd = [
        'docker', 'run',
        '--name', container_name,
        '-p', f"{port}:8080",
        '-v', f"{config_dir}:/app/.zabob-memgraph"
    ]

    if detach:
        cmd.append('-d')

    cmd.append(DOCKER_IMAGE)

    try:
        if detach:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            container_id = result.stdout.strip()
            save_server_info(config_dir, port=port, docker_container=container_name,
                             container_id=container_id, host=host)
            console.print(f"✅ Docker container started: {container_name}")
            console.print(f"🌐 Web interface: http://{host}:{port}")
        else:
            save_server_info(config_dir, port=port, docker_container=container_name, host=host)
            console.print(f"🌐 Web interface: http://{host}:{port}")
            subprocess.run(cmd, check=True)

    except subprocess.CalledProcessError as e:
        console.print(f"❌ Failed to start Docker container: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\\n👋 Stopping container...")
        subprocess.run(['docker', 'stop', container_name], capture_output=True)
        cleanup_server_info(config_dir)


# Add commands to the CLI group
cli.add_command(start)
cli.add_command(stop)
cli.add_command(restart)
cli.add_command(status)
cli.add_command(monitor)
cli.add_command(test)
cli.add_command(open_browser, name="open")


if __name__ == "__main__":
    cli()
