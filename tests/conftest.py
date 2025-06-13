# conftest.py - Test fixtures
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

def wait_for_service(url, max_attempts=10, timeout=1.0, client_logger=None):
    """Wait for service to be ready with retry pattern.
    
    Args:
        url: Service URL to check
        max_attempts: Maximum number of retry attempts (increased to 10)
        timeout: Timeout per attempt in seconds (increased to 1.0s)
        client_logger: Logger for client-side logging
        
    Returns:
        requests.Response: Successful response
        
    Raises:
        TimeoutError: If service not ready after max_attempts
    """
    if client_logger:
        client_logger.info(f"Starting service health check: {url} (max {max_attempts} attempts, {timeout}s timeout each)")
    
    last_error = None
    for attempt in range(max_attempts):
        if client_logger:
            client_logger.info(f"Health check attempt {attempt + 1}/{max_attempts}")
            
        try:
            response = requests.get(url, timeout=timeout)
            if client_logger:
                client_logger.info(f"Got HTTP response: {response.status_code}")
                
            if response.status_code == 200:
                if client_logger:
                    client_logger.info(f"Service ready after {attempt + 1} attempts")
                logging.info(f"Service at {url} ready after {attempt + 1} attempts")
                return response
            else:
                last_error = f"HTTP {response.status_code}"
                if client_logger:
                    client_logger.warning(f"Unexpected status code: {response.status_code}")
        except requests.exceptions.ConnectionError as e:
            last_error = f"Connection error: {e}"
            if client_logger:
                client_logger.warning(f"Connection failed: {e}")
        except requests.exceptions.Timeout as e:
            last_error = f"Timeout: {e}"
            if client_logger:
                client_logger.warning(f"Request timeout: {e}")
        except requests.exceptions.RequestException as e:
            last_error = f"Request error: {e}"
            if client_logger:
                client_logger.warning(f"Request error: {e}")
        except Exception as e:
            last_error = f"Unexpected error: {e}"
            if client_logger:
                client_logger.error(f"Unexpected error: {e}")
            
        if attempt < max_attempts - 1:
            if client_logger:
                client_logger.info(f"Waiting 0.2s before next attempt...")
            time.sleep(0.2)  # Slightly longer pause between retries
            
    # Log the final error state
    error_msg = f"Service at {url} not ready after {max_attempts} attempts. Last error: {last_error}"
    if client_logger:
        client_logger.error(error_msg)
    logging.error(error_msg)
    raise TimeoutError(error_msg)

@pytest.fixture
def client_logger(test_output_dir):
    """Create client-side logger for test process"""
    client_log_file = test_output_dir / 'client.log'
    
    # Create a dedicated logger for this test
    logger = logging.getLogger(f"client_{test_output_dir.name}")
    logger.setLevel(logging.INFO)
    
    # Remove any existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Add file handler
    file_handler = logging.FileHandler(client_log_file)
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    logger.info(f"=== Client logging started for test: {test_output_dir.name} ===")
    
    return logger

@pytest.fixture
def test_dir():
    """Directory containing the test files"""
    return Path(__file__).parent

@pytest.fixture
def project_dir(test_dir):
    """Root project directory"""
    return test_dir.parent

@pytest.fixture
def package_dir(project_dir):
    """Package directory (memgraph)"""
    return project_dir / 'memgraph'

@pytest.fixture
def web_service_module(package_dir):
    """Path to web_service.py module within package"""
    return package_dir / 'web_service.py'

@pytest.fixture(scope="session")
def get_free_port():
    """Get available port number"""
    def _get_port():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port
    return _get_port

@pytest.fixture
def test_output_dir(test_dir, request, tmp_path):
    """Create test output directory for artifacts"""
    # Create path: tests/out/<test-file-stem>/<test-name>
    test_file_stem = Path(request.fspath).stem
    test_name = request.node.name
    output_dir = test_dir / 'out' / test_file_stem / test_name

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
def web_content(package_dir, tmp_path):
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
def index_html(web_content):
    """Path to index.html in web content"""
    return web_content / 'index.html'

@pytest.fixture
def static_files(web_content):
    """Generator of static files in web content"""
    return list(web_content.rglob('*'))
