# conftest.py - Test fixtures

from contextlib import contextmanager
import json
import subprocess
from collections.abc import Generator
from typing import Any, Literal, Protocol, cast, overload
import pytest
import shutil
import socket
import logging
import os
import stat
import time
import requests
import sys
from pathlib import Path


def remove_readonly(func, path, _):
    """Clear the readonly bit and reattempt the removal"""
    os.chmod(path, stat.S_IWRITE)
    func(path)


@pytest.fixture
def log(request: pytest.FixtureRequest, client_log):
    """Create client-side logger for test process"""
    # Create a dedicated logger for this test
    logger = logging.getLogger("client")
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
    """Find a free port for testing"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


@pytest.fixture(scope="session")
def test_server(port, tmp_path_factory):
    """Start a test server with temporary database on a free port"""
    # Create temporary directory for test database
    temp_dir = tmp_path_factory.mktemp("test_db")
    db_path = temp_dir / "test_knowledge_graph.db"

    # Set environment variables for test server
    env = os.environ.copy()
    env["MEMGRAPH_PORT"] = str(port)
    env["MEMGRAPH_HOST"] = "localhost"
    env["MEMGRAPH_DATABASE_PATH"] = str(db_path)
    env["MEMGRAPH_LOG_LEVEL"] = "WARNING"  # Reduce log noise in tests

    # Start the server using the CLI's run command
    project_dir = Path(__file__).parent.parent

    # Start the server process
    process = subprocess.Popen(
        [sys.executable, "-m", "memgraph", "run", "--port", str(port)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(project_dir)
    )

    # Wait for server to be ready (max 30 seconds with retries for CI)
    start_time = time.time()
    server_ready = False
    base_url = f"http://localhost:{port}"

    while time.time() - start_time < 30:
        try:
            response = requests.get(f"{base_url}/health", timeout=3)
            if response.status_code == 200:
                server_ready = True
                # Extra wait to ensure server is fully ready (longer for CI)
                time.sleep(2.0)
                break
        except (requests.ConnectionError, requests.Timeout):
            time.sleep(0.5)

    if not server_ready:
        process.terminate()
        stdout, stderr = process.communicate(timeout=5)
        pytest.fail(f"Test server failed to start on port {port}\nStdout: {stdout}\nStderr: {stderr}")

    # Additional stabilization delay after health check passes
    time.sleep(1.0)

    yield {"port": port, "base_url": base_url, "db_path": db_path}

    # Cleanup: terminate server
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


@pytest.fixture(scope="session")
def populated_test_server(test_server):
    """Test server with sample data populated

    Note: Populates database using sync wrapper to avoid event loop conflicts.
    """
    from memgraph.sqlite_backend import SQLiteKnowledgeGraphDB
    import asyncio
    import threading

    # Get database path from test_server fixture
    db_path = test_server["db_path"]

    # Create database instance
    db = SQLiteKnowledgeGraphDB(db_path=str(db_path))

    # Create sample data in a separate thread to avoid event loop conflicts
    def populate_data():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Create sample entities
            loop.run_until_complete(db.create_entities([
                {
                    "name": "Python",
                    "entityType": "Language",
                    "observations": ["High-level programming language", "Dynamic typing"]
                },
                {
                    "name": "FastAPI",
                    "entityType": "Framework",
                    "observations": ["Modern web framework", "Built on Starlette"]
                },
                {
                    "name": "SQLite",
                    "entityType": "Database",
                    "observations": ["Embedded database", "ACID compliant"]
                }
            ]))

            # Create sample relations
            loop.run_until_complete(db.create_relations([
                {
                    "from_entity": "FastAPI",
                    "to": "Python",
                    "relationType": "written_in"
                },
                {
                    "from_entity": "FastAPI",
                    "to": "SQLite",
                    "relationType": "supports"
                }
            ]))
        finally:
            loop.close()

    # Run in a separate thread to avoid pytest-asyncio conflicts
    thread = threading.Thread(target=populate_data)
    thread.start()
    thread.join()

    return test_server


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

    # Note: node_modules not needed for web service tests.
    # The web service serves static files (HTML/CSS/JS) that run in the browser,
    # not Node.js server-side code.

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


type Transport = Literal['stdio', 'http', 'web', 'both']
'''
Value indicating transport mechanism for MCP service
- 'stdio': Use standard input/output streams
- 'http': Use streaming HTTP requests
- 'web': Regular web HTP requests
- 'both': Both web and MCP clients available
'''


class TestClient(Protocol):
    '''
    Protocol for single client fixture

    Args:
        url: URL to connect to (default http://localhost:{port}/)
    Returns:
        str: Output from client
    '''
    def __call__(self, url: str) -> str: ...


_node_js_path: Path | None = None


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
    @overload
    @contextmanager
    def __call__(self, service: Path, transport: Literal['both']
                 ) -> Generator[tuple[TestClient, TestClient], None, None]: ...

    @overload
    @contextmanager
    def __call__(self, service: Path, transport: Literal['stdio', 'http', 'web']
                 ) -> Generator[TestClient, None, None]: ...

    @contextmanager
    def __call__(self, service: Path, transport: Transport
                 ) -> Generator[TestClient | tuple[TestClient, TestClient], None, None]: ...


@contextmanager
def open_subprocess(cmd: list[Any], log: logging.Logger) -> Generator[subprocess.Popen[str], Any, None]:
    cmd = [str(c) for c in cmd]
    log.info(f"Starting subprocess: {' '.join(cmd)}")
    proc = subprocess.Popen(cmd, text=True)
    log.info(f"Started subprocess PID: {proc.pid}")
    try:
        yield proc
    finally:
        log.info(f"Terminating subprocess PID: {proc.pid}")
        proc.terminate()
        # proc.communicate()


@pytest.fixture
def open_service(request,
                 web_content: Path,
                 port,
                 log: logging.Logger,
                 node_js: Path,
                 client_js: Path,
                 service_log) -> ServiceOpener:
    """
    Start the a service as a subprocess and ensure cleanup

    Once a service is started, yield a client function to interact with it.
    """
    test_name = request.node.name

    @overload
    @contextmanager
    def _service(service: Path, transport: Literal['both']) -> Generator[tuple[TestClient, TestClient], None, None]: ...

    @overload
    @contextmanager
    def _service(service: Path, transport: Literal['stdio', 'http', 'web']) -> Generator[TestClient, None, None]: ...

    @contextmanager
    def _service(service: Path, transport: Transport
                 ) -> Generator[TestClient | tuple[TestClient, TestClient], None, None]:
        '''
        Service context manager.

        Args:
            service: Path to service script to run
            transport: Transport mechanism to use ('stdio', 'http', 'web', 'both')
        Yields:
            TestClient | tuple[TestClient, TestClient]: Function(s) to interact with the service
        '''
        def _mcp_client(url: str) -> str:
            '''
            Client function to interact with service via MCP over stdio or HTTP.
            Args:
                url: URL path to request (e.g. 'mcp/health')
            Returns:
                str: Response text from client.js subprocess
            '''
            match transport:
                case 'stdio':
                    pass
                case _:
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
                    while line := stderr.readline():
                        log.info(f"client.js: {line}")
                stdout = proc.stdout
                if stdout is None:
                    return ''
                else:
                    return stdout.read()

        def _web_client(url: str) -> str:
            '''
            Client function to interact with service via regular web HTTP.
            Args:
                url: URL path to request (e.g. 'health', 'index.html')
            Returns:
                str: Response text from HTTP GET request
            '''
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
                yield _mcp_client
            case 'http':
                proc = subprocess.Popen([
                    "python", str(service),
                    "--static-dir", str(web_content),
                    "--port", str(port),
                    "--log-file", str(service_log)
                ],
                                            text=True,)

                log.info(f"Started service process PID: {proc.pid}")

                # Wait for server to be ready (max 10 seconds)
                start_time = time.time()
                server_ready = False
                while time.time() - start_time < 10:
                    try:
                        response = requests.get(f"http://localhost:{port}/health", timeout=1)
                        if response.status_code == 200:
                            server_ready = True
                            log.info("Server health check passed")
                            break
                    except (requests.ConnectionError, requests.Timeout):
                        time.sleep(0.1)

                if not server_ready:
                    proc.terminate()
                    log.error("Server failed to start within 10 seconds")
                    pytest.fail(f"Test server failed to start on port {port}")

                try:
                    yield _mcp_client
                finally:
                    log.info(f"Terminating service process for {test_name}")
                    proc.terminate()
                    proc.wait()
                    # proc.communicate()

            case 'web':
                proc = subprocess.Popen([
                    "python3", str(service),
                    "--static-dir", str(web_content),
                    "--port", str(port),
                    "--log-file", str(service_log)
                ],
                                            text=True,)

                log.info(f"Started service process PID: {proc.pid}")

                # Wait for server to be ready (max 10 seconds)
                start_time = time.time()
                server_ready = False
                while time.time() - start_time < 10:
                    try:
                        response = requests.get(f"http://localhost:{port}/health", timeout=1)
                        if response.status_code == 200:
                            server_ready = True
                            log.info("Server health check passed")
                            break
                    except (requests.ConnectionError, requests.Timeout):
                        time.sleep(0.1)

                if not server_ready:
                    proc.terminate()
                    log.error("Server failed to start within 10 seconds")
                    pytest.fail(f"Test server failed to start on port {port}")

                try:
                    yield _web_client
                finally:
                    log.info(f"Terminating service process for {test_name}")
                    proc.terminate()
                    # proc.communicate()

            case 'both':
                # Start unified service and provide both web and MCP clients
                proc = subprocess.Popen([
                    "python", str(service),
                    "--static-dir", str(web_content),
                    "--port", str(port),
                    "--log-file", str(service_log)
                ],
                                            text=True,)

                log.info(f"Started service process PID: {proc.pid}")

                # Wait for server to be ready (max 10 seconds)
                start_time = time.time()
                server_ready = False
                while time.time() - start_time < 10:
                    try:
                        response = requests.get(f"http://localhost:{port}/health", timeout=1)
                        if response.status_code == 200:
                            server_ready = True
                            log.info("Server health check passed")
                            break
                    except (requests.ConnectionError, requests.Timeout):
                        time.sleep(0.1)

                if not server_ready:
                    proc.terminate()
                    log.error("Server failed to start within 10 seconds")
                    pytest.fail(f"Test server failed to start on port {port}")

                log.info(f"Started unified service process PID: {proc.pid}")
                try:
                    time.sleep(0.5)  # Give server a moment to start

                    # Yield tuple of (mcp_client, web_client) for unpacking
                    yield (_mcp_client, _web_client)
                finally:
                    log.info(f"Terminating unified service process for {test_name}")
                    proc.terminate()
                    proc.wait()
                    # proc.communicate()
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
