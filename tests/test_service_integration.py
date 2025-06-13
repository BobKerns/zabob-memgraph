# test_service_integration.py - Phase 2a: Service Integration Tests
import pytest
import requests
import time
import subprocess
import logging

def test_unified_service_starts(package_dir, web_content, get_free_port, test_output_dir):
    """Test that unified service starts without errors"""
    port = get_free_port()
    log_file = test_output_dir / 'unified_service.log'
    service_module = package_dir / 'service.py'
    
    proc = subprocess.Popen([
        "python", str(service_module),
        "--static-dir", str(web_content),
        "--port", str(port),
        "--log-file", str(log_file)
    ])
    
    try:
        time.sleep(2)
        # If process is still running, it started successfully
        assert proc.poll() is None, "Unified service exited unexpectedly"
        
    finally:
        proc.terminate()
        proc.wait(timeout=5)

def test_unified_service_web_routes(package_dir, web_content, get_free_port, test_output_dir):
    """Test that unified service serves web content correctly"""
    port = get_free_port()
    log_file = test_output_dir / 'web_routes.log'
    service_module = package_dir / 'service.py'
    
    proc = subprocess.Popen([
        "python", str(service_module),
        "--static-dir", str(web_content),
        "--port", str(port),
        "--log-file", str(log_file)
    ])
    
    try:
        time.sleep(2)
        
        # Test health endpoint
        response = requests.get(f"http://localhost:{port}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "unified_service"
        
        # Test index serving at root
        response = requests.get(f"http://localhost:{port}/")
        assert response.status_code == 200
        assert "html" in response.text.lower()
        
        # Test static file serving
        static_files = [p for p in web_content.rglob('*') if p.is_file() and p.suffix in ['.css', '.js', '.html']]
        if static_files:
            test_file = static_files[0]
            relative_path = test_file.relative_to(web_content)
            response = requests.get(f"http://localhost:{port}/static/{relative_path}")
            assert response.status_code == 200
            assert len(response.text) > 0
        
    finally:
        proc.terminate()
        proc.wait(timeout=5)

def test_unified_service_mcp_routes(package_dir, web_content, get_free_port, test_output_dir):
    """Test that unified service has MCP endpoints"""
    port = get_free_port()
    log_file = test_output_dir / 'mcp_routes.log'
    service_module = package_dir / 'service.py'
    
    proc = subprocess.Popen([
        "python", str(service_module),
        "--static-dir", str(web_content),
        "--port", str(port),
        "--log-file", str(log_file)
    ])
    
    try:
        time.sleep(2)
        
        # Test MCP health endpoint (placeholder for now)
        response = requests.get(f"http://localhost:{port}/mcp/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "mcp_service"
        
    finally:
        proc.terminate()
        proc.wait(timeout=5)

def test_unified_service_both_routes_same_port(package_dir, web_content, get_free_port, test_output_dir):
    """Test that both web and MCP routes work on the same port"""
    port = get_free_port()
    log_file = test_output_dir / 'both_routes.log'
    service_module = package_dir / 'service.py'
    
    proc = subprocess.Popen([
        "python", str(service_module),
        "--static-dir", str(web_content),
        "--port", str(port),
        "--log-file", str(log_file)
    ])
    
    try:
        time.sleep(2)
        
        # Test web health
        web_response = requests.get(f"http://localhost:{port}/health")
        assert web_response.status_code == 200
        assert web_response.json()["service"] == "unified_service"
        
        # Test MCP health  
        mcp_response = requests.get(f"http://localhost:{port}/mcp/health")
        assert mcp_response.status_code == 200
        assert mcp_response.json()["service"] == "mcp_service"
        
        # Test static content
        static_response = requests.get(f"http://localhost:{port}/")
        assert static_response.status_code == 200
        
        logging.info(f"All routes working on port {port}")
        
    finally:
        proc.terminate()
        proc.wait(timeout=5)
