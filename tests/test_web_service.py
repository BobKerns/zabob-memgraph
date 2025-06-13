# test_web_service.py - Web service tests
import pytest
import requests
import time
import subprocess
import logging

def test_serves_static_files(web_service_module, web_content, get_free_port, test_output_dir):
    """Test that web_service.py serves static files correctly"""
    port = get_free_port()
    log_file = test_output_dir / 'web_service.log'
    
    logging.info(f"Starting web service with static dir: {str(web_content)}")
    logging.info(f"Web content exists: {web_content.exists()}")
    if web_content.exists():
        files = [str(p.relative_to(web_content)) for p in web_content.rglob('*') if p.is_file()]
        logging.info(f"Web content files: {' | '.join(files)}")
    
    # Start web service as module
    proc = subprocess.Popen([
        "python", str(web_service_module), 
        "--static-dir", str(web_content),
        "--port", str(port),
        "--log-file", str(log_file)
    ])
    
    try:
        # Give service time to start
        time.sleep(2)
        
        # Test health endpoint first
        response = requests.get(f"http://localhost:{port}/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        logging.info("Health check passed")
        
        # Test serving index.html at root
        response = requests.get(f"http://localhost:{port}/")
        logging.info(f"Root request status: {response.status_code}")
        if response.status_code != 200:
            logging.error(f"Root request error: {response.text}")
        assert response.status_code == 200
        assert "html" in response.text.lower()
        logging.info("Index serving passed")
        
        # Test serving actual static files via /static/ path
        static_files = [p for p in web_content.rglob('*') if p.is_file() and p.suffix in ['.css', '.js', '.html']]
        if static_files:
            # Test first static file found
            test_file = static_files[0]
            relative_path = test_file.relative_to(web_content)
            static_url = f"http://localhost:{port}/static/{relative_path}"
            logging.info(f"Testing static file: {static_url}")
            
            response = requests.get(static_url)
            logging.info(f"Static file status: {response.status_code}")
            if response.status_code != 200:
                logging.error(f"Static file error: {response.text}")
            assert response.status_code == 200
            assert len(response.text) > 0
            logging.info(f"Static file serving passed for {relative_path}")
        else:
            logging.info("No static files found to test")
        
    finally:
        # Clean shutdown
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

def test_web_service_health_check(web_service_module, web_content, get_free_port, test_output_dir):
    """Test that web service health endpoint works"""
    port = get_free_port()
    log_file = test_output_dir / 'health_service.log'
    
    proc = subprocess.Popen([
        "python", str(web_service_module),
        "--static-dir", str(web_content),
        "--port", str(port),
        "--log-file", str(log_file)
    ])
    
    try:
        time.sleep(1)
        # Test health endpoint
        response = requests.get(f"http://localhost:{port}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "web_service"
        
    finally:
        proc.terminate()
        proc.wait(timeout=5)

def test_web_service_starts(web_service_module, web_content, get_free_port, test_output_dir):
    """Test that web service starts without errors"""
    port = get_free_port()
    log_file = test_output_dir / 'startup_service.log'
    
    proc = subprocess.Popen([
        "python", str(web_service_module),
        "--static-dir", str(web_content),
        "--port", str(port),
        "--log-file", str(log_file)
    ])
    
    try:
        time.sleep(1)
        # If process is still running, it started successfully
        assert proc.poll() is None, "Web service exited unexpectedly"
        
    finally:
        proc.terminate()
        proc.wait(timeout=5)
