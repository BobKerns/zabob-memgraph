#!/usr/bin/env uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "aiofiles",
#     "fastapi",
#     "jinja2",
#     "mcp",
#     "pydantic",
#     "uvicorn[standard]",
#     "httpx",
# ]
# ///
"""
Docker MCP to Server Import Utility

This script imports knowledge graph data from Docker MCP containers
via the running zabob-memgraph server's HTTP API.
"""

import asyncio
import sys
from pathlib import Path

import httpx

# Add the package to the path
sys.path.insert(0, str(Path(__file__).parent))

from memgraph.docker_mcp_client import docker_mcp_knowledge_client


async def import_via_server_api(server_url: str = "http://localhost:8080"):
    """Import data via the server's HTTP API"""
    print(f"🌐 Starting import via server API: {server_url}")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            # Check if server is running
            health_response = await client.get(f"{server_url}/health")
            if health_response.status_code != 200:
                print(f"❌ Server not responding at {server_url}")
                print(f"   Make sure zabob-memgraph server is running")
                return False
                
            print(f"✅ Server is running")
            
            # Get data from Docker MCP
            print("📥 Reading data from Docker MCP...")
            graph_data = await docker_mcp_knowledge_client.read_graph()
            
            if not graph_data.get("entities"):
                print("❌ No data retrieved from Docker MCP")
                return False
                
            print(f"✅ Retrieved {len(graph_data['entities'])} entities and {len(graph_data['relations'])} relations")
            
            # Send data to server
            print("📤 Sending data to server...")
            import_response = await client.post(
                f"{server_url}/api/import-mcp",
                json=graph_data
            )
            
            if import_response.status_code == 200:
                result = import_response.json()
                if result["status"] == "success":
                    print(f"✅ Import successful!")
                    print(f"   Entities imported: {result['imported_entities']}")
                    print(f"   Relations imported: {result['imported_relations']}")
                    
                    # Show database stats
                    if "database_stats" in result:
                        stats = result["database_stats"]
                        print(f"\n📊 Database Statistics:")
                        print(f"   Total entities: {stats['entity_count']}")
                        print(f"   Total relations: {stats['relation_count']}")
                        print(f"   Entity types: {stats['entity_types']}")
                        print(f"   Relation types: {stats['relation_types']}")
                        print(f"   Database: {stats['database_path']}")
                    
                    return True
                else:
                    print(f"❌ Import failed: {result['message']}")
                    return False
            else:
                print(f"❌ Server returned error {import_response.status_code}")
                print(f"   Response: {import_response.text}")
                return False
                
        except httpx.RequestError as e:
            print(f"❌ Failed to connect to server: {e}")
            print(f"   Make sure zabob-memgraph server is running at {server_url}")
            return False
        except Exception as e:
            print(f"❌ Import error: {e}")
            return False


async def test_docker_connection():
    """Test connection to Docker MCP container"""
    print("\n🧪 Testing Docker MCP connection...")

    try:
        # Try to read data from Docker MCP
        graph_data = await docker_mcp_knowledge_client.read_graph()

        if "Docker MCP Status" in [e.get("name", "") for e in graph_data.get("entities", [])]:
            print("❌ Docker MCP container not responding properly")
            print("   Check that Docker is running and mcp/memory image is available")
            print("   Verify claude-memory volume contains your data")
            return False
        else:
            print(f"✅ Docker MCP connection successful")
            print(f"   Found {len(graph_data['entities'])} entities and {len(graph_data['relations'])} relations")

            # Show sample entity names
            entity_names = [e['name'] for e in graph_data['entities'][:5]]
            print(f"   Sample entities: {', '.join(entity_names)}")
            return True

    except Exception as e:
        print(f"❌ Docker connection test failed: {e}")
        return False


async def check_docker_setup():
    """Check Docker setup and requirements"""
    print("🔍 Checking Docker setup...")

    import subprocess

    try:
        # Check if Docker is running
        result = subprocess.run(["docker", "version"],
                              capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            print("❌ Docker is not running or not installed")
            return False

        print("✅ Docker is running")

        # Check if mcp/memory image exists
        result = subprocess.run(["docker", "images", "mcp/memory"],
                              capture_output=True, text=True, timeout=10)
        if "mcp/memory" not in result.stdout:
            print("❌ mcp/memory Docker image not found")
            print("   Run: docker pull mcp/memory")
            return False

        print("✅ mcp/memory image found")

        # Check if claude-memory volume exists
        result = subprocess.run(["docker", "volume", "ls"],
                              capture_output=True, text=True, timeout=10)
        if "claude-memory" not in result.stdout:
            print("⚠️  claude-memory volume not found")
            print("   This volume should contain your knowledge graph data")
            print("   You may need to create it or check the volume name")
            return True  # Not fatal, might be named differently

        print("✅ claude-memory volume found")
        return True

    except subprocess.TimeoutExpired:
        print("❌ Docker commands timed out")
        return False
    except Exception as e:
        print(f"❌ Docker check failed: {e}")
        return False


async def main():
    """Main import function using server API"""
    print("🚀 Docker MCP to Server Import Tool")
    print("=" * 50)

    # Check Docker setup first
    docker_ok = await check_docker_setup()
    if not docker_ok:
        print("\n❌ Docker setup issues detected. Please fix before continuing.")
        return

    # Test Docker MCP connection
    connection_ok = await test_docker_connection()
    if not connection_ok:
        print("\n❌ Cannot connect to Docker MCP container.")
        print("   The import would fail. Check Docker setup and try again.")
        return

    # Import via server API
    import_success = await import_via_server_api()

    if import_success:
        print("\n✅ All operations completed successfully!")
        print("   Your knowledge graph data is now in the server database.")
        print("   Refresh the web interface to see the imported data.")
    else:
        print("\n❌ Import failed. Check error messages above.")


if __name__ == "__main__":
    asyncio.run(main())
