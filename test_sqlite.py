#!/usr/bin/env python3
"""
Simple test script to validate SQLite backend functionality
"""

import sys
import asyncio
from pathlib import Path

# Add the package to the path
sys.path.insert(0, str(Path(__file__).parent))

from memgraph.sqlite_backend import sqlite_knowledge_db

async def test_sqlite():
    print("🧪 Testing SQLite backend...")
    
    # Test database creation and stats
    stats = await sqlite_knowledge_db.get_stats()
    print(f"Database stats: {stats}")
    
    # Test read (should be empty initially)
    data = await sqlite_knowledge_db.read_graph()
    print(f"Initial data: {len(data['entities'])} entities, {len(data['relations'])} relations")
    
    print("✅ SQLite backend is working!")

if __name__ == "__main__":
    asyncio.run(test_sqlite())
