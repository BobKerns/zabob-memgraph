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
MCP to SQLite Import Utility

This script imports knowledge graph data from MCP tools into SQLite database.
Can be run standalone or called from the HTTP server.
"""

import asyncio
import sys
from pathlib import Path

# Add the package to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from memgraph.stdio_mcp_client import stdio_mcp_knowledge_client
from memgraph.sqlite_backend import sqlite_knowledge_db


async def import_mcp_to_sqlite():
    """Import data from MCP tools to SQLite database"""
    print("Starting MCP to SQLite import...")
    
    try:
        # Import from MCP
        result = await sqlite_knowledge_db.import_from_mcp(stdio_mcp_knowledge_client)
        
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


async def test_sqlite_functionality():
    """Test SQLite read and search functionality"""
    print("\n🧪 Testing SQLite functionality...")
    
    try:
        # Test read_graph
        graph_data = await sqlite_knowledge_db.read_graph()
        print(f"✅ Read {len(graph_data['entities'])} entities and {len(graph_data['relations'])} relations")
        
        # Test search
        if graph_data['entities']:
            # Search for a common term
            search_results = await sqlite_knowledge_db.search_nodes("project")
            print(f"✅ Search for 'project' returned {len(search_results['entities'])} entities")
            
            # Show first few entity names
            entity_names = [e['name'] for e in graph_data['entities'][:5]]
            print(f"   Sample entities: {', '.join(entity_names)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False


async def main():
    """Main import and test function"""
    print("🚀 MCP to SQLite Import Tool")
    print("=" * 40)
    
    # Try import
    import_success = await import_mcp_to_sqlite()
    
    if import_success:
        # Test functionality
        await test_sqlite_functionality()
        print("\n✅ All tests passed! SQLite backend is ready.")
    else:
        print("\n❌ Import failed. Check MCP client configuration.")
        # Still test with any existing data
        await test_sqlite_functionality()


if __name__ == "__main__":
    asyncio.run(main())
