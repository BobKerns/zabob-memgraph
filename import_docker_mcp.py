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
# ]
# ///
"""
Docker MCP to SQLite Import Utility

This script imports knowledge graph data from Docker MCP containers into SQLite.
Specifically designed to work with the claude-memory Docker volume.
"""

import asyncio
import sys
from pathlib import Path

# Add the package to the path
sys.path.insert(0, str(Path(__file__).parent))

from memgraph.docker_mcp_client import docker_mcp_knowledge_client
from memgraph.sqlite_backend import sqlite_knowledge_db


async def import_docker_mcp_to_sqlite():
    """Import data from Docker MCP memory container to SQLite database"""
    print("🐳 Starting Docker MCP to SQLite import...")
    print("Container command:", " ".join(docker_mcp_knowledge_client.container_command))
    
    try:
        # Import from Docker MCP
        result = await sqlite_knowledge_db.import_from_mcp(docker_mcp_knowledge_client)
        
        if result["status"] == "success":
            print(f"✅ Import successful!")
            print(f"   Entities imported: {result['imported_entities']}")
            print(f"   Relations imported: {result['imported_relations']}")
            print(f"   Timestamp: {result['timestamp']}")
            
            # Show database stats
            stats = await sqlite_knowledge_db.get_stats()
            print(f"\n📊 Database Statistics:")
            print(f"   Total entities: {stats['entity_count']}")
            print(f"   Total relations: {stats['relation_count']}")
            print(f"   Entity types: {stats['entity_types']}")
            print(f"   Relation types: {stats['relation_types']}")
            print(f"   Database: {stats['database_path']}")
            
        else:
            print(f"❌ Import failed: {result['message']}")
            return False
            
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False
    
    return True


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
    """Main import and test function"""
    print("🚀 Docker MCP to SQLite Import Tool")
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
    
    # Proceed with import
    import_success = await import_docker_mcp_to_sqlite()
    
    if import_success:
        print("\n✅ All operations completed successfully!")
        print("   Your knowledge graph data is now in SQLite database.")
        print("   Restart the memgraph server to see the imported data.")
    else:
        print("\n❌ Import failed. Check error messages above.")


if __name__ == "__main__":
    asyncio.run(main())
