# test_service_integration.py - Phase 2a: Service Integration Tests
import pytest
import requests
import time
import subprocess
import logging
from conftest import wait_for_service

def test_unified_service_starts(package_dir, web_content, get_free_port, test_output_dir, client_logger):
    """Test that unified service starts without errors"""
    port = get_free_port()
    log_file = test_output_dir / 'service.log'  # Standardized name
    service_module = package_dir / 'service.py'
    
    client_logger.info(f"Starting test_unified_service_starts on port {port}")
    client_logger.info(f"Service log: {log_file}")

    proc = subprocess.Popen([
        "python", str(service_module),
        "--static-dir", str(web_content),
        "--port", str(port),
        "--log-file", str(log_file)
    ])
    
    client_logger.info(f"Started service process PID: {proc.pid}")

    try:
        time.sleep(0.5)
        # If process is still running, it started successfully
        if proc.poll() is None:
            client_logger.info("Service process still running - startup successful")
        else:
            client_logger.error(f"Service process exited with code: {proc.returncode}")
        assert proc.poll() is None, "Unified service exited unexpectedly"

    finally:
        client_logger.info("Terminating service process")
        proc.terminate()
        proc.wait(timeout=5)
        client_logger.info("Service process terminated")

def test_unified_service_web_routes(package_dir, web_content, get_free_port, test_output_dir, client_logger):
    """Test that unified service serves web content correctly"""
    port = get_free_port()
    log_file = test_output_dir / 'service.log'  # Standardized name
    service_module = package_dir / 'service.py'
    
    client_logger.info(f"Starting test_unified_service_web_routes on port {port}")
    client_logger.info(f"Service module: {service_module}")
    client_logger.info(f"Web content: {web_content}")
    client_logger.info(f"Service log: {log_file}")

    proc = subprocess.Popen([
        "python", str(service_module),
        "--static-dir", str(web_content),
        "--port", str(port),
        "--log-file", str(log_file)
    ])
    
    client_logger.info(f"Started service process PID: {proc.pid}")

    try:
        # Wait for service with retry pattern
        wait_for_service(f"http://localhost:{port}/health", client_logger=client_logger)

        # Test health endpoint
        client_logger.info("Testing health endpoint")
        response = requests.get(f"http://localhost:{port}/health")
        client_logger.info(f"Health response: {response.status_code}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "unified_service"
        client_logger.info("Health endpoint test passed")

        # Test index serving at root
        client_logger.info("Testing index serving")
        response = requests.get(f"http://localhost:{port}/")
        client_logger.info(f"Index response: {response.status_code}")
        assert response.status_code == 200
        assert "html" in response.text.lower()
        client_logger.info("Index serving test passed")

        # Test static file serving
        static_files = [p for p in web_content.rglob('*') if p.is_file() and p.suffix in ['.css', '.js', '.html']]
        if static_files:
            test_file = static_files[0]
            relative_path = test_file.relative_to(web_content)
            client_logger.info(f"Testing static file: {relative_path}")
            response = requests.get(f"http://localhost:{port}/static/{relative_path}")
            client_logger.info(f"Static file response: {response.status_code}")
            assert response.status_code == 200
            assert len(response.text) > 0
            client_logger.info("Static file test passed")
        else:
            client_logger.warning("No static files found to test")

    finally:
        client_logger.info("Terminating service process")
        proc.terminate()
        proc.wait(timeout=5)
        client_logger.info("Service process terminated")

def test_unified_service_mcp_routes(package_dir, web_content, get_free_port, test_output_dir, client_logger):
    """Test that unified service has MCP endpoints"""
    port = get_free_port()
    log_file = test_output_dir / 'service.log'  # Standardized name
    service_module = package_dir / 'service.py'
    
    client_logger.info(f"Starting test_unified_service_mcp_routes on port {port}")

    proc = subprocess.Popen([
        "python", str(service_module),
        "--static-dir", str(web_content),
        "--port", str(port),
        "--log-file", str(log_file)
    ])
    
    client_logger.info(f"Started service process PID: {proc.pid}")

    try:
        # Wait for service with retry pattern
        wait_for_service(f"http://localhost:{port}/mcp/health", client_logger=client_logger)

        # Test MCP health endpoint (placeholder for now)
        client_logger.info("Testing MCP health endpoint")
        response = requests.get(f"http://localhost:{port}/mcp/health")
        client_logger.info(f"MCP health response: {response.status_code}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "mcp_service"
        client_logger.info("MCP health endpoint test passed")

    finally:
        client_logger.info("Terminating service process")
        proc.terminate()
        proc.wait(timeout=5)
        client_logger.info("Service process terminated")

def test_unified_service_both_routes_same_port(package_dir, web_content, get_free_port, test_output_dir, client_logger):
    """Test that both web and MCP routes work on the same port"""
    port = get_free_port()
    log_file = test_output_dir / 'service.log'  # Standardized name
    service_module = package_dir / 'service.py'
    
    client_logger.info(f"Starting test_unified_service_both_routes_same_port on port {port}")

    proc = subprocess.Popen([
        "python", str(service_module),
        "--static-dir", str(web_content),
        "--port", str(port),
        "--log-file", str(log_file)
    ])
    
    client_logger.info(f"Started service process PID: {proc.pid}")

    try:
        # Wait for service with retry pattern
        wait_for_service(f"http://localhost:{port}/health", client_logger=client_logger)

        # Test web health
        client_logger.info("Testing web health endpoint")
        web_response = requests.get(f"http://localhost:{port}/health")
        client_logger.info(f"Web health response: {web_response.status_code}")
        assert web_response.status_code == 200
        assert web_response.json()["service"] == "unified_service"
        client_logger.info("Web health test passed")

        # Test MCP health
        client_logger.info("Testing MCP health endpoint")
        mcp_response = requests.get(f"http://localhost:{port}/mcp/health")
        client_logger.info(f"MCP health response: {mcp_response.status_code}")
        assert mcp_response.status_code == 200
        assert mcp_response.json()["service"] == "mcp_service"
        client_logger.info("MCP health test passed")

        # Test static content
        client_logger.info("Testing static content")
        static_response = requests.get(f"http://localhost:{port}/")
        client_logger.info(f"Static content response: {static_response.status_code}")
        assert static_response.status_code == 200
        client_logger.info("Static content test passed")

        logging.info(f"All routes working on port {port}")
        client_logger.info("All route tests passed successfully")

    finally:
        client_logger.info("Terminating service process")
        proc.terminate()
        proc.wait(timeout=5)
        client_logger.info("Service process terminated")
