# test_client_integration.py - Phase 2b: Client Integration Tests
import pytest
import requests
import time
import subprocess
import logging
from pathlib import Path
from conftest import wait_for_service

def test_web_app_loads_static_content(package_dir, web_content, get_free_port, test_output_dir):
    """Test that web app loads static content from unified service"""
    port = get_free_port()
    log_file = test_output_dir / 'web_app_static.log'
    service_module = package_dir / 'service.py'

    proc = subprocess.Popen([
        "python", str(service_module),
        "--static-dir", str(web_content),
        "--port", str(port),
        "--log-file", str(log_file)
    ])

    try:
        # Wait for service with retry pattern
        wait_for_service(f"http://localhost:{port}/")

        # Test that index.html loads and contains expected web app structure
        response = requests.get(f"http://localhost:{port}/")
        assert response.status_code == 200
        content = response.text.lower()

        # Look for typical web app elements
        assert "html" in content
        # If graph.js or similar is referenced, check for it
        if "graph.js" in content or "script" in content:
            logging.info("Web app structure detected in index.html")

    finally:
        proc.terminate()
        proc.wait(timeout=5)

def test_web_app_connects_to_mcp_service(package_dir, web_content, get_free_port, test_output_dir):
    """Test that web app can connect to MCP service endpoints"""
    port = get_free_port()
    log_file = test_output_dir / 'web_app_mcp.log'
    service_module = package_dir / 'service.py'

    proc = subprocess.Popen([
        "python", str(service_module),
        "--static-dir", str(web_content),
        "--port", str(port),
        "--log-file", str(log_file)
    ])

    try:
        # Wait for service with retry pattern
        wait_for_service(f"http://localhost:{port}/mcp/health")

        # Test MCP health endpoint (placeholder for now)
        response = requests.get(f"http://localhost:{port}/mcp/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "mcp_service"

        # TODO: Test actual MCP protocol endpoints when implemented
        # For now, verify the endpoint structure is accessible

    finally:
        proc.terminate()
        proc.wait(timeout=5)

def test_client_js_mcp_integration(package_dir, web_content, get_free_port, test_output_dir, tmp_path):
    """Test client.js MCP integration via subprocess"""
    port = get_free_port()
    log_file = test_output_dir / 'client_js_mcp.log'
    service_module = package_dir / 'service.py'

    # client.js should be in the copied web content
    client_js = web_content / 'client.js'
    if not client_js.exists():
        pytest.skip("client.js not found in web content")

    # Start the unified service with MCP endpoints
    service_proc = subprocess.Popen([
        "python", str(service_module),
        "--static-dir", str(web_content),
        "--port", str(port),
        "--log-file", str(log_file)
    ])

    try:
        # Wait for service with retry pattern
        wait_for_service(f"http://localhost:{port}/health")

        # Test client.js via subprocess with MCP server URL
        # Run from tmp_path directory where node_modules is available
        mcp_url = f"http://localhost:{port}/mcp"
        client_proc = subprocess.Popen([
            "node", str(client_js), mcp_url
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=str(tmp_path))

        stdout, stderr = client_proc.communicate(timeout=10)

        # Log the output for debugging
        logging.info(f"client.js stdout: {stdout}")
        if stderr:
            logging.warning(f"client.js stderr: {stderr}")

        # Verify client.js executed without critical errors
        assert client_proc.returncode == 0, f"client.js failed with code {client_proc.returncode}"

        # Check for expected MCP tool call output
        if "Tool call result:" in stdout:
            logging.info("MCP tool calls detected in client.js output")

    except subprocess.TimeoutExpired:
        client_proc.kill()
        pytest.fail("client.js subprocess timed out")

    finally:
        service_proc.terminate()
        service_proc.wait(timeout=5)

def test_mcp_data_format_validation(package_dir, web_content, get_free_port, test_output_dir, tmp_path):
    """Test that MCP client returns data in expected format for visualization"""
    pytest.skip("Multi-process integration test needs rethinking - browser client.js + owner stdio process + ongoing interaction")
    # TODO: Implement proper multi-process test:
    # - Browser client (client.js) making HTTP requests to web service  
    # - Separate owner process using stdio for direct MCP communication
    # - Multiple concurrent processes with ongoing interaction
    # - Test orchestration of web + HTTP + stdio services simultaneously

def test_full_web_app_stack(package_dir, web_content, get_free_port, test_output_dir):
    """Test complete web app stack: static + MCP + client integration"""
    port = get_free_port()
    log_file = test_output_dir / 'full_stack.log'
    service_module = package_dir / 'service.py'

    proc = subprocess.Popen([
        "python", str(service_module),
        "--static-dir", str(web_content),
        "--port", str(port),
        "--log-file", str(log_file)
    ])

    try:
        # Wait for service with retry pattern
        wait_for_service(f"http://localhost:{port}/health")

        # Test all components working together

        # 1. Static content loads
        index_response = requests.get(f"http://localhost:{port}/")
        assert index_response.status_code == 200

        # 2. Web service health
        web_health = requests.get(f"http://localhost:{port}/health")
        assert web_health.status_code == 200
        assert web_health.json()["service"] == "unified_service"

        # 3. MCP service health
        mcp_health = requests.get(f"http://localhost:{port}/mcp/health")
        assert mcp_health.status_code == 200
        assert mcp_health.json()["service"] == "mcp_service"

        # 4. All on same port
        logging.info(f"Full stack operational on single port {port}")

        # TODO: Add client-side JavaScript execution test when integration complete

    finally:
        proc.terminate()
        proc.wait(timeout=5)
