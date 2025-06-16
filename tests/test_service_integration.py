# test_service_integration.py - Phase 2a: Service Integration Tests
import json
import pytest
import requests
import logging

@pytest.mark.parametrize("transport", [ "web", "http"])
def test_unified_service_starts(open_service,
                                service_py,
                                transport,
                                log,
                                ):
    """Test that unified service starts without errors"""
    with open_service(service_py, transport) as service:
        log.info(f"Unified service started with transport: {transport}")


def test_unified_service_web_routes(open_service,
                                    service_py,
):
    """Test that unified service serves web content correctly"""
    with open_service(service_py, "web") as client:
        assert client('health') != ''
        assert client('index.html') != ''

def test_unified_service_mcp_routes(open_service,
                                    service_py,
                                    log,
                                    ):
    """Test that unified service has MCP endpoints"""
    with open_service(service_py, "http") as client:
        response = client("mcp/resource/health")
        data = json.loads(response)
        assert data["status"] == "healthy"
        assert data["service"] == "mcp_service"
        log.info("MCP health endpoint test passed")


def test_unified_service_both_routes_same_port(open_service,
                                               service_py,
                                               ):
    """Test that both web and MCP routes work on the same port"""
    with open_service(service_py, "web") as client:
        assert client('health') != ''
        assert client('index.html') != ''
        assert client('mcp/health') != ''
        assert client('mcp/tool/list_tools') != ''
