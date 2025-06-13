# conftest.py - Test fixtures
import pytest
import shutil
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
def web_service_script(project_dir):
    """Path to web_service.py script"""
    return project_dir / 'web_service.py'

@pytest.fixture
def web_content(package_dir, tmp_path):
    """Copy actual web content to temporary directory"""
    source_web = package_dir / 'web'
    dest_web = tmp_path / 'web'
    
    if source_web.exists():
        shutil.copytree(source_web, dest_web)
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
    
    return dest_web

@pytest.fixture
def index_html(web_content):
    """Path to index.html in web content"""
    return web_content / 'index.html'

@pytest.fixture
def static_files(web_content):
    """Generator of static files in web content"""
    return list(web_content.rglob('*'))
