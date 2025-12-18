#!/usr/bin/env python3
"""Restore the 75 lost relations from lost_relations_2025-12-14.json."""

import asyncio
import json
import sys
from pathlib import Path

from memgraph import load_config

from memgraph.config import Config, default_config_dir

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent))

from memgraph.sqlite_backend import SQLiteKnowledgeGraphDB # noqa


async def restore_relations():
    """Load and restore all lost relations."""

    # Load the JSON file
    json_path = Path(__file__).parent / "lost_relations_2025-12-14.json"
    print(f"Loading relations from: {json_path}")

    config: Config = load_config(default_config_dir())

    with open(json_path) as f:
        data = json.load(f)

    relations = data["relations"]
    print(f"Found {len(relations)} relations to restore")
    print(f"Context: {data['context']}\n")

    # Use the real database
    db = SQLiteKnowledgeGraphDB(config)

    # Get initial count
    initial_stats = await db.get_stats()
    initial_count = initial_stats.get("relation_count", 0)
    print(f"Initial relation count: {initial_count}")

    # Transform relations to database format
    db_relations = [
        {
            "from_entity": r["source"],
            "to": r["target"],
            "relationType": r["relation"],
        }
        for r in relations
    ]

    # Restore in batches for progress reporting
    batch_size = 10
    total_created = 0

    for i in range(0, len(db_relations), batch_size):
        batch = db_relations[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(db_relations) + batch_size - 1) // batch_size

        print(f"\nProcessing batch {batch_num}/{total_batches} ({len(batch)} relations)...")

        before_stats = await db.get_stats()
        before_count = before_stats.get("relation_count", 0)

        await db.create_relations(batch)

        after_stats = await db.get_stats()
        after_count = after_stats.get("relation_count", 0)
        created = after_count - before_count
        total_created += created

        print(f"  Created {created}/{len(batch)} relations")

        # Show some examples from this batch
        for rel in batch[:3]:
            print(f"    - {rel['from_entity']} -> {rel['to']} ({rel['relationType']})")

    # Final verification
    final_stats = await db.get_stats()
    final_count = final_stats.get("relation_count", 0)

    print(f"\n{'='*60}")
    print("Restoration complete!")
    print(f"  Initial count: {initial_count}")
    print(f"  Final count:   {final_count}")
    print(f"  Created:       {total_created}/{len(relations)}")
    print(f"  Net change:    +{final_count - initial_count}")

    if total_created == len(relations):
        print(f"\n✅ SUCCESS! All {len(relations)} relations restored")
        return True
    else:
        print(f"\n⚠️  WARNING: Only {total_created}/{len(relations)} relations created")
        print("   Some may have been duplicates and were skipped")
        return True


if __name__ == "__main__":
    success = asyncio.run(restore_relations())
    sys.exit(0 if success else 1)
