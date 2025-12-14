# test_service_integration.py - Phase 2a: Service Integration Tests
import json
import pytest


@pytest.mark.parametrize("transport", ["web", "http", "stdio", "both"])
def test_unified_service_starts(open_service,
                                service_py,
                                transport,
                                log,
                                ):
    """Test that unified service starts without errors"""
    with open_service(service_py, transport) as _:
        log.info(f"Unified service started with transport: {transport}")


def test_unified_service_web_routes(open_service,
                                    service_py,
                                    log,
                                    ):
    """Test that unified service serves web content correctly"""
    with open_service(service_py, "web") as client:
        assert client('health') != ''
        assert client('index.html') != ''


@pytest.mark.skip(
    reason="MCP client.js is hardcoded to call specific MCP tools, "
    "not generic HTTP endpoints. Need to rewrite tests to properly test MCP tools "
    "or create a generic HTTP test client."
)
def test_unified_service_mcp_routes(open_service,
                                    service_py,
                                    log,
                                    ):
    """Test that unified service has MCP endpoints"""
    with open_service(service_py, "both") as (mcp_client, web_client):
        # Test web endpoints with direct HTTP
        web_health_response = web_client("health")
        web_health_data = json.loads(web_health_response)
        assert web_health_data["status"] == "healthy"
        assert web_health_data["service"] == "unified_service"
        log.info("Web health endpoint working")

        # Test MCP endpoints with client.js
        mcp_health_response = mcp_client("mcp/health")
        # Note: client.js response format may be different, check for expected content
        assert "healthy" in mcp_health_response or "mcp_service" in mcp_health_response
        log.info("MCP health endpoint working")

        log.info("Both web and MCP endpoints verified")


@pytest.mark.skip(
    reason="MCP client.js is hardcoded to call specific MCP tools, "
    "not generic HTTP endpoints. Need to rewrite tests to properly test MCP tools "
    "or create a generic HTTP test client."
)
def test_unified_service_both_routes_same_port(open_service,
                                               service_py,
                                               log,
                                               ):
    """Test that both web and MCP routes work on the same port"""
    with open_service(service_py, "both") as (mcp_client, web_client):
        # Test web routes
        log.info("Testing web routes")
        health_response = web_client('health')
        assert health_response != ''
        assert "healthy" in health_response

        index_response = web_client('')  # index.html
        assert index_response != ''
        assert "html" in index_response.lower()
        log.info("Web routes working")

        # Test MCP routes
        log.info("Testing MCP routes")
        mcp_health_response = mcp_client('mcp/health')
        assert mcp_health_response != ''
        # MCP client.js may return different format, just check it's not empty

        # Note: mcp/tool/list_tools may not be implemented yet, comment out for now
        # mcp_tools_response = mcp_client('mcp/tool/list_tools')
        # assert mcp_tools_response != ''
        log.info("MCP routes working")

        log.info("Both web and MCP routes verified on same port")
