#!/usr/bin/env python3
"""Quick test to verify create_relations fix works."""

import asyncio
import sys
from pathlib import Path

from memgraph import load_config

from memgraph.config import default_config_dir

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent))

from memgraph.sqlite_backend import SQLiteKnowledgeGraphDB   # noqa


async def test_create_relations():
    """Test that create_relations actually persists to database."""

    # Use the real database
    config = load_config(default_config_dir())
    db = SQLiteKnowledgeGraphDB(config)

    # Get initial count
    initial_stats = await db.get_stats()
    initial_count = initial_stats.get("relation_count", 0)
    print(f"Initial relation count: {initial_count}")

    # Create a test relation with correct field names
    test_relations = [
        {
            "from_entity": "zabob-memgraph",
            "to": "SQLite",
            "relationType": "uses_for_testing",
        }
    ]

    print("\nCreating test relation: zabob-memgraph -> SQLite (uses_for_testing)")
    await db.create_relations(test_relations)

    # Check final count
    final_stats = await db.get_stats()
    final_count = final_stats.get("relation_count", 0)
    print(f"Final relation count: {final_count}")

    # Verify
    created = final_count - initial_count
    if created == 1:
        print(f"\n✅ SUCCESS! Created {created} relation (expected 1)")
        return True
    else:
        print(f"\n❌ FAILED! Created {created} relations (expected 1)")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_create_relations())
    sys.exit(0 if success else 1)
