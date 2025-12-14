#!/usr/bin/env python3
"""
Quick test of normalized observations schema
"""

import asyncio
import os
import tempfile
from pathlib import Path

from memgraph.sqlite_backend import SQLiteKnowledgeGraphDB


async def test_new_schema():
    """Test creating and reading entities with normalized observations"""
    # Create temp database
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_path = temp_db.name
    temp_db.close()

    try:
        print(f"📝 Testing new schema with database: {temp_path}")

        # Create database instance
        os.environ["MEMGRAPH_DATABASE_PATH"] = temp_path
        db = SQLiteKnowledgeGraphDB(temp_path)

        # Test 1: Create entities with observations
        print("\n1️⃣  Creating entities...")
        await db.create_entities(
            [
                {
                    "name": "Python",
                    "entityType": "programming_language",
                    "observations": [
                        "High-level language",
                        "Dynamic typing",
                        "Great for data science",
                    ],
                },
                {
                    "name": "FastAPI",
                    "entityType": "web_framework",
                    "observations": [
                        "Modern Python framework",
                        "Built on Starlette",
                        "Automatic OpenAPI docs",
                    ],
                },
            ]
        )
        print("✅ Entities created")

        # Test 2: Create relations
        print("\n2️⃣  Creating relations...")
        await db.create_relations(
            [{"from_entity": "FastAPI", "to": "Python", "relationType": "built_with"}]
        )
        print("✅ Relations created")

        # Test 3: Read full graph
        print("\n3️⃣  Reading graph...")
        graph = await db.read_graph()
        print(f"   Entities: {len(graph['entities'])}")
        print(f"   Relations: {len(graph['relations'])}")

        for entity in graph["entities"]:
            print(
                f"   - {entity['name']}: {len(entity['observations'])} observations"
            )

        # Test 4: Search
        print("\n4️⃣  Searching for 'Python'...")
        results = await db.search_nodes("Python")
        print(f"   Found {len(results['entities'])} entities")

        # Test 5: Search in observations
        print("\n5️⃣  Searching for 'Modern'...")
        results = await db.search_nodes("Modern")
        print(f"   Found {len(results['entities'])} entities")
        if results["entities"]:
            print(f"   - {results['entities'][0]['name']}")

        # Test 6: Get stats
        print("\n6️⃣  Getting stats...")
        stats = await db.get_stats()
        print(f"   Entities: {stats['entity_count']}")
        print(f"   Observations: {stats['observation_count']}")
        print(f"   Relations: {stats['relation_count']}")

        print("\n🎉 All tests passed!")

    finally:
        # Cleanup
        Path(temp_path).unlink(missing_ok=True)
        print("\n🧹 Cleaned up test database")


if __name__ == "__main__":
    asyncio.run(test_new_schema())
