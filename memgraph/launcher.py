"""Server launcher and process management utilities"""

from enum import StrEnum
import json
import re
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any, TypedDict, cast

import click
import requests
import psutil

from memgraph.config import DEFAULT_PORT, Config, save_config
from rich.console import Console


class ServerInfo(TypedDict):
    launched_by: str
    port: int
    pid: int | None
    host: str
    docker_container: str | None
    container_id: str | None
    image: str | None
    database_path: Path


class ServerStatus(StrEnum):
    RUNNING = "RUNNING"
    "Process is running and accepting connections"
    NOT_RESPONDING = "NOT_RESPONDING"
    "Process not responding"
    ERROR = "ERROR"
    "Error checking process"
    GONE = "GONE"
    "Process exited"
    NOT_RUNNING = "NOT_RUNNING"
    "Process exists but is not running (unusual)"
    STOPPED = "STOPPED"
    "Docker container stopped"


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


def is_server_running(server: ServerInfo | None) -> bool:
    """Check if the server is running based on servers/*.json"""
    if server is None:
        return False

    status = server_status(server)
    return status == ServerStatus.RUNNING


def server_status(info: ServerInfo | None) -> ServerStatus:
    """Get server status from ServerInfo"""
    if info is None:
        return ServerStatus.GONE
    match info:
        case {"container_id": str() as container_id}:
            return check_container(container_id)
        case {"docker_container": str() as container}:
            return check_container(container)
        case {'pid': int() as pid, 'host': str() as host, 'port': int() as port}:
            return check_pid(pid, f'http://{host}:{port}/')
        case _:
            raise ValueError("Invalid ServerInfo format")


_RE_HOST_PORT = re.compile(r'^(?P<host>.+):(?P<port>\d+)$')


def get_server_info(config_dir: Path, /, *,
                    port: int | None = None,
                    pid: int | None = None,
                    host: str | None = None,
                    name: str | None = None,
                    container_id: str | None = None,
                    image: str | None = None,
                    database_path: Path | None = None,) -> list[ServerInfo]:
    """Get server information from servers/*.json"""
    servers_dir = config_dir / 'servers'
    servers_dir.mkdir(parents=True, exist_ok=True)

    # Canonicalize 0 or "" to None
    port = port or None
    pid = pid or None
    host = host or None

    def read_server_info(info_file: Path) -> ServerInfo | None:
        try:
            with open(info_file) as f:
                data = json.load(f)
                db = data.get('database_path')
                if db is not None:
                    data['database_path'] = Path(db)
                return cast(ServerInfo, data)
        except Exception:
            return None

    servers = [
            data
            for info_file in servers_dir.glob('*.json')
            if (data := read_server_info(info_file))
            and (port is None or data.get('port') == port)
            and (pid is None or data.get('pid') == pid)
            and (host is None or data.get('host') == host)
            and (name is None or name in (data.get('docker_container'), data.get('container_id')))
            and (container_id is None or data.get('container_id') == container_id)
            and (image is None or data.get('image') == image)
            and (database_path is None or data.get('database_path') == database_path)
            ]
    if servers or (not any([name, container_id])):
        return servers

    for key, value in (('name', name), ('id', name), ('id', container_id)):
        container_id = subprocess.run(
            ['docker', 'ps', '-q', '-f', f'{key}={value}'],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
        if container_id:
            ports = subprocess.run(
                ['docker', 'port', container_id, str(DEFAULT_PORT)],
                capture_output=True,
                text=True,
            ).stdout.strip()
            portspecs = ports.splitlines()
            if len(portspecs) == 0:
                continue
            portspec = portspecs[0]
            mtch = _RE_HOST_PORT.match(portspec)
            if mtch is None:
                raise RuntimeError(f"Could not parse port specification: {portspec}")
            host = mtch.group('host')
            port_str = mtch.group('port')
            port = int(port_str)
            info = {
                'launched_by': 'docker',
                'port': port or 0,
                'pid': None,
                'host': host or 'localhost',
                'docker_container': name,
                'image': image,
                'container_id': container_id,
                'database_path': database_path,
            }
            svr_info = {
                k: v
                for k, v in info.items()
                if k is not None
            }
            return [cast(ServerInfo, svr_info)]
    return servers


def get_one_server_info(config_dir: Path, /, *,
                        port: int | None = None,
                        pid: int | None = None,
                        host: str | None = None,
                        name: str | None = None,
                        image: str | None = None,
                        database_path: Path | None = None) -> ServerInfo | None:
    """
    Get information for a single matching server.

    Exit if multiple matches are found. This is intended for command-line use,
    where specifying which server to use is important if ambiguity exists.

    Args:
        port (int, optional): Port number to filter by
        pid (int, optional): Process ID to filter by
        host (str, optional): Hostname to filter by
        name (str, optional): Docker container name to filter by
    Returns:
        dict: Server information if exactly one match is found, else exits.
    """
    servers = get_server_info(config_dir,
                              port=port,
                              pid=pid,
                              host=host,
                              name=name,
                              image=image,
                              database_path=database_path)
    if len(servers) > 1:
        click.echo("❌ Multiple servers found, please specify which one to use:")
        for server in servers:
            click.echo(
                f"- PID: {server.get('pid', 'N/A')}, Port: {server.get('port', 'N/A')}, "
                f"Container: {server.get('docker_container', 'N/A')}"
            )
        sys.exit(1)
    return servers[0] if servers else None


def info_file_path(config_dir: Path, /, **info: Any) -> Path:
    """
    Get the path to the server info file based on provided info.

    This does not check if the file exists; it only constructs the expected path.

    Args:
        info: Server information such as docker_container, hostname, port, pid
    Returns:
        Path: Path to the server info file
    """
    servers_dir = config_dir / 'servers'
    servers_dir.mkdir(parents=True, exist_ok=True)

    match info:
        case {'container': container_name} if container_name is not None:
            return servers_dir / f"container_{container_name}.json"
        case {'pid': int() as pid} if pid > 0:
            return servers_dir / f"pid_{pid}.json"
        case {'port': int() as port} if port > 0:
            return servers_dir / f"{port}.json"
        case _:
            raise RuntimeError("Insufficient info to determine server info file path")


def save_server_info(config_dir: Path, /, **info: Any) -> Path:
    """
    Save server information to servers.[filename].json
    """
    info_file = info_file_path(config_dir, **info)
    json_info = {
        k: (v if not isinstance(v, Path) else str(v))
        for k, v in info.items()
        if v is not None
        }

    with info_file.open('w') as f:
        json.dump(json_info, f, indent=2)
    return info_file


def cleanup_server_info(config_dir: Path,
                        **info: Any) -> None:
    """Remove server information file"""
    info_file = info_file_path(config_dir, **info)
    print(f"Cleaning up server info file: {info_file}")
    info_file.unlink(missing_ok=True)


def start_local_server(config: Config, /, *,
                       console: Console,
                       explicit_port: int | None) -> None:
    """Start the server locally as a background process"""

    # Determine port
    port = config['port']
    host = config['host']

    if explicit_port:
        console.print(f"🔒 Port explicitly set to {port} (auto-finding disabled)")
    elif is_port_available(port, host):
        console.print(f"📍 Using available port {port}")
    else:
        console.print(f"⚠️ Port {port} is not available, trying to find a free port...")
        port = find_free_port(port)
        config['port'] = port
        console.print(f"📍 Found available port {port}, updating default")
        config_dir = config['config_dir']
        save_config(config_dir, config)

    console.print(f"🚀 Starting server on {host}:{port}")
    console.print(f"🌐 Web interface: http://{host}:{port}")

    try:
        process = subprocess.Popen(
                        [sys.executable, '-m', 'memgraph', 'run',
                            '--port', str(config['port']),
                            '--host', config['host'],
                            '--config-dir', str(config_dir),
                            '--log-level', config['log_level'],
                            '--database-path', str(config['database_path']),
                            *(['--access-log'] if config['access_log'] else []),
                         ],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        stdin=subprocess.DEVNULL,
                        start_new_session=True,
            )
        console.print(f"✅ Server started (PID: {process.pid})")

    except Exception as e:
        console.print(f"❌ Failed to start server: {e}")
        sys.exit(1)


def start_docker_server(config: Config, /, *,
                        console: Console,
                        explicit_port: int | None,
                        detach: bool = True,
                        ) -> None:
    """Start the server using Docker"""

    container_name = config['container_name']
    docker_image = config['docker_image']
    port = explicit_port or config['port']
    host = config['host']
    log_level = config['log_level']
    access_log = config['access_log']
    config_dir = config['config_dir']
    database_path = config['database_path']

    container_id = subprocess.run(
        ['docker', 'ps', '-q', '--all', '-f', f'name={container_name}'],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()

    if container_id:
        console.print(f"❌ Docker container with name '{container_name}' already exists.")
        console.print(f"Please stop it first with: docker stop {container_name}")
        sys.exit(1)

    if not explicit_port:
        if not is_port_available(port, host):
            port = find_free_port(port)
            config['port'] = port
            save_config(config_dir, config)

    # Build Docker run command
    cmd = [
        'docker',
        'run',
        '--rm',
        '--init',
        '-it' if not detach else '-d',
        '--name', container_name,
        '-p', f'{port}:{DEFAULT_PORT}',
        '-v', f'{config_dir}:/app/.zabob/memgraph',
        docker_image,
        "run",
        '--access-log' if access_log else '--no-access-log',
        '--log-level', log_level,
    ]

    try:
        if detach:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            container_id = result.stdout.strip()
            save_server_info(
                config_dir,
                launched_by='docker',
                port=port,
                docker_container=container_name,
                container_id=container_id,
                docker_image=docker_image,
                log_level=log_level,
                access_log=access_log,
                host=host,
                database_path=database_path,
            )
            console.print(f"✅ Docker container started: {container_name}")
            console.print(f"🌐 Web interface: http://{host}:{port}")
        else:
            info_file = save_server_info(
                config_dir,
                launched_by='docker',
                port=port,
                docker_container=container_name,
                container_id=None,
                docker_image=docker_image,
                log_level=log_level,
                access_log=access_log,
                host=host,
                database_path=database_path,
            )
            try:
                console.print(f"🌐 Web interface: http://{host}:{port}")
                subprocess.run(cmd, check=True)
            finally:
                info_file.unlink(missing_ok=True)

    except subprocess.CalledProcessError as e:
        console.print(f"❌ Failed to start Docker container: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n👋 Stopping container...")
        subprocess.run(['docker', 'stop', str(container_name)], capture_output=True)
        cleanup_server_info(config_dir,
                            port=port,
                            docker_container=container_name,
                            container_id=container_id,
                            docker_image=docker_image,
                            host=host,)


def check_container(container: str) -> ServerStatus:
    try:
        result = subprocess.run(
            ['docker', 'inspect', '-f', '{{.State.Running}}', container],
            capture_output=True,
            text=True,
            check=True,
        )
        is_running = result.stdout.strip() == "true"
        return ServerStatus.RUNNING if is_running else ServerStatus.STOPPED
    except subprocess.CalledProcessError:
        return ServerStatus.GONE


def check_pid(pid: int, base_url: str) -> ServerStatus:
    try:
        process = psutil.Process(pid)
        if process.is_running():
            try:
                response = requests.get(f"{base_url}/health", timeout=3)
                if response.status_code == 200:
                    return ServerStatus.RUNNING
                else:
                    return ServerStatus.ERROR
            except Exception:
                return ServerStatus.NOT_RESPONDING
        else:
            return ServerStatus.NOT_RUNNING
    except psutil.NoSuchProcess:
        return ServerStatus.GONE


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
