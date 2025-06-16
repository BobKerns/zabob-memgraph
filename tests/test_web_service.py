# test_web_service.py - Web service tests
import anyio
import json
import time
import subprocess

def test_serves_static_files(check_static_site,
                             web_service_py,
                             web_content,
                             log,
                             ):
    """Test that web_service.py serves static files correctly"""
    check_static_site(web_service_py)


def test_web_service_health_check(web_service_py,
                                  open_service,
                                  port,
                                  log,
                                  ):
    """Test that web service health endpoint works"""
    log.info(f"Starting test_web_service_health_check on port {port}")

    with open_service(web_service_py, 'web') as client:

        # Test health endpoint
        log.info("Testing health endpoint")
        response = client("health")
        data = json.loads(response)
        assert data["status"] == "healthy"
        assert data["service"] == "web_service"
        log.info("Health endpoint test passed")


def test_web_service_starts(web_service_py, web_content, port, log, service_log):
    """Test that web service starts without errors"""

    log.info(f"Starting test_web_service_starts on port {port}")

    proc = subprocess.Popen([
        "python", str(web_service_py),
        "--static-dir", str(web_content),
        "--port", str(port),
        "--log-file", str(service_log)
    ])

    log.info(f"Started web service process PID: {proc.pid}")

    try:
        time.sleep(0.5)
        # If process is still running, it started successfully
        if proc.poll() is None:
            log.info("Web service process still running - startup successful")
        else:
            log.error(f"Web service process exited with code: {proc.returncode}")
        assert proc.poll() is None, "Web service exited unexpectedly"

    finally:
        log.info("Terminating web service process")
        proc.terminate()
        proc.communicate()
        log.info("Web service process terminated")
