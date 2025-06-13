# conftest.py - Test fixtures
import pytest
import shutil
import socket
import logging
from pathlib import Path

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
def test_output_dir(test_dir, request):
    """Create test output directory for artifacts"""
    # Create path: tests/out/<test-file-stem>/<test-name>
    test_file_stem = Path(request.fspath).stem
    test_name = request.node.name
    output_dir = test_dir / 'out' / test_file_stem / test_name
    
    # Clean up old test artifacts
    if output_dir.exists():
        shutil.rmtree(output_dir, ignore_errors=True)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    yield output_dir
    
    # Copy artifacts from tmp_path if available
    if hasattr(request, 'tmp_path_factory'):
        try:
            tmp_path = request.getfixturevalue('tmp_path')
            if tmp_path.exists():
                dest_tmp = output_dir / 'tmp_artifacts'
                shutil.copytree(tmp_path, dest_tmp, ignore_errors=True)
        except Exception as e:
            logging.warning(f"Failed to copy test artifacts: {e}")

@pytest.fixture
def web_content(package_dir, tmp_path):
    """Copy actual web content to temporary directory"""
    source_web = package_dir / 'web'
    dest_web = tmp_path / 'web'
    
    logging.info(f"Looking for web content at: {str(source_web)}")
    logging.info(f"Source web exists: {source_web.exists()}")
    if source_web.exists():
        contents = [str(p) for p in source_web.iterdir()]
        logging.info(f"Source web contents: {' | '.join(contents)}")
    
    if source_web.exists():
        shutil.copytree(source_web, dest_web)
        logging.info(f"Copied web content to: {str(dest_web)}")
        dest_contents = [str(p.name) for p in dest_web.iterdir()]
        logging.info(f"Dest web contents: {' | '.join(dest_contents)}")
    else:
        # Fallback: create minimal content if web directory doesn't exist
        dest_web.mkdir()
        (dest_web / 'index.html').write_text("""
<!DOCTYPE html>
<html>
<head><title>Test Page</title></head>
<body><h1>Knowledge Graph</h1></body>
</html>
        """.strip())
        logging.info(f"Created fallback content at: {str(dest_web)}")
    
    return dest_web

@pytest.fixture
def index_html(web_content):
    """Path to index.html in web content"""
    return web_content / 'index.html'

@pytest.fixture
def static_files(web_content):
    """Generator of static files in web content"""
    return list(web_content.rglob('*'))
