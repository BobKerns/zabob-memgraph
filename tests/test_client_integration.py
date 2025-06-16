# test_client_integration.py - Phase 2b: Client Integration Tests
import json
import pytest
import requests
import logging

def test_web_app_loads_static_content(js_client,
                                      log,
                                      ):

    # Test that index.html loads and contains expected web app structure
    log.info("Testing index.html loading")
    response = js_client("/")
    log.info(f"Index response: {response}")
    assert response.status_code == 200
    content = response.text.lower()

    # Look for typical web app elements
    assert "html" in content
    log.info("HTML content verified")
    # If graph.js or similar is referenced, check for it
    if "graph.js" in content or "script" in content:
        log.info("Web app structure detected in index.html")
        logging.info("Web app structure detected in index.html")

@pytest.mark.parametrize("transport", ["http", "stdio"])
def test_web_app_connects_to_mcp_service(js_client,
                                         transport,
                                         log,
                                         ):
    """Test that web app can connect to MCP service endpoints"""
    log.info("Testing MCP health endpoint")
    response = js_client(transport, "mcp/health")
    data = json.loads(response)
    assert data["status"] == "healthy"
    assert data["service"] == "mcp_service"
    log.info("MCP health test passed")


@pytest.mark.parametrize("transport, tool, expected", [
    ("stdio", "list_tools",{}),
    ("http", "list_tools", {}),
])
def test_client_js_mcp_integration(client_js,
                                   open_service,
                                    transport,
                                    tool,
                                    expected,
                                   log):
    """Test client.js MCP integration via subprocess"""
    log.info(f"Testing MCP tool endpoint: {tool} via {transport}")
    with open_service(client_js, transport) as js_client:
        result = json.loads(js_client(f"mcp/tool/{tool}"))
        assert result == expected
