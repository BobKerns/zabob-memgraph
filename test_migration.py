#!/usr/bin/env python3
"""
Test the migration script with a v1 database
"""

import asyncio
import json
import shutil
import sqlite3
import tempfile
from pathlib import Path


def create_v1_database(db_path: Path) -> None:
    """Create a v1 database with JSON observations"""
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        -- V1 schema with JSON observations
        CREATE TABLE entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            entity_type TEXT NOT NULL,
            observations TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE relations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_entity TEXT NOT NULL,
            to_entity TEXT NOT NULL,
            relation_type TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(from_entity, to_entity, relation_type)
        );

        -- Insert test data
        INSERT INTO entities VALUES
            (1, 'Python', 'Language', '["Interpreted", "Dynamic typing", "Versatile"]',
             '2024-01-01', '2024-01-01'),
            (2, 'FastAPI', 'Framework', '["Modern", "Fast", "Type hints"]',
             '2024-01-01', '2024-01-01'),
            (3, 'SQLite', 'Database', '["Embedded", "Serverless", "ACID"]',
             '2024-01-01', '2024-01-01');

        INSERT INTO relations VALUES
            (1, 'FastAPI', 'Python', 'written_in', '2024-01-01', '2024-01-01'),
            (2, 'FastAPI', 'SQLite', 'uses', '2024-01-01', '2024-01-01');
    """
    )
    conn.commit()
    conn.close()


def verify_v1_data(db_path: Path) -> dict:
    """Verify v1 database contents"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Count entities and observations
    cursor.execute("SELECT COUNT(*) FROM entities")
    entity_count = cursor.fetchone()[0]

    # Count total observations in JSON arrays
    cursor.execute("SELECT observations FROM entities")
    total_obs = sum(len(json.loads(row[0])) for row in cursor.fetchall())

    cursor.execute("SELECT COUNT(*) FROM relations")
    relation_count = cursor.fetchone()[0]

    conn.close()

    return {
        "entities": entity_count,
        "observations": total_obs,
        "relations": relation_count,
    }


def verify_v2_data(db_path: Path) -> dict:
    """Verify v2 database contents"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM entities")
    entity_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM observations")
    obs_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM relations")
    relation_count = cursor.fetchone()[0]

    # Check schema version
    cursor.execute(
        "SELECT version FROM schema_metadata ORDER BY updated_at DESC LIMIT 1"
    )
    schema_version = cursor.fetchone()[0]

    # Verify observations table structure
    cursor.execute("PRAGMA table_info(observations)")
    obs_columns = {row[1] for row in cursor.fetchall()}

    conn.close()

    return {
        "entities": entity_count,
        "observations": obs_count,
        "relations": relation_count,
        "schema_version": schema_version,
        "has_normalized_observations": "entity_id" in obs_columns,
    }


async def test_migration():
    """Test the migration process"""
    temp_dir = Path(tempfile.mkdtemp())

    try:
        print("🧪 Testing Migration Script")
        print("=" * 50)

        # Create v1 database
        v1_db = temp_dir / "test_v1.db"
        print(f"\n1️⃣  Creating v1 database: {v1_db}")
        create_v1_database(v1_db)

        v1_stats = verify_v1_data(v1_db)
        print("   ✅ V1 database created:")
        print(f"      Entities: {v1_stats['entities']}")
        print(f"      Observations: {v1_stats['observations']}")
        print(f"      Relations: {v1_stats['relations']}")

        # Copy for migration
        test_db = temp_dir / "test.db"
        shutil.copy(v1_db, test_db)

        # Run migration
        print(f"\n2️⃣  Running migration on: {test_db}")
        import subprocess

        result = subprocess.run(
            ["python", "migrate_to_v2.py", "--db-path", str(test_db), "--backup"],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print("   ❌ Migration failed!")
            print(f"   stdout: {result.stdout}")
            print(f"   stderr: {result.stderr}")
            return False

        print("   ✅ Migration completed")

        # Verify v2 database
        print("\n3️⃣  Verifying v2 database")
        v2_stats = verify_v2_data(test_db)
        print(f"   Schema version: {v2_stats['schema_version']}")
        print(f"   Entities: {v2_stats['entities']}")
        print(f"   Observations: {v2_stats['observations']}")
        print(f"   Relations: {v2_stats['relations']}")
        print(f"   Normalized observations: {v2_stats['has_normalized_observations']}")

        # Validate counts match
        print("\n4️⃣  Validating migration")
        checks = [
            (
                "Entity count matches",
                v1_stats["entities"] == v2_stats["entities"],
            ),
            (
                "Observation count matches",
                v1_stats["observations"] == v2_stats["observations"],
            ),
            (
                "Relation count matches",
                v1_stats["relations"] == v2_stats["relations"],
            ),
            ("Schema version is 2", v2_stats["schema_version"] == 2),
            (
                "Has normalized observations",
                v2_stats["has_normalized_observations"],
            ),
        ]

        all_passed = True
        for check_name, passed in checks:
            status = "✅" if passed else "❌"
            print(f"   {status} {check_name}")
            if not passed:
                all_passed = False

        # Check backup was created
        backup_files = list(temp_dir.glob("test_v1_backup_*.db"))
        print("\n5️⃣  Backup verification")
        if backup_files:
            print(f"   ✅ Backup created: {backup_files[0].name}")
        else:
            print("   ❌ No backup file found")
            all_passed = False

        if all_passed:
            print("\n🎉 All migration tests passed!")
        else:
            print("\n❌ Some tests failed")

        return all_passed

    finally:
        # Cleanup
        shutil.rmtree(temp_dir)
        print("\n🧹 Cleaned up test directory")


if __name__ == "__main__":
    success = asyncio.run(test_migration())
    exit(0 if success else 1)
