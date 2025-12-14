"""Server launcher and process management utilities"""

import json
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any, Literal

import psutil


DEFAULT_PORT: Literal[6789] = 6789
CONFIG_DIR: Path = Path.home() / ".zabob" / "memgraph"
DOCKER_IMAGE: str = "bobkerns/zabob-memgraph:latest"
DEFAULT_CONTAINER_NAME: str = "zabob-memgraph"


def find_free_port(start_port: int = DEFAULT_PORT) -> int:
    """Find a free port starting from start_port"""
    for port in range(start_port, start_port + 100):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    raise RuntimeError(
        f"Could not find a free port in range {start_port}-{start_port + 100}"
    )


def is_port_available(port: int, host: str = 'localhost') -> bool:
    """Check if a port is available"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, port))
            return True
    except OSError:
        return False


def load_launcher_config(config_dir: Path) -> dict[str, Any]:
    """Load launcher configuration from file or return defaults"""
    config_file = config_dir / "launcher_config.json"

    defaults: dict[str, Any] = {
        "default_port": DEFAULT_PORT,
        "default_host": "localhost",
        "docker_image": DOCKER_IMAGE,
        "container_name": DEFAULT_CONTAINER_NAME,
    }

    if config_file.exists():
        try:
            with open(config_file) as f:
                user_config = json.load(f)
                defaults.update(user_config)
        except Exception:
            pass

    return defaults


def save_launcher_config(config_dir: Path, config: dict[str, Any]) -> None:
    """Save launcher configuration to file"""
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "launcher_config.json"

    try:
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception:
        pass


def is_server_running(config_dir: Path) -> bool:
    """Check if the server is running based on server_info.json"""
    info_file = config_dir / "server_info.json"

    if not info_file.exists():
        return False

    try:
        with open(info_file) as f:
            info = json.load(f)

        # Check if process is actually running
        pid = info.get('pid')
        if pid:
            return bool(psutil.pid_exists(pid))

        # Check if Docker container is running
        docker_container = info.get('docker_container')
        if docker_container:
            result = subprocess.run(
                ['docker', 'ps', '-q', '-f', f'name={docker_container}'],
                capture_output=True,
                text=True,
                check=False,
            )
            return bool(result.stdout.strip())

        return False
    except Exception:
        return False


def get_server_info(config_dir: Path) -> dict[str, Any]:
    """Get server information from server_info.json"""
    info_file = config_dir / "server_info.json"

    try:
        with open(info_file) as f:
            data: dict[str, Any] = json.load(f)
            return data
    except Exception:
        return {}


def save_server_info(config_dir: Path, **info: Any) -> None:
    """Save server information to server_info.json"""
    config_dir.mkdir(parents=True, exist_ok=True)
    info_file = config_dir / "server_info.json"

    with open(info_file, 'w') as f:
        json.dump(info, f, indent=2)


def cleanup_server_info(config_dir: Path) -> None:
    """Remove server_info.json file"""
    info_file = config_dir / "server_info.json"
    if info_file.exists():
        info_file.unlink()


def start_local_server(
    config_dir: Path, port: int | None, host: str, console: Any
) -> None:
    """Start the server locally as a background process"""
    from memgraph.config import load_config

    # Load config
    config = load_config()

    # Determine port
    if port is not None:
        console.print(f"🔒 Port explicitly set to {port} (auto-finding disabled)")
    else:
        launcher_config = load_launcher_config(config_dir)
        port = launcher_config.get('port', config.get('port', DEFAULT_PORT))
        if not isinstance(port, int):
            port = DEFAULT_PORT
        if not is_port_available(port, host):
            port = find_free_port(port)
            launcher_config['port'] = port
            save_launcher_config(config_dir, launcher_config)
            console.print(f"📍 Using available port {port}")

    console.print(f"🚀 Starting server on {host}:{port}")

    # Start uvicorn in background
    cmd = [
        sys.executable,
        '-m',
        'uvicorn',
        'memgraph.service:app',
        f'--host={host}',
        f'--port={port}',
    ]

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

        # Save server info
        save_server_info(config_dir, pid=process.pid, port=port, host=host)

        console.print(f"✅ Server started (PID: {process.pid})")
        console.print(f"🌐 Web interface: http://{host}:{port}")

    except Exception as e:
        console.print(f"❌ Failed to start server: {e}")
        sys.exit(1)


def start_docker_server(
    config_dir: Path,
    port: int | None,
    host: str,
    detach: bool,
    console: Any,
    docker_image: str | None = None,
    container_name: str | None = None,
) -> None:
    """Start the server using Docker"""
    launcher_config = load_launcher_config(config_dir)

    match docker_image:
        case None | "":
            docker_image = launcher_config.get('docker_image', DOCKER_IMAGE)
        case str() if docker_image.startswith(":"):
            default = launcher_config.get('docker_image', DOCKER_IMAGE)
            docker_image = f'{default.split(":")[0]}{docker_image}'
        case _:
            pass  # Use provided docker_image as is

    match container_name:
        case None | "":
            _container_name = launcher_config.get('container_name', DEFAULT_CONTAINER_NAME)
        case _:
            _container_name = container_name  # Use provided container_name as is

    if port is None:
        port = launcher_config.get('port', DEFAULT_PORT)
        if not isinstance(port, int):
            port = DEFAULT_PORT
        if not is_port_available(port, host):
            port = find_free_port(port)
            launcher_config['port'] = port
            save_launcher_config(config_dir, launcher_config)

    # Build Docker run command
    cmd = [
        'docker',
        'run',
        '--rm',
        '--init',
        '-it' if not detach else '-d',
        '--name',
        _container_name,
        '-p',
        f'{port}:{DEFAULT_PORT}',
        '-v',
        f'{config_dir}:/app/.zabob/memgraph',
        docker_image,
    ]

    try:
        if detach:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            container_id = result.stdout.strip()
            save_server_info(
                config_dir,
                port=port,
                docker_container=container_name,
                container_id=container_id,
                host=host,
            )
            console.print(f"✅ Docker container started: {container_name}")
            console.print(f"🌐 Web interface: http://{host}:{port}")
        else:
            save_server_info(
                config_dir, port=port, docker_container=container_name, host=host
            )
            console.print(f"🌐 Web interface: http://{host}:{port}")
            subprocess.run(cmd, check=True)

    except subprocess.CalledProcessError as e:
        console.print(f"❌ Failed to start Docker container: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n👋 Stopping container...")
        subprocess.run(['docker', 'stop', _container_name], capture_output=True)
        cleanup_server_info(config_dir)


def is_dev_environment() -> bool:
    """Check if running in development environment"""
    project_root = Path(__file__).parent.parent

    # Check for .git directory
    if (project_root / ".git").exists():
        return True

    # Check for dev dependencies
    try:
        import watchfiles  # noqa: F401

        return True
    except ImportError:
        pass

    return False
