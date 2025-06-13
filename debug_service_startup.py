#!/usr/bin/env python3
"""
Debug script to test service startup manually.
"""
import subprocess
import time
import requests
import sys
from pathlib import Path

def test_service_startup():
    """Test if service starts and responds correctly."""
    # Get the service module path
    service_path = Path(__file__).parent / 'memgraph' / 'service.py'
    web_path = Path(__file__).parent / 'memgraph' / 'web'
    log_path = Path(__file__).parent / 'debug_service.log'
    
    print(f"Service path: {service_path}")
    print(f"Web path: {web_path}")
    print(f"Web path exists: {web_path.exists()}")
    print(f"Log path: {log_path}")
    
    if web_path.exists():
        contents = list(web_path.iterdir())
        print(f"Web contents: {[p.name for p in contents]}")
    
    # Start service
    port = 8899  # Use a specific port for debugging
    proc = subprocess.Popen([
        sys.executable, str(service_path),
        "--static-dir", str(web_path),
        "--port", str(port),
        "--log-file", str(log_path)
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    print(f"Started process PID: {proc.pid}")
    
    try:
        # Wait a bit for startup
        for i in range(10):
            time.sleep(1)
            
            # Check if process is still running
            if proc.poll() is not None:
                stdout, stderr = proc.communicate()
                print(f"Process exited with code: {proc.returncode}")
                print(f"Stdout: {stdout}")
                print(f"Stderr: {stderr}")
                break
                
            # Try to connect
            try:
                response = requests.get(f"http://localhost:{port}/health", timeout=1)
                print(f"Attempt {i+1}: Got response {response.status_code}")
                if response.status_code == 200:
                    print("Success! Service is responding")
                    data = response.json()
                    print(f"Health data: {data}")
                    break
            except Exception as e:
                print(f"Attempt {i+1}: Connection failed: {e}")
        else:
            print("All attempts failed")
            
        # Check log file
        if log_path.exists():
            print(f"\nLog file contents:")
            print(log_path.read_text())
        else:
            print("No log file created")
            
    finally:
        # Clean shutdown
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("Process terminated")

if __name__ == "__main__":
    test_service_startup()
