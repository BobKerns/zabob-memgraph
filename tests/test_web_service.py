# test_web_service.py - Web service tests
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

        # Test health endpoint with retry logic
        log.info("Testing health endpoint")
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = client("health")
                data = json.loads(response)
                assert data["status"] == "healthy"
                # Service can be either "web_service" or "unified_service"
                assert data["service"] in ["web_service", "unified_service"], (
                    f"Unexpected service: {data.get('service')}"
                )
                log.info(f"Health endpoint test passed (service: {data['service']})")
                break
            except (json.JSONDecodeError, KeyError, AssertionError) as e:
                if attempt == max_retries - 1:
                    raise
                log.warning(f"Health check attempt {attempt + 1} failed: {e}, retrying...")
                time.sleep(0.5)


def test_web_service_starts(web_service_py, web_content, port, log, service_log):
    """Test that web service starts without errors"""
    import requests

    log.info(f"Starting test_web_service_starts on port {port}")

    proc = subprocess.Popen([
        "python", str(web_service_py),
        "--static-dir", str(web_content),
        "--port", str(port),
        "--log-file", str(service_log)
    ])

    log.info(f"Started web service process PID: {proc.pid}")

    # Wait for server to be ready (max 10 seconds)
    start_time = time.time()
    server_ready = False
    while time.time() - start_time < 10:
        try:
            response = requests.get(f"http://localhost:{port}/health", timeout=1)
            if response.status_code == 200:
                server_ready = True
                log.info("Server health check passed")
                break
        except (requests.ConnectionError, requests.Timeout):
            time.sleep(0.1)

    if not server_ready:
        proc.terminate()
        log.error("Server failed to start within 10 seconds")
        raise AssertionError(f"Test server failed to start on port {port}")

    try:
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
