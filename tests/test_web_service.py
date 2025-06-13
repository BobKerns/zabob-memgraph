# test_web_service.py - Web service tests
import pytest
import requests
import time
import subprocess

def test_serves_static_files(web_service_script, web_content):
    """Test that web_service.py serves static files correctly"""
    
    # Start web service using absolute path
    proc = subprocess.Popen([
        "python", str(web_service_script), 
        "--static-dir", str(web_content),
        "--port", "8081"
    ])
    
    try:
        # Give service time to start
        time.sleep(2)
        
        # Test health endpoint
        response = requests.get("http://localhost:8081/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        
        # Test serving index.html at root
        response = requests.get("http://localhost:8081/")
        assert response.status_code == 200
        assert "html" in response.text.lower()
        
        # Test serving static files (if any exist)
        static_files = list(web_content.rglob('*.css')) + list(web_content.rglob('*.js'))
        if static_files:
            # Test first CSS or JS file found
            test_file = static_files[0]
            relative_path = test_file.relative_to(web_content)
            response = requests.get(f"http://localhost:8081/static/{relative_path}")
            assert response.status_code == 200
        
    finally:
        # Clean shutdown
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

def test_web_service_starts(web_service_script, web_content):
    """Test that web service starts without errors"""
    proc = subprocess.Popen([
        "python", str(web_service_script),
        "--static-dir", str(web_content),
        "--port", "8082"
    ])
    
    try:
        time.sleep(1)
        # If process is still running, it started successfully
        assert proc.poll() is None, "Web service exited unexpectedly"
        
    finally:
        proc.terminate()
        proc.wait(timeout=5)
