#!/usr/bin/env python3
"""
Test the knowledge graph server
"""

import subprocess
import time
import requests
import sys
from pathlib import Path

def test_server():
    """Test the knowledge graph server"""
    
    print("Testing Knowledge Graph MCP Server...")
    
    # Test that we can import the module
    try:
        from memgraph.server import app
        print("✅ Module imports successfully")
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    
    # Test API endpoints (requires server to be running)
    base_url = "http://localhost:8080"
    
    try:
        # Test health endpoint
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health endpoint working")
        else:
            print(f"❌ Health endpoint failed: {response.status_code}")
            
        # Test knowledge graph endpoint
        response = requests.get(f"{base_url}/api/knowledge-graph", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Knowledge graph endpoint working: {len(data['nodes'])} nodes, {len(data['links'])} links")
        else:
            print(f"❌ Knowledge graph endpoint failed: {response.status_code}")
            
        # Test search endpoint
        response = requests.get(f"{base_url}/api/search?q=test", timeout=5)
        if response.status_code == 200:
            results = response.json()
            print(f"✅ Search endpoint working: {len(results)} results")
        else:
            print(f"❌ Search endpoint failed: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("⚠️  Server not running. Start with: python main.py")
        print("   Then test the web interface at http://localhost:8080")
        
    return True

if __name__ == "__main__":
    test_server()
