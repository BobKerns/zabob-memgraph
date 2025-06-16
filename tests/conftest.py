# conftest.py - Test fixtures

from contextlib import contextmanager
import json
import subprocess
from collections.abc import Generator
from typing import Any, Literal, Protocol, cast
from psutil.tests import sh
import pytest
import shutil
import socket
import logging
import os
import stat
import time
import requests
from pathlib import Path

def remove_readonly(func, path, _):
    """Clear the readonly bit and reattempt the removal"""
    os.chmod(path, stat.S_IWRITE)
    func(path)

@pytest.fixture
def wait_for_service(log):
    """Wait for service to be ready with retry pattern.'''
    """
    def wait_for_service(max_attempts=10, timeout=1.0):
        """
        Wait for a service to be ready by polling its health endpoint.
        Args:
            max_attempts: Maximum number of retry attempts (increased to 10)
            timeout: Timeout per attempt in seconds (increased to 1.0s)

        Returns:
            requests.Response: Successful response

        Raises:
            TimeoutError: If service not ready after max_attempts
        """
        url = "http://localhost:8000/health"
        log.info(f"Starting service health check: {url} (max {max_attempts} attempts, {timeout}s timeout each)")
        last_error = None
        for attempt in range(max_attempts):
            log.info(f"Health check attempt {attempt + 1}/{max_attempts}")

            try:
                response = requests.get(url, timeout=timeout)
                log.info(f"Got HTTP response: {response.status_code}")

                if response.status_code == 200:
                    logging.info(f"Service at {url} ready after {attempt + 1} attempts")
                    return response
                else:
                    last_error = f"HTTP {response.status_code}"
                    log.warning(f"Unexpected status code: {response.status_code}")
            except requests.exceptions.ConnectionError as e:
                last_error = f"Connection error: {e}"
                log.warning(f"Connection failed: ~{e}")
            except requests.exceptions.Timeout as e:
                last_error = f"Timeout: {e}"
                log.warning(f"Request timeout: {e}")
            except requests.exceptions.RequestException as e:
                last_error = f"Request error: {e}"
                log.warning(f"Request error: {e}")
            except Exception as e:
                last_error = f"Unexpected error: {e}"
                log.error(f"Unexpected error: {e}")

            if attempt < max_attempts - 1:
                log.info(f"Waiting 0.2s before next attempt...")
                time.sleep(0.2)  # Slightly longer pause between retries

        # Log the final error state
        error_msg = f"Service at {url} not ready after {max_attempts} attempts. Last error: {last_error}"
        log.error(error_msg)
        raise TimeoutError(error_msg)
    return wait_for_service

@pytest.fixture
def log(request: pytest.FixtureRequest, client_log):
    """Create client-side logger for test process"""
    # Create a dedicated logger for this test
    logger = logging.getLogger(f"client")
    logger.setLevel(logging.INFO)

    # Remove any existing handlers to avoid duplicates
    logger.handlers.clear()

    # Add file handler
    file_handler = logging.FileHandler(client_log)
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.info(f"=== Client logging started for test: {request.node.name} ===")

    return logger

@pytest.fixture
def service_log(test_output_dir: Path) -> Path:
    """Path to service log file"""
    return test_output_dir / 'service.log'

@pytest.fixture
def client_log(test_output_dir: Path) -> Path:
    """Path to client log file"""
    return test_output_dir / 'client.log'

@pytest.fixture
def test_dir() -> Path:
    """Directory containing the test files"""
    return Path(__file__).parent

@pytest.fixture
def project_dir(test_dir: Path) -> Path:
    """Root project directory"""
    return test_dir.parent

@pytest.fixture
def package_dir(project_dir: Path) -> Path:
    """Package directory (memgraph)"""
    return project_dir / 'memgraph'

@pytest.fixture
def web_service_py(package_dir: Path) -> Path:
    """Path to web_service.py module within package"""
    return package_dir / 'web_service.py'

@pytest.fixture
def http_service_py(package_dir: Path) -> Path:
    """Path to MCP via streaming HTTP http_service.py module within package"""
    return package_dir / 'web_service.py'

@pytest.fixture
def stdio_service_py(package_dir: Path) -> Path:
    """Path to MCP via stdio stdio_service.py module within package"""
    return package_dir / 'stdio_service.py'
@pytest.fixture
def service_py(package_dir: Path) -> Path:
    """Path to unified service.py module within package"""
    return package_dir / 'service.py'

@pytest.fixture(scope="session")
def port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port

@pytest.fixture
def test_output_dir(test_dir: Path, request, tmp_path: Path) -> Generator[Path, None, None]:
    """Create test output directory for artifacts"""
    # Create path: tests/out/<test-file-stem>/<test-name>
    test_file_stem = Path(request.fspath).stem
    test_name: str = cast(str, request.node.name)
    output_dir: Path = test_dir / 'out' / test_file_stem / test_name

    # Clean up old test artifacts
    if output_dir.exists():
        shutil.rmtree(output_dir, onexc=remove_readonly)

    output_dir.mkdir(parents=True, exist_ok=True)

    yield output_dir

    # Copy artifacts from tmp_path if available (suppress errors after warning)
    try:
        if tmp_path.exists():
            dest_tmp = output_dir / 'tmp_artifacts'
            shutil.copytree(tmp_path, dest_tmp)
    except Exception as e:
        logging.warning(f"Failed to copy test artifacts: {e}")

@pytest.fixture
def web_content(package_dir: Path, tmp_path: Path) -> Path:
    """Copy actual web content to temporary directory"""
    source_web = package_dir / 'web'
    dest_web = tmp_path / 'web'

    if not source_web.exists():
        pytest.fail(f"Required web content directory not found: {source_web}")

    shutil.copytree(source_web, dest_web)

    # Copy Node.js dependencies for client.js subprocess testing
    project_root = package_dir.parent
    package_json = project_root / 'package.json'
    node_modules = project_root / 'node_modules'

    shutil.copy2(package_json, tmp_path / 'package.json')

    if node_modules.exists():
        shutil.copytree(node_modules, tmp_path / 'node_modules')
    else:
        logging.warning(f"node_modules not found at {node_modules} - Node.js tests may fail")

    return dest_web

@pytest.fixture
def index_html(web_content: Path) -> Path:
    """Path to index.html in web content"""
    return web_content / 'index.html'

@pytest.fixture
def client_js(web_content: Path) -> Path:
    """Path to client.js in web content"""
    return web_content / 'client.js'

@pytest.fixture
def static_files(web_content: Path) -> list[Path]:
    """Generator of static files in web content"""
    return list(web_content.rglob('*'))

type Transport = Literal['stdio', 'http', 'web']
'''
Value indicating transport mechanism for MCP service
- 'stdio': Use standard input/output streams
- 'http': Use streaming HTTP requests
- 'web': Regular web HTP requests
'''

class TestClient(Protocol):
    '''
    Protocol for js_client fixture

    Args:
        url: URL to connect to (default http://localhost:{port}/)
    Returns:
        str: Output from client.js
    '''
    def __call__(self, url: str) -> str: ...

_node_js_path: Path|None = None

@pytest.fixture
def node_js() -> Path:
    """Locate Node.js executable"""
    global _node_js_path
    if _node_js_path is None:
        loc = os.getenv("NODEJS_PATH") or shutil.which("node")
        if loc is None:
            pytest.fail("Node.js executable not found in PATH - required for client.js tests")
        _node_js_path = Path(loc)
    return _node_js_path

class ServiceOpener(Protocol):
    @contextmanager
    def __call__(self, service: Path, transport: Transport) -> Generator[TestClient, None, None]: ...

@contextmanager
def open_subprocess(cmd: list[Any], log: logging.Logger)  -> Generator[subprocess.Popen[str], Any, None]:
    cmd = [str(c) for c in cmd]
    log.info(f"Starting subprocess: {' '.join(cmd)}")
    proc = subprocess.Popen(cmd, text=True)
    log.info(f"Started subprocess PID: {proc.pid}")
    try:
        yield proc
    finally:
        log.info(f"Terminating subprocess PID: {proc.pid}")
        proc.terminate()


@pytest.fixture
def open_service(request,
                 web_content: Path,
                 port,
                 log: logging.Logger,
                 node_js: Path,
                 client_js: Path,
                 service_log) -> ServiceOpener:
    """Start the a service as a subprocess and ensure cleanup"""
    test_name = request.node.name

    @contextmanager
    def _service(service: Path, transport: Transport)-> Generator[TestClient, None, None]:
        def _client(url: str) -> str:
            match transport:
                case 'http'|'web':
                    url = f'http://localhost:{port}/{url}'
            log.info(f"Starting client subprocess for {url}")

            cmd = [node_js, client_js,
                '--service-path', str(client_js),
                '--transport', 'http',
                "--url", url,
                ]
            with open_subprocess(cmd, log) as proc:
                proc.wait()
                stderr = proc.stderr
                if stderr is not None:
                    while l := stderr.readline():
                        log.info(f"client.js: {l}")
                stdout = proc.stdout
                if stdout is None:
                    return ''
                else:
                    return stdout.read()

        def _web_client(url: str) -> str:
            match transport:
                case 'http'|'web':
                    url = f'http://localhost:{port}/{url}'
            log.info(f"Starting web client request for {url}")
            try:
                response = requests.get(url, timeout=1.0)
                log.info(f"Got HTTP response: {response.status_code}")
                log.info(f"Response text (truncated): {response.text[:100]}...")
                if response.status_code != 200:
                    log.error(f"Web client error: {response.text}")
                return response.text
            except Exception as e:
                log.error(f"Web client request error: {e}")
                raise e

        match transport:
            case 'stdio':
                yield _client
            case 'http':
                proc = subprocess.Popen([
                    "python", str(service),
                    "--static-dir", str(web_content),
                    "--port", str(port),
                    "--log-file", str(service_log)
                ],
                                            text=True,)

                log.info(f"Started service process PID: {proc.pid}")
                try:
                    time.sleep(0.5)  # Give server a moment to start
                    yield _client
                finally:
                    log.info(f"Terminating service process for {test_name}")
                    proc.terminate()

            case 'web':
                proc = subprocess.Popen([
                    "python3", str(service),
                    "--static-dir", str(web_content),
                    "--port", str(port),
                    "--log-file", str(service_log)
                ],
                                            text=True,)

                log.info(f"Started service process PID: {proc.pid}")
                try:
                    time.sleep(0.5)
                    yield _web_client
                finally:
                    log.info(f"Terminating service process for {test_name}")
                    proc.terminate()
    return _service

@pytest.fixture
def check_static_site(open_service, log, web_content):
    """Check that static site files are present"""
    def _check(server: Path):
        with open_service(server, 'web') as client:

            # Wait for service with retry pattern
            log.info("Testing health endpoint")
            response = client("health")
            response_json = json.loads(response)
            assert response_json["status"] == "healthy"
            log.info("Health check passed")

            # Test serving index.html at root
            log.info("Testing index serving")
            response = client('')
            assert "html" in response.lower()
            log.info("Index serving passed")

            # Test serving actual static files via /static/ path
            static_files = [p for p in web_content.rglob('*') if p.is_file() and p.suffix in ['.css', '.js', '.html']]
            if static_files:
                # Test first static file found
                test_file = static_files[0]
                relative_path = test_file.relative_to(web_content)
                static_url = str(relative_path).replace('\\', '/')
                log.info(f"Testing static file: {static_url}")

                response = client(static_url)
                assert len(response) > 0
                log.info(f"Static file serving passed for {static_url}")
            else:
                log.info("No static files found to test")
    return _check
