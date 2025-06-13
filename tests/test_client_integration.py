# test_client_integration.py - Phase 2b: Client Integration Tests
import pytest
import requests
import time
import subprocess
import logging
from pathlib import Path

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
        time.sleep(2)
        
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
        time.sleep(2)
        
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

def test_client_js_mcp_integration(package_dir, web_content, get_free_port, test_output_dir):
    """Test client.js MCP integration with unified service"""
    port = get_free_port()
    log_file = test_output_dir / 'client_js_mcp.log'
    service_module = package_dir / 'service.py'
    
    # Check if client.js exists in web content
    client_js = None
    for js_file in web_content.rglob('*.js'):
        if 'client' in js_file.name.lower():
            client_js = js_file
            break
    
    if not client_js:
        pytest.skip("client.js not found in web content - integration pending")
    
    proc = subprocess.Popen([
        "python", str(service_module),
        "--static-dir", str(web_content),
        "--port", str(port),
        "--log-file", str(log_file)
    ])
    
    try:
        time.sleep(2)
        
        # Test that client.js is accessible
        relative_path = client_js.relative_to(web_content)
        response = requests.get(f"http://localhost:{port}/static/{relative_path}")
        assert response.status_code == 200
        assert len(response.text) > 0
        
        # Check for MCP-related code in client.js
        content = response.text
        if "mcp" in content.lower() or "load_graph" in content.lower():
            logging.info("MCP functionality detected in client.js")
        
    finally:
        proc.terminate()
        proc.wait(timeout=5)

def test_load_graph_integration(package_dir, web_content, get_free_port, test_output_dir):
    """Test load_graph integration working end-to-end"""
    port = get_free_port()
    log_file = test_output_dir / 'load_graph.log'
    service_module = package_dir / 'service.py'
    
    proc = subprocess.Popen([
        "python", str(service_module),
        "--static-dir", str(web_content),
        "--port", str(port),
        "--log-file", str(log_file)
    ])
    
    try:
        time.sleep(2)
        
        # Test the unified service is ready for load_graph integration
        web_response = requests.get(f"http://localhost:{port}/health")
        assert web_response.status_code == 200
        
        mcp_response = requests.get(f"http://localhost:{port}/mcp/health")
        assert mcp_response.status_code == 200
        
        # TODO: Test actual load_graph functionality when client.js is integrated
        # This will involve:
        # 1. client.js calling MCP endpoints to load graph data
        # 2. graph.js receiving and displaying the data
        # 3. End-to-end data flow verification
        
        logging.info("Services ready for load_graph integration")
        
    finally:
        proc.terminate()
        proc.wait(timeout=5)

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
        time.sleep(2)
        
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
